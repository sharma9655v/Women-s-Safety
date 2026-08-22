"""Government open-data source adapter.

Parses CSV-style government crime datasets (NCRB, state open data portals)
into raw records for the normalization stage.

IMPORTANT: This adapter does NOT fabricate records. It only parses content
that was actually downloaded from an approved, enabled source in
sources.yaml. If the source provides no rows, it returns zero rows.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from ml.data.ingestion.base import (
    BaseIngestionAdapter,
    CSVIngestionMixin,
    IngestionResult,
    RawRecord,
)
from ml.data.ingestion.download import download_with_cache


class GovernmentCrimeSource(BaseIngestionAdapter, CSVIngestionMixin):
    """Adapter for government open-data CSV datasets (NCRB, state portals).

    Expects source_config to contain:
      - source_id: unique id matching sources.yaml
      - source_url: direct download URL of the dataset file
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

        if result.from_cache and not force:
            # Reuse cached parse output when checksum unchanged
            parsed_cache = self._get_cached_path("parsed.json")
            if parsed_cache.exists():
                meta = self._load_cache_metadata() or {}
                if meta.get("checksum") == result.checksum:
                    rows = json.loads(parsed_cache.read_text(encoding="utf-8"))
                    return self._build_result(rows, result.checksum, cached=True)

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

        # Cache parsed output keyed by checksum
        parsed_cache = self._get_cached_path("parsed.json")
        parsed_cache.write_text(json.dumps(rows), encoding="utf-8")
        self._save_cache_metadata(
            {
                "checksum": result.checksum,
                "etag": result.etag,
                "last_modified": result.last_modified,
                "downloaded_at": result.downloaded_at,
                "row_count": len(rows),
            }
        )

        return self._build_result(rows, result.checksum, cached=False)

    def parse(self, raw_content: bytes) -> list[dict[str, Any]]:
        """Parse CSV bytes into raw row dicts."""
        return self.parse_csv(raw_content)

    def _build_result(
        self, rows: list[dict[str, Any]], checksum: str, cached: bool
    ) -> IngestionResult:
        fetched_at = datetime.now(UTC).isoformat()
        records = [
            RawRecord(
                source_id=self.source_id,
                source_record_id=str(row.get("id") or row.get("record_id") or idx),
                raw_data=row,
                fetched_at=fetched_at,
                source_checksum=checksum,
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
            source_checksum=checksum,
        )
