"""Dataset versioning and lineage tracking."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ml.data.config.schema import DatasetRecord


@dataclass(frozen=True)
class SourceVersion:
    """Version info for a single source."""

    source_id: str
    source_name: str
    version: str
    record_count: int
    checksum: str
    fetched_at: str


@dataclass(frozen=True)
class DatasetManifest:
    """Complete dataset manifest with lineage."""

    dataset_version: str
    created_at: str
    record_count: int
    sources: list[SourceVersion]
    feature_schema_version: str
    geocoding_version: str
    processing_version: str
    validation_report_path: str | None
    quality_report_path: str | None
    dataset_hash: str
    geographic_coverage: dict[str, Any] = field(default_factory=dict)
    temporal_coverage: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_version": self.dataset_version,
            "created_at": self.created_at,
            "record_count": self.record_count,
            "sources": [vars(s) for s in self.sources],
            "feature_schema_version": self.feature_schema_version,
            "geocoding_version": self.geocoding_version,
            "processing_version": self.processing_version,
            "validation_report_path": self.validation_report_path,
            "quality_report_path": self.quality_report_path,
            "dataset_hash": self.dataset_hash,
            "geographic_coverage": self.geographic_coverage,
            "temporal_coverage": self.temporal_coverage,
        }


@dataclass(frozen=True)
class LineageRecord:
    """Lineage record for a single processed record."""

    record_id: str
    source_id: str
    original_source_record_id: str | None
    processing_stages: list[str]
    processing_versions: dict[str, str]
    dataset_version: str
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "source_id": self.source_id,
            "original_source_record_id": self.original_source_record_id,
            "processing_stages": self.processing_stages,
            "processing_versions": self.processing_versions,
            "dataset_version": self.dataset_version,
            "created_at": self.created_at,
        }


class VersionManager:
    """Manage dataset versions and lineage."""

    def __init__(self, versions_dir: Path):
        self.versions_dir = versions_dir
        self.versions_dir.mkdir(parents=True, exist_ok=True)

    def generate_version(self) -> str:
        """Generate a unique dataset version (timestamp + collision suffix).

        Two builds within the same second must never share a version:
        datasets are immutable and never overwritten.
        """
        base = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
        candidate = base
        counter = 0
        while (self.versions_dir / f"manifest_{candidate}.json").exists():
            counter += 1
            candidate = f"{base}-{counter}"
        return candidate

    def compute_dataset_hash(self, records: list[DatasetRecord]) -> str:
        """Compute deterministic hash of dataset."""
        # Sort by record_id for determinism
        sorted_records = sorted(records, key=lambda r: r.record_id)
        content = "".join(r.record_id for r in sorted_records)
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def create_manifest(
        self,
        records: list[DatasetRecord],
        source_versions: list[SourceVersion],
        feature_schema_version: str,
        geocoding_version: str,
        processing_version: str,
        validation_report_path: str | None = None,
        quality_report_path: str | None = None,
    ) -> DatasetManifest:
        """Create dataset manifest."""
        dataset_version = self.generate_version()
        created_at = datetime.now(UTC).isoformat() + "Z"

        # Compute geographic coverage
        coords = [
            (r.latitude, r.longitude)
            for r in records
            if r.latitude is not None and r.longitude is not None
        ]
        if coords:
            lats, lons = zip(*coords, strict=True)
            geographic_coverage = {
                "min_lat": min(lats),
                "max_lat": max(lats),
                "min_lon": min(lons),
                "max_lon": max(lons),
                "center_lat": sum(lats) / len(lats),
                "center_lon": sum(lons) / len(lons),
            }
        else:
            geographic_coverage = {}

        # Compute temporal coverage
        dates = [r.incident_date for r in records if r.incident_date]
        if dates:
            temporal_coverage = {
                "min_date": min(dates),
                "max_date": max(dates),
            }
        else:
            temporal_coverage = {}

        dataset_hash = self.compute_dataset_hash(records)

        return DatasetManifest(
            dataset_version=dataset_version,
            created_at=created_at,
            record_count=len(records),
            sources=source_versions,
            feature_schema_version=feature_schema_version,
            geocoding_version=geocoding_version,
            processing_version=processing_version,
            validation_report_path=validation_report_path,
            quality_report_path=quality_report_path,
            dataset_hash=dataset_hash,
            geographic_coverage=geographic_coverage,
            temporal_coverage=temporal_coverage,
        )

    def save_manifest(self, manifest: DatasetManifest) -> Path:
        """Save manifest to versions directory."""
        manifest_path = self.versions_dir / f"manifest_{manifest.dataset_version}.json"
        manifest_path.write_text(json.dumps(manifest.to_dict(), indent=2) + "\n", encoding="utf-8")
        return manifest_path

    def load_manifest(self, dataset_version: str) -> DatasetManifest | None:
        """Load manifest by version."""
        manifest_path = self.versions_dir / f"manifest_{dataset_version}.json"
        if not manifest_path.exists():
            return None
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        # Reconstruct - simplified for now
        return DatasetManifest(**data)

    def list_versions(self) -> list[str]:
        """List all available dataset versions."""
        versions = []
        for path in self.versions_dir.glob("manifest_*.json"):
            version = path.stem.replace("manifest_", "")
            versions.append(version)
        return sorted(versions, reverse=True)


class LineageTracker:
    """Track lineage for individual records."""

    def __init__(self, lineage_dir: Path):
        self.lineage_dir = lineage_dir
        self.lineage_dir.mkdir(parents=True, exist_ok=True)

    def track_record(
        self,
        record: DatasetRecord,
        processing_stages: list[str],
        processing_versions: dict[str, str],
    ) -> LineageRecord:
        """Create lineage record for a processed record."""
        return LineageRecord(
            record_id=record.record_id,
            source_id=record.source_id,
            original_source_record_id=record.original_source_record_id,
            processing_stages=processing_stages,
            processing_versions=processing_versions,
            dataset_version=record.dataset_version,
            created_at=datetime.now(UTC).isoformat() + "Z",
        )

    def save_lineage(self, lineage_records: list[LineageRecord], dataset_version: str) -> Path:
        """Save lineage records."""
        lineage_path = self.lineage_dir / f"lineage_{dataset_version}.jsonl"
        with lineage_path.open("w", encoding="utf-8") as f:
            for lr in lineage_records:
                f.write(json.dumps(lr.to_dict()) + "\n")
        return lineage_path


def create_source_version(
    source_id: str,
    source_name: str,
    records: list[DatasetRecord],
    checksum: str,
) -> SourceVersion:
    """Create source version info from records."""
    source_records = [r for r in records if r.source_id == source_id]
    return SourceVersion(
        source_id=source_id,
        source_name=source_name,
        version=datetime.now(UTC).strftime("%Y%m%dT%H%M%S"),
        record_count=len(source_records),
        checksum=checksum,
        fetched_at=datetime.now(UTC).isoformat() + "Z",
    )
