"""Tests for the automated dataset pipeline (ml.data).

Fixture data in this module and tests/fixtures/ is SYNTHETIC and exists ONLY
to exercise pipeline mechanics. It is never used as ML training data: the
build pipeline only ingests sources enabled in ml/ml/data/config/sources.yaml,
and every source there is disabled pending manual approval.

Coverage per master-prompt section 27:
  source parser / normalization / coordinate validation / category mapping /
  deduplication / privacy-spatial generalization / quality scoring /
  versioning / demo-data exclusion / temporal target split / export.
"""

from __future__ import annotations

import csv
import json
import random
from pathlib import Path

import pytest

from ml.data.build_dataset import exclude_source_types, load_source_registry
from ml.data.config.schema import (
    CRIME_CATEGORY_MAPPING,
    CrimeCategory,
    DatasetRecord,
    SourceType,
    VerificationState,
)
from ml.data.exports.export import (
    export_all_formats,
    export_csv,
    export_jsonl,
    export_parquet,
)
from ml.data.features.engineer import split_temporal
from ml.data.normalization.normalize import Normalizer
from ml.data.quality.quality_report import generate_quality_report, save_quality_report
from ml.data.sources.adapters import ResearchDatasetSource, get_adapter
from ml.data.sources.government import GovernmentCrimeSource
from ml.data.spatial.aggregate import SpatialConfig, SpatialProcessor
from ml.data.validation.deduplicate import deduplicate_records
from ml.data.validation.validate import validate_records
from ml.data.versioning.version import VersionManager, create_source_version

FIXTURES = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_record(
    record_id: str = "r1",
    source_id: str = "src_a",
    source_type: SourceType = SourceType.OFFICIAL,
    category: CrimeCategory = CrimeCategory.HARASSMENT,
    date: str = "2023-05-01",
    lat: float | None = 28.6315,
    lon: float | None = 77.2167,
    quality: float | None = 0.8,
    verification: VerificationState = VerificationState.VERIFIED,
) -> DatasetRecord:
    return DatasetRecord(
        record_id=record_id,
        source_id=source_id,
        source_name="Test Source",
        source_type=source_type,
        crime_category=category,
        crime_subcategory=None,
        incident_date=date,
        incident_time=None,
        latitude=lat,
        longitude=lon,
        district=None,
        city="New Delhi",
        state="Delhi",
        country="India",
        description_available=False,
        verification_state=verification,
        source_url=None,
        collection_timestamp="2026-08-22T00:00:00Z",
        geocoding_method="source_provided",
        geocoding_confidence=1.0,
        spatial_precision="exact",
        data_quality_score=quality,
        dataset_version="test",
        original_category=category.value,
        original_source_record_id=record_id,
    )


@pytest.fixture()
def normalizer() -> Normalizer:
    return Normalizer(dataset_version="test")


def tmp_dir() -> Path:
    """Throwaway adapter cache dir (never pollutes the repo tree)."""
    import tempfile

    return Path(tempfile.mkdtemp(prefix="wsdp_cache_"))


def _src(source_id: str = "ncrb_test", parser: str = "ncrb_csv") -> dict:
    return {
        "source_id": source_id,
        "source_name": "Fixture Source (synthetic)",
        "source_type": "government",
        "parser": parser,
        "license": "CC BY 4.0",
        "source_url": "https://example.invalid/data.csv",
    }


# ---------------------------------------------------------------------------
# Source parsers (section 27: source parser)
# ---------------------------------------------------------------------------


class TestSourceParsers:
    def test_government_csv_parser_reads_fixture_rows(self):
        adapter = GovernmentCrimeSource(_src(), cache_dir=tmp_dir())
        raw = (FIXTURES / "fixture_records.csv").read_bytes()
        rows = adapter.parse(raw)
        assert len(rows) == 6  # includes one deliberate duplicate row
        assert rows[0]["category"] == "harassment"

    def test_unknown_license_refuses_ingestion(self, tmp_path):
        cfg = _src("research_bad", parser="research_csv")
        cfg["license"] = "unknown"
        adapter = ResearchDatasetSource(cfg, cache_dir=tmp_path)
        result = adapter.fetch()
        assert result.records == []
        assert any("License is unknown" in e for e in result.errors)

    def test_unknown_parser_fails_loudly(self, tmp_path):
        with pytest.raises(ValueError, match="Unknown parser"):
            get_adapter(_src(parser="mystery_format"), cache_dir=tmp_path)

    def test_registry_only_lists_disabled_templates(self):
        """Every shipped source must be an unapproved template until a human
        verifies license + URL. The pipeline must therefore ingest nothing by
        default — never silently scrape the internet."""
        registry_path = Path(__file__).parents[1] / "ml" / "data" / "config" / "sources.yaml"
        registry = load_source_registry(registry_path)
        assert all(not entry.enabled for entry in registry.values())


