"""Base ingestion adapter interface.

Each data source implements its own adapter that produces canonical records.
"""

from __future__ import annotations

import abc
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RawRecord:
    """Raw record from source before normalization."""

    source_id: str
    source_record_id: str
    raw_data: dict[str, Any]
    fetched_at: str
    source_checksum: str


@dataclass(frozen=True)
class IngestionResult:
    """Result of ingesting a source."""

    source_id: str
    records: list[RawRecord]
    total_fetched: int
    total_valid: int
    total_invalid: int
    errors: list[str]
    fetched_at: str
    source_checksum: str


class BaseIngestionAdapter(abc.ABC):
    """Abstract base class for source-specific ingestion adapters."""

    def __init__(self, source_config: dict[str, Any], cache_dir: Path):
        self.source_config = source_config
        self.source_id = source_config["source_id"]
        self.cache_dir = cache_dir / self.source_id
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    @abc.abstractmethod
    def fetch(self, force: bool = False) -> IngestionResult:
        """Fetch data from source. Implement retry, timeout, checksum validation."""
        pass

    @abc.abstractmethod
    def parse(self, raw_content: bytes) -> list[dict[str, Any]]:
        """Parse raw content into list of raw records."""
        pass

    def _compute_checksum(self, content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()

    def _get_cached_path(self, filename: str) -> Path:
        return self.cache_dir / filename

    def _load_cache_metadata(self) -> dict[str, Any] | None:
        meta_path = self.cache_dir / "metadata.json"
        if meta_path.exists():
            return json.loads(meta_path.read_text(encoding="utf-8"))
        return None

    def _save_cache_metadata(self, metadata: dict[str, Any]) -> None:
        meta_path = self.cache_dir / "metadata.json"
        meta_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")

    def _should_refetch(self, force: bool, remote_checksum: str | None = None) -> bool:
        if force:
            return True
        meta = self._load_cache_metadata()
        if not meta:
            return True
        if remote_checksum and meta.get("checksum") != remote_checksum:
            return True
        return False


class CSVIngestionMixin:
    """Mixin for CSV-based sources."""

    def parse_csv(self, content: bytes, encoding: str = "utf-8") -> list[dict[str, Any]]:
        import csv
        from io import StringIO

        text = content.decode(encoding)
        reader = csv.DictReader(StringIO(text))
        return [dict(row) for row in reader]


class JSONIngestionMixin:
    """Mixin for JSON-based sources."""

    def parse_json(self, content: bytes, encoding: str = "utf-8") -> list[dict[str, Any]]:
        data = json.loads(content.decode(encoding))
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "records" in data:
            return data["records"]
        if isinstance(data, dict) and "features" in data:  # GeoJSON
            return [feat.get("properties", {}) for feat in data["features"]]
        return [data]


class GeoJSONIngestionMixin:
    """Mixin for GeoJSON sources."""

    def parse_geojson(self, content: bytes, encoding: str = "utf-8") -> list[dict[str, Any]]:
        data = json.loads(content.decode(encoding))
        records = []
        for feature in data.get("features", []):
            props = feature.get("properties", {})
            geom = feature.get("geometry")
            if geom and geom.get("type") == "Point":
                coords = geom.get("coordinates", [])
                if len(coords) >= 2:
                    props["longitude"] = coords[0]
                    props["latitude"] = coords[1]
            records.append(props)
        return records


class ParquetIngestionMixin:
    """Mixin for Parquet sources."""

    def parse_parquet(self, content: bytes) -> list[dict[str, Any]]:
        from io import BytesIO

        import pyarrow.parquet as pq

        table = pq.read_table(BytesIO(content))
        return table.to_pylist()
