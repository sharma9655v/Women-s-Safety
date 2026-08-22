"""Main dataset build pipeline.

Orchestrates the full pipeline:
1. Load source configurations
2. Download/ingest raw data
3. Normalize to canonical schema
4. Validate records
5. Deduplicate
6. Geocode (if needed)
7. Spatial aggregation
8. Feature engineering
9. Quality scoring
10. Versioning and lineage
11. Export
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from ml.data.config.schema import SourceRegistryEntry, SourceType
from ml.data.exports.export import export_all_formats
from ml.data.features.engineer import FeatureConfig, FeatureEngineer, split_temporal
from ml.data.ingestion.base import IngestionResult
from ml.data.ingestion.download import create_session
from ml.data.normalization.normalize import NormalizedRecord, normalize_records
from ml.data.quality.quality_report import (
    generate_quality_report,
    save_quality_report,
)
from ml.data.spatial.aggregate import SpatialConfig, SpatialProcessor
from ml.data.validation.deduplicate import deduplicate_records
from ml.data.validation.validate import validate_records
from ml.data.versioning.version import (
    LineageTracker,
    VersionManager,
    create_source_version,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def exclude_source_types(records: list, excluded: list[str] | set[str]) -> list:
    """Drop records whose source_type is excluded (e.g. demo_seed).

    Demo/seed data must never silently become ML training evidence. The
    default exclusion is enforced by config; this function is the single
    choke point so the rule is unit-testable.

    Comparison uses ``.value`` (not ``str()``): on Python 3.11+ a
    ``(str, Enum)`` member stringifies as "SourceType.DEMO_SEED", which
    would silently match nothing and let demo data through.
    """
    excluded_norm = {str(e) for e in excluded}
    kept = []
    for r in records:
        raw = getattr(r, "source_type", "")
        value = getattr(raw, "value", raw)  # Enum -> its string value
        if str(value) not in excluded_norm:
            kept.append(r)
    return kept


class PipelineConfig:
    """Pipeline configuration loaded from YAML."""

    def __init__(self, config_path: Path):
        with config_path.open(encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

    @property
    def sources(self) -> list[dict[str, Any]]:
        return [s for s in self.config.get("sources", []) if s.get("enabled", True)]

    @property
    def pipeline_config(self) -> dict[str, Any]:
        return self.config.get("pipeline", {})

    @property
    def output_dir(self) -> Path:
        return Path(self.pipeline_config.get("output_dir", "ml/data/exports"))

    @property
    def cache_dir(self) -> Path:
        return Path(self.pipeline_config.get("cache_dir", "ml/data/cache"))

    @property
    def versions_dir(self) -> Path:
        return Path(self.pipeline_config.get("versions_dir", "ml/data/versions"))

    @property
    def offline_mode(self) -> bool:
        return self.pipeline_config.get("offline_mode", False)

    @property
    def min_quality_score(self) -> float:
        return self.pipeline_config.get("min_data_quality_score", 0.3)

    @property
    def excluded_source_types(self) -> list[str]:
        return self.pipeline_config.get("excluded_source_types", ["demo_seed"])

    @property
    def temporal_split(self) -> dict[str, str]:
        return self.pipeline_config.get(
            "temporal_split",
            {
                "train_end": "2023-12-31",
                "validation_end": "2024-06-30",
                "test_start": "2024-07-01",
            },
        )

    @property
    def spatial_config(self) -> SpatialConfig:
        spatial = self.pipeline_config.get("spatial_aggregation", {})
        return SpatialConfig(
            aggregation_method=spatial.get("method", "h3"),
            h3_resolution=spatial.get("resolution", 8),
            admin_level=spatial.get("admin_level", "district"),
        )


def load_source_registry(registry_path: Path) -> dict[str, SourceRegistryEntry]:
    """Load source registry from YAML."""
    if not registry_path.exists():
        logger.warning(f"Source registry not found at {registry_path}")
        return {}

    with registry_path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    sources = {}
    # `sources:` may be null when every entry is a disabled template.
    for src in data.get("sources") or []:
        entry = SourceRegistryEntry(
            source_id=src["source_id"],
            source_name=src["source_name"],
            source_type=SourceType(src["source_type"]),
            publisher=src["publisher"],
            license=src["license"],
            source_url=src["source_url"],
            geographical_coverage=src["geographical_coverage"],
            temporal_coverage=src["temporal_coverage"],
            update_frequency=src["update_frequency"],
            allowed_usage=src["allowed_usage"],
            reliability_level=src["reliability_level"],
            parser=src["parser"],
            enabled=src.get("enabled", True),
        )
        sources[entry.source_id] = entry

    return sources


class DatasetPipeline:
    """Main dataset build pipeline."""

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.session = create_session()
        self.version_manager = VersionManager(config.versions_dir)
        self.lineage_tracker = LineageTracker(config.versions_dir / "lineage")

    def run(self) -> dict[str, Any]:
        """Run the full pipeline."""
        logger.info("Starting dataset build pipeline")

        # Load source registry
        registry_path = Path("ml/data/config/sources.yaml")
        source_registry = load_source_registry(registry_path)
        enabled_sources = [s for s in source_registry.values() if s.enabled]

        if not enabled_sources:
            logger.warning("No enabled sources found in registry")
            return {"status": "no_sources", "records": 0}

        all_normalized: list[NormalizedRecord] = []
        source_versions = []
        source_checksums = {}

        # Stage 1: Ingestion
        logger.info(f"Ingesting {len(enabled_sources)} sources")
        for source_entry in enabled_sources:
            if source_entry.source_type.value in self.config.excluded_source_types:
                logger.info(f"Skipping excluded source: {source_entry.source_id}")
                continue

            result = self._ingest_source(source_entry)
            if result.records:
                # Stage 2: Normalization
                normalized = normalize_records(
                    [r.raw_data for r in result.records],
                    source_entry.to_dict(),
                    self.config.pipeline_config.get(
                        "dataset_version", datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
                    ),
                )
                all_normalized.extend(normalized)

                source_versions.append(
                    create_source_version(
                        source_entry.source_id,
                        source_entry.source_name,
                        normalized,
                        result.source_checksum,
                    )
                )
                source_checksums[source_entry.source_id] = result.source_checksum

                logger.info(f"  {source_entry.source_id}: {len(normalized)} records normalized")

        if not all_normalized:
            logger.warning("No records after normalization")
            return {"status": "no_records", "records": 0}

        logger.info(f"Total normalized records: {len(all_normalized)}")

        # Stage 3: Convert to DatasetRecord
        dataset_records = self._to_dataset_records(all_normalized)

        # Stage 4: Filter excluded source types (demo_seed never trains)
        dataset_records = exclude_source_types(dataset_records, self.config.excluded_source_types)

        # Stage 5: Validation
        logger.info("Validating records")
        valid_records, validation_report = validate_records(dataset_records)
        logger.info(
            "  Valid: %s, Invalid: %s",
            validation_report.valid_records,
            validation_report.invalid_records,
        )

        # Stage 6: Deduplication
        logger.info("Deduplicating records")
        dedup_result = deduplicate_records(valid_records)
        logger.info(
            f"  Unique: {dedup_result.total_unique}, Duplicates: {dedup_result.total_duplicates}"
        )

        # Stage 7: Geocoding (for records without coordinates)
        logger.info("Geocoding records without coordinates")
        geocoded_records = self._geocode_records(dedup_result.unique_records)
        logger.info(
            f"  Geocoded: {sum(1 for r in geocoded_records if r.latitude is not None)} records"
        )

        # Stage 8: Spatial features
        logger.info("Computing spatial features")
        spatial_processor = SpatialProcessor(self.config.spatial_config)
        spatial_processor.compute_spatial_features(geocoded_records)

        # Stage 9: Feature engineering
        logger.info("Engineering features")
        feature_engineer = FeatureEngineer(FeatureConfig())
        features = feature_engineer.engineer_features(geocoded_records)

        # Stage 10: Quality filtering
        logger.info("Filtering by quality score")
        quality_filtered = [
            r
            for r in geocoded_records
            if (r.data_quality_score or 0) >= self.config.min_quality_score
        ]
        logger.info(f"  After quality filter: {len(quality_filtered)} records")

        # Stage 11: Temporal split
        logger.info("Creating temporal splits")
        train, validation, test = split_temporal(
            quality_filtered,
            self.config.temporal_split["train_end"],
            self.config.temporal_split["validation_end"],
            self.config.temporal_split["test_start"],
        )
        logger.info(f"  Train: {len(train)}, Validation: {len(validation)}, Test: {len(test)}")

        # Stage 12: Quality report
        logger.info("Generating quality report")
        quality_report = generate_quality_report(
            quality_filtered, validation_report, dataset_records[0].dataset_version
        )
        quality_json_path, quality_html_path = save_quality_report(
            quality_report, self.config.output_dir
        )

        # Stage 13: Versioning and lineage
        logger.info("Creating manifest and lineage")
        manifest = self.version_manager.create_manifest(
            records=quality_filtered,
            source_versions=source_versions,
            feature_schema_version="1.0.0",
            geocoding_version="1.0.0",
            processing_version="1.0.0",
            validation_report_path=quality_json_path,
            quality_report_path=quality_json_path,
        )
        self.version_manager.save_manifest(manifest)

        # Lineage
        lineage_records = []
        for record in quality_filtered:
            lr = self.lineage_tracker.track_record(
                record,
                processing_stages=[
                    "ingestion",
                    "normalization",
                    "validation",
                    "deduplication",
                    "geocoding",
                    "features",
                ],
                processing_versions={
                    "normalization": "1.0.0",
                    "validation": "1.0.0",
                    "deduplication": "1.0.0",
                    "geocoding": "1.0.0",
                    "features": "1.0.0",
                },
            )
            lineage_records.append(lr)
        self.lineage_tracker.save_lineage(lineage_records, manifest.dataset_version)

        # Stage 14: Export
        logger.info("Exporting dataset")
        export_results = export_all_formats(
            records=quality_filtered,
            features=features,
            output_dir=self.config.output_dir,
            dataset_version=manifest.dataset_version,
        )

        # Summary
        summary = {
            "status": "success",
            "dataset_version": manifest.dataset_version,
            "total_records": len(quality_filtered),
            "train_records": len(train),
            "validation_records": len(validation),
            "test_records": len(test),
            "sources": [sv.source_id for sv in source_versions],
            "exports": {k: str(v) for k, v in export_results.items()},
            "quality_report_json": quality_json_path,
            "quality_report_html": quality_html_path,
            "manifest": str(self.config.versions_dir / f"manifest_{manifest.dataset_version}.json"),
        }

        logger.info(f"Pipeline completed successfully: {manifest.dataset_version}")
        return summary

    def _ingest_source(self, source_entry: SourceRegistryEntry) -> IngestionResult:
        """Ingest a single source using its registered parser adapter."""
        from ml.data.sources.adapters import get_adapter

        try:
            adapter = get_adapter(source_entry.to_dict(), self.config.cache_dir)
            return adapter.fetch(force=not self.config.offline_mode)
        except ValueError as exc:
            logger.error(f"Source {source_entry.source_id}: {exc}")
            return IngestionResult(
                source_id=source_entry.source_id,
                records=[],
                total_fetched=0,
                total_valid=0,
                total_invalid=0,
                errors=[str(exc)],
                fetched_at=datetime.now(UTC).isoformat(),
                source_checksum="",
            )
        except Exception as exc:
            logger.error(f"Source {source_entry.source_id} ingestion failed: {exc}")
            return IngestionResult(
                source_id=source_entry.source_id,
                records=[],
                total_fetched=0,
                total_valid=0,
                total_invalid=0,
                errors=[f"Ingestion failed: {exc}"],
                fetched_at=datetime.now(UTC).isoformat(),
                source_checksum="",
            )

    def _to_dataset_records(self, normalized: list[NormalizedRecord]) -> list[Any]:
        """Convert NormalizedRecord to DatasetRecord."""
        from ml.data.config.schema import DatasetRecord

        records = []
        for nr in normalized:
            records.append(
                DatasetRecord(
                    record_id=nr.record_id,
                    source_id=nr.source_id,
                    source_name=nr.source_name,
                    source_type=nr.source_type,
                    crime_category=nr.crime_category,
                    crime_subcategory=nr.crime_subcategory,
                    incident_date=nr.incident_date,
                    incident_time=nr.incident_time,
                    latitude=nr.latitude,
                    longitude=nr.longitude,
                    district=nr.district,
                    city=nr.city,
                    state=nr.state,
                    country=nr.country,
                    description_available=nr.description_available,
                    verification_state=nr.verification_state,
                    source_url=nr.source_url,
                    collection_timestamp=nr.collection_timestamp,
                    geocoding_method=nr.geocoding_method,
                    geocoding_confidence=nr.geocoding_confidence,
                    spatial_precision=nr.spatial_precision,
                    data_quality_score=nr.data_quality_score,
                    dataset_version=nr.dataset_version,
                    original_category=nr.original_category,
                    original_source_record_id=nr.original_source_record_id,
                    processing_version=nr.processing_version,
                )
            )
        return records

    def _geocode_records(self, records: list[Any]) -> list[Any]:
        """Geocode records without coordinates (placeholder)."""
        # In production, use actual geocoder
        return records


def main():
    parser = argparse.ArgumentParser(description="Women Safety Dataset Build Pipeline")
    parser.add_argument(
        "--config", default="ml/data/config/sources.yaml", help="Path to config file"
    )
    parser.add_argument(
        "--offline", action="store_true", help="Run in offline mode (use cached data)"
    )
    parser.add_argument("--output-dir", help="Override output directory")
    args = parser.parse_args()

    config = PipelineConfig(Path(args.config))

    if args.offline:
        config.config["pipeline"]["offline_mode"] = True

    if args.output_dir:
        config.config["pipeline"]["output_dir"] = args.output_dir

    pipeline = DatasetPipeline(config)
    result = pipeline.run()

    print(json.dumps(result, indent=2))
    return 0 if result.get("status") == "success" else 1


if __name__ == "__main__":
    sys.exit(main())