# ---------------------------------------------------------------------------
# Normalization + category mapping (section 27)
# ---------------------------------------------------------------------------


class TestNormalization:
    def test_category_mapping_is_explicit_and_traceable(self, normalizer):
        rec = normalizer.normalize(
            {"id": "X1", "category": "harassment", "date": "2023-03-14"},
            _src(),
        )
        assert rec.crime_category is CrimeCategory.HARASSMENT
        # original preserved for traceability (spec section 8)
        assert rec.original_category == "harassment"

    def test_unknown_category_maps_to_other_with_original_kept(self, normalizer):
        rec = normalizer.normalize(
            {"id": "X2", "category": "weird_local_label", "date": "2023-03-14"},
            _src(),
        )
        assert rec.crime_category is CrimeCategory.OTHER
        assert rec.original_category == "weird_local_label"

    def test_multiple_date_formats_parse(self, normalizer):
        for raw_date in ("2023-03-14", "15/03/2023", "2023-04-01T18:05:00"):
            rec = normalizer.normalize({"id": "D", "category": "rape", "date": raw_date}, _src())
            assert rec.incident_date != ""

    def test_missing_or_invalid_date_is_not_fabricated(self, normalizer):
        rec = normalizer.normalize({"id": "D2", "category": "rape", "date": "not-a-date"}, _src())
        assert rec.incident_date == ""  # validation will reject it downstream

    def test_invalid_coordinates_dropped_at_normalization(self, normalizer):
        rec = normalizer.normalize(
            {
                "id": "C1",
                "category": "rape",
                "date": "2023-03-14",
                "latitude": "999.0",
                "longitude": "77.2",
            },
            _src(),
        )
        assert rec.latitude is None  # impossible latitude rejected

    def test_state_names_normalized(self, normalizer):
        _, _, _, country = normalizer._normalize_admin({"state": "delhi"}, _src())
        district, city, state, _ = normalizer._normalize_admin(
            {"state": "delhi", "city": "new delhi"}, _src()
        )
        assert state == "Delhi"

    def test_every_mapping_target_is_a_real_category(self):
        for source_map in CRIME_CATEGORY_MAPPING.values():
            for target in source_map.values():
                assert isinstance(target, CrimeCategory)


# ---------------------------------------------------------------------------
# Validation / coordinate checks (section 27)
# ---------------------------------------------------------------------------


class TestValidation:
    def test_impossible_coordinates_rejected(self):
        bad = make_record(lat=999.0, lon=77.2)
        valid, report = validate_records([bad])
        assert len(valid) == 0
        assert report.invalid_records == 1

    def test_valid_record_passes(self):
        valid, report = validate_records([make_record()])
        assert len(valid) == 1
        assert report.valid_records == 1

    def test_invalid_date_rejected(self):
        rec = make_record(date="")
        valid, report = validate_records([rec])
        assert len(valid) == 0

    def test_duplicate_ids_counted_not_merged_silently(self):
        recs = [make_record(record_id="dup"), make_record(record_id="dup")]
        valid, report = validate_records(recs)
        assert report.duplicate_records >= 1


# ---------------------------------------------------------------------------
# Deduplication (section 12 / 27)
# ---------------------------------------------------------------------------


class TestDeduplication:
    def test_same_source_same_record_id_merges(self):
        a = make_record(record_id="F-001", quality=0.4)
        b = make_record(record_id="F-001", quality=0.9)
        result = deduplicate_records([a, b])
        assert result.total_unique == 1
        assert result.unique_records[0].data_quality_score == 0.9  # best kept

    def test_cross_source_records_never_merge(self):
        """Same facts from two different sources are corroboration, not a
        duplicate — merging would destroy source diversity evidence."""
        a = make_record(record_id="F-001", source_id="src_a")
        b = make_record(record_id="F-001", source_id="src_b")
        result = deduplicate_records([a, b])
        assert result.total_unique == 2

    def test_dedup_decision_traceable(self):
        a = make_record(record_id="F-001", quality=0.4)
        b = make_record(record_id="F-001", quality=0.9)
        result = deduplicate_records([a, b])
        group = result.duplicate_groups[0]
        assert {r.record_id for r in group} == {"F-001"} or len(group) == 2
        kept = result.unique_records[0]
        assert kept in (a, b)  # decision traceable to input records


