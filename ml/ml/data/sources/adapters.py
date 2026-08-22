"""OpenStreetMap, government, and research dataset adapters."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from ml.data.ingestion.base import (
    BaseIngestionAdapter,
    CSVIngestionMixin,
    GeoJSONIngestionMixin,
    IngestionResult,
    JSONIngestionMixin,
    RawRecord,
)
from ml.data.ingestion.download import download_with_cache
from ml.data.sources.government import GovernmentCrimeSource  # noqa: F401 (re-export)


class OSMSource(BaseIngestionAdapter, GeoJSONIngestionMixin):
    """Adapter for OSM-derived GeoJSON extracts (e.g. lighting tags).

    Only parses content downloaded from an approved source URL.
    License compliance (ODbL attribution/share-alike) is enforced by the
    source registry — this adapter never bypasses it.
    """

    def fetch(self, force: bool = False) -> IngestionResult:
        url = self.source_config.get("source_url")
        if not url:
            return IngestionResult(
                source_id=self.source_id,
                records=[],
                total_fetched=0,
                total_valid=0,
                total_invalid=0,
                errors=["No source_url configured"],
                fetched_at=datetime.now(UTC).isoformat(),
                source_checksum="",
            )

        result = download_with_cache(url, self.cache_dir, force=force)
        try:
            rows = self.parse(result.content)
        except Exception as exc:
            return IngestionResult(
                source_id=self.source_id,
                records=[],
                total_fetched=0,
                total_valid=0,
                total_invalid=0,
                errors=[f"Parse failed: {exc}"],
                fetched_at=result.downloaded_at,
                source_checksum=result.checksum,
            )

        fetched_at = datetime.now(UTC).isoformat()
        records = [
            RawRecord(
                source_id=self.source_id,
                source_record_id=str(row.get("osm_id") or idx),
                raw_data=row,
                fetched_at=fetched_at,
                source_checksum=result.checksum,
            )
            for idx, row in enumerate(rows)
        ]
        return IngestionResult(
            source_id=self.source_id,
            records=records,
            total_fetched=len(records),
            total_valid=len(records),
            total_invalid=0,
            errors=[],
            fetched_at=fetched_at,
            source_checksum=result.checksum,
        )

    def parse(self, raw_content: bytes) -> list[dict[str, Any]]:
        return self.parse_geojson(raw_content)


class ResearchDatasetSource(BaseIngestionAdapter, CSVIngestionMixin, JSONIngestionMixin):
    """Adapter for licensed academic/research datasets (CSV or JSON).

    The dataset license must be recorded in sources.yaml before enabling;
    this adapter refuses to run when the license field is missing/unknown.
    """

    KNOWN_LICENSES = {
        "CC BY 4.0",
        "CC BY-SA 4.0",
        "CC0 1.0",
        "ODbL 1.0",
        "Open Government Data License - India",
        "Public Domain",
    }

    def fetch(self, force: bool = False) -> IngestionResult:
        license_name = (self.source_config.get("license") or "").strip()
        if not license_name or license_name.lower() in ("unknown", "tbd", ""):
            # Fail loudly: unknown license is a hard stop per pipeline rules
            return IngestionResult(
                source_id=self.source_id,
                records=[],
                total_fetched=0,
                total_valid=0,
                total_invalid=0,
                errors=[
                    "License is unknown — refusing to ingest. "
                    "Record an explicit license in sources.yaml."
                ],
                fetched_at=datetime.now(UTC).isoformat(),
                source_checksum="",
            )

        url = self.source_config.get("source_url")
        if not url:
            return IngestionResult(
                source_id=self.source_id,
                records=[],
                total_fetched=0,
                total_valid=0,
                total_invalid=0,
                errors=["No source_url configured"],
                fetched_at=datetime.now(UTC).isoformat(),
                source_checksum="",
            )

        result = download_with_cache(url, self.cache_dir, force=force)
        try:
            rows = self._parse_auto(result.content)
        except Exception as exc:
            return IngestionResult(
                source_id=self.source_id,
                records=[],
                total_fetched=0,
                total_valid=0,
                total_invalid=0,
                errors=[f"Parse failed: {exc}"],
                fetched_at=result.downloaded_at,
                source_checksum=result.checksum,
            )

        fetched_at = datetime.now(UTC).isoformat()
        records = [
            RawRecord(
                source_id=self.source_id,
                source_record_id=str(row.get("id") or row.get("record_id") or idx),
                raw_data=row,
                fetched_at=fetched_at,
                source_checksum=result.checksum,
            )
            for idx, row in enumerate(rows)
        ]
        return IngestionResult(
            source_id=self.source_id,
            records=records,
            total_fetched=len(records),
            total_valid=len(records),
            total_invalid=0,
            errors=[],
            fetched_at=fetched_at,
            source_checksum=result.checksum,
        )

    def parse(self, raw_content: bytes) -> list[dict[str, Any]]:
        return self._parse_auto(raw_content)

    def _parse_auto(self, raw_content: bytes) -> list[dict[str, Any]]:
        """Auto-detect CSV vs JSON by first non-whitespace byte."""
        stripped = raw_content.lstrip()
        if stripped.startswith(b"{") or stripped.startswith(b"["):
            return self.parse_json(raw_content)
        return self.parse_csv(raw_content)


def get_adapter(source_config: dict[str, Any], cache_dir) -> BaseIngestionAdapter:
    """Factory: build the right adapter for a source based on its parser field."""
    parser = source_config.get("parser", "")
    adapters = {
        "ncrb_csv": GovernmentCrimeSource,
        "municipal_csv": GovernmentCrimeSource,
        "government_csv": GovernmentCrimeSource,
        "osm_geojson": OSMSource,
        "osm_pbf": OSMSource,  # GeoJSON path; PBF would need osmium (not bundled)
        "research_csv": ResearchDatasetSource,
        "research_json": ResearchDatasetSource,
    }
    adapter_cls = adapters.get(parser)
    if adapter_cls is None:
        raise ValueError(
            f"Unknown parser {parser!r} for source {source_config.get('source_id')!r}. "
            f"Known parsers: {sorted(adapters)}"
        )
    return adapter_cls(source_config, cache_dir)


# Re-export for build_dataset wiring
GovernmentCrimeSourceType = GovernmentCrimeSource