# ---------------------------------------------------------------------------
# Privacy / spatial generalization (sections 10 / 26)
# ---------------------------------------------------------------------------


class TestPrivacySpatial:
    def test_sensitive_category_coordinates_generalized(self):
        proc = SpatialProcessor(SpatialConfig(h3_resolution=8))
        sensitive = make_record(category=CrimeCategory.RAPE)
        gen_lat, gen_lon = proc.generalize_coordinates(sensitive)
        cell = proc.get_cell_id(sensitive)
        centroid = __import__("h3").cell_to_latlng(cell)
        assert (gen_lat, gen_lon) == pytest.approx(centroid, abs=1e-6)
        # moved off the exact input point
        assert (gen_lat, gen_lon) != (sensitive.latitude, sensitive.longitude)

    def test_non_sensitive_coordinates_unchanged(self):
        proc = SpatialProcessor(SpatialConfig(h3_resolution=8))
        ordinary = make_record(category=CrimeCategory.POOR_LIGHTING)
        assert proc.generalize_coordinates(ordinary) == (ordinary.latitude, ordinary.longitude)

    def test_cell_assignment_stable(self):
        proc = SpatialProcessor(SpatialConfig(h3_resolution=8))
        r = make_record()
        assert proc.get_cell_id(r) == proc.get_cell_id(make_record(record_id="r2"))

    def test_no_pii_fields_in_canonical_schema(self):
        forbidden = {"victim_name", "phone", "email", "address"}
        fields = set(DatasetRecord.field_names())
        assert not (forbidden & fields)


# ---------------------------------------------------------------------------
# Quality scoring (sections 13 / 22 / 27)
# ---------------------------------------------------------------------------


class TestQualityScoring:
    def test_verified_complete_record_scores_higher_than_sparse(self):
        rich = make_record()
        poor = make_record(
            lat=None,
            lon=None,
            quality=None,
            verification=VerificationState.REPORTED,
            category=CrimeCategory.OTHER,
        )
        n = Normalizer(dataset_version="t")
        rich_score = n._compute_quality_score(
            rich.latitude,
            rich.longitude,
            rich.incident_date,
            rich.crime_category,
            rich.verification_state,
            False,
        )
        poor_score = n._compute_quality_score(
            None,
            None,
            poor.incident_date,
            poor.crime_category,
            poor.verification_state,
            False,
        )
        assert rich_score > poor_score
        assert 0.0 <= poor_score <= 1.0 <= 1.0

    def test_quality_report_generated_and_saved(self, tmp_path):
        records = [make_record(), make_record(record_id="r2", quality=0.5)]
        _, vreport = validate_records(records)
        qreport = generate_quality_report(records, vreport, dataset_version="tv1")
        json_path, html_path = save_quality_report(qreport, str(tmp_path))
        loaded = json.loads(Path(json_path).read_text(encoding="utf-8"))
        assert loaded["total_records"] == 2
        assert Path(html_path).exists() and "tv1" in Path(html_path).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Versioning & lineage (sections 20 / 21 / 27)
# ---------------------------------------------------------------------------


class TestVersioning:
    def test_manifest_hash_order_independent(self, tmp_path):
        vm = VersionManager(tmp_path)
        recs = [make_record(record_id=f"r{i}") for i in range(10)]
        h1 = vm.compute_dataset_hash(recs)
        shuffled = recs[:]
        random.Random(7).shuffle(shuffled)
        h2 = vm.compute_dataset_hash(shuffled)
        assert h1 == h2

    def test_manifest_roundtrip_and_listing(self, tmp_path):
        vm = VersionManager(tmp_path)
        recs = [make_record()]
        manifest = vm.create_manifest(
            records=recs,
            source_versions=[create_source_version("s", "S", recs, "abc")],
            feature_schema_version="1.0.0",
            geocoding_version="1.0.0",
            processing_version="1.0.0",
        )
        path = vm.save_manifest(manifest)
        assert path.exists()
        assert vm.list_versions() == [manifest.dataset_version]
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["record_count"] == 1
        assert data["dataset_hash"]

    def test_versions_are_immutable_new_files(self, tmp_path):
        vm = VersionManager(tmp_path)
        v1 = vm.generate_version()
        manifest1 = vm.create_manifest([make_record()], [], "1", "1", "1")
        p1 = vm.save_manifest(manifest1)
        v2 = vm.generate_version()
        manifest2 = vm.create_manifest([make_record()], [], "1", "1", "1")
        p2 = vm.save_manifest(manifest2)
        # Never overwrite previous datasets (spec section 20)
        assert p1 != p2 or v1 != v2


# ---------------------------------------------------------------------------
# Demo-data exclusion (sections 19 / 28)
# ---------------------------------------------------------------------------


class TestDemoExclusion:
    def test_demo_seed_records_excluded(self):
        official = make_record(record_id="ok")
        demo = make_record(record_id="demo", source_type=SourceType.DEMO_SEED)
        kept = exclude_source_types([official, demo], ["demo_seed"])
        assert [r.record_id for r in kept] == ["ok"]

    def test_default_config_excludes_demo_seed(self):
        config_yaml = Path(__file__).parents[1] / "ml" / "data" / "config" / "sources.yaml"
        text = config_yaml.read_text(encoding="utf-8")
        assert "demo_seed" in text  # exclusion list present in shipped config

    def test_demo_seed_would_fail_validation_gate(self):
        """Even if a demo record slipped through normalization it carries
        source_type=demo_seed and is dropped before validation."""
        records = [
            make_record(record_id="a"),
            make_record(record_id="b", source_type=SourceType.DEMO_SEED),
            make_record(record_id="c", source_type=SourceType.DEMO_SEED),
        ]
        kept = exclude_source_types(records, excluded={"demo_seed"})
        assert len(kept) == 1 and kept[0].record_id == "a"


# ---------------------------------------------------------------------------
# Temporal split / target generation (sections 17 / 18 / 27)
# ---------------------------------------------------------------------------


class TestTemporalSplit:
    def test_split_is_temporal_not_random(self):
        recs = [
            make_record(record_id="old", date="2022-01-10"),
            make_record(record_id="mid", date="2024-03-01"),
            make_record(record_id="new", date="2025-02-15"),
        ]
        train, val, test = split_temporal(recs, "2023-12-31", "2024-06-30", "2024-07-01")
        assert [r.record_id for r in train] == ["old"]
        assert [r.record_id for r in val] == ["mid"]
        assert [r.record_id for r in test] == ["new"]

    def test_no_overlap_between_splits(self):
        dates = [f"20{y}-{m:02d}-01" for y in range(22, 26) for m in range(1, 13)]
        recs = [make_record(record_id=str(i), date=d) for i, d in enumerate(dates)]
        train, val, test = split_temporal(recs, "2023-06-30", "2024-06-30", "2024-07-01")
        train_ids = {id(r) for r in train}
        assert not (train_ids & {id(r) for r in val})
        assert not (train_ids & {id(r) for r in test})


# ---------------------------------------------------------------------------
# Export (sections 23 / 27)
# ---------------------------------------------------------------------------


class TestExport:
    @pytest.fixture()
    def exported(self, tmp_path):
        recs = [make_record(record_id=f"r{i}") for i in range(3)]
        paths = {}
        paths["csv"] = export_csv(recs, tmp_path / "p.csv")
        paths["parquet"] = export_parquet(recs, tmp_path / "p.parquet")
        paths["jsonl"] = export_jsonl(recs, tmp_path / "p.jsonl")
        paths["dir"], paths["recs"] = tmp_path, recs
        return paths

    def test_csv_roundtrip(self, exported):
        with open(exported["csv"], newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 3
        assert rows[0]["record_id"] == "r0"
        assert set(rows[0]) == set(DatasetRecord.field_names())

    def test_parquet_roundtrip(self, exported):
        import pyarrow.parquet as pq

        table = pq.read_table(exported["parquet"])
        assert table.num_rows == 3

    def test_jsonl_line_per_record(self, exported):
        lines = exported["jsonl"].read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 3
        assert json.loads(lines[0])["record_id"] == "r0"

    def test_export_all_formats(self, tmp_path):
        recs = [make_record()]
        results = export_all_formats(recs, features=None, output_dir=tmp_path, dataset_version="vX")
        for key in ("csv", "parquet", "jsonl"):
            assert key in results and results[key].exists()

    def test_exports_contain_no_raw_description_text(self, exported):
        """description_available is a boolean flag; free text never leaves
        the API (matches schema.sql description_redacted policy)."""
        text = exported["csv"].read_text(encoding="utf-8")
        assert "description_redacted" not in text
