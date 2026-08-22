"""Deterministic deduplication for dataset records."""

from __future__ import annotations

from dataclasses import dataclass

from ml.data.config.schema import DatasetRecord


@dataclass(frozen=True)
class DeduplicationResult:
    """Result of deduplication."""

    unique_records: list[DatasetRecord]
    duplicate_groups: list[list[DatasetRecord]]
    total_input: int
    total_unique: int
    total_duplicates: int


class Deduplicator:
    """Deterministic deduplication based on configurable match fields."""

    def __init__(
        self,
        match_fields: list[str] | None = None,
        exact_match_fields: list[str] | None = None,
    ):
        self.match_fields = match_fields or [
            "source_id",
            "original_source_record_id",
            "incident_date",
            "latitude",
            "longitude",
            "crime_category",
        ]
        self.exact_match_fields = exact_match_fields or [
            "source_id",
            "original_source_record_id",
        ]

    def _make_key(self, record: DatasetRecord) -> tuple:
        """Create a deduplication key from match fields."""
        key_parts = []
        for field in self.match_fields:
            value = getattr(record, field, None)
            if value is None:
                key_parts.append("__NULL__")
            elif isinstance(value, float):
                # Round coordinates to 4 decimal places (~11m)
                if field in ("latitude", "longitude"):
                    key_parts.append(round(value, 4))
                else:
                    key_parts.append(value)
            else:
                key_parts.append(str(value).strip().lower())
        return tuple(key_parts)

    def _exact_key(self, record: DatasetRecord) -> tuple:
        """Create exact match key."""
        key_parts = []
        for field in self.exact_match_fields:
            value = getattr(record, field, None)
            if value is None:
                key_parts.append("__NULL__")
            else:
                key_parts.append(str(value).strip())
        return tuple(key_parts)

    def deduplicate(self, records: list[DatasetRecord]) -> DeduplicationResult:
        """Remove duplicates, keeping the highest quality record from each group."""
        if not records:
            return DeduplicationResult(
                unique_records=[],
                duplicate_groups=[],
                total_input=0,
                total_unique=0,
                total_duplicates=0,
            )

        # Group by match key
        groups: dict[tuple, list[DatasetRecord]] = {}
        for record in records:
            key = self._make_key(record)
            groups.setdefault(key, []).append(record)

        # Also group by exact key for tracking
        exact_groups: dict[tuple, list[DatasetRecord]] = {}
        for record in records:
            key = self._exact_key(record)
            exact_groups.setdefault(key, []).append(record)

        unique_records = []
        duplicate_groups = []

        for group in groups.values():
            if len(group) == 1:
                unique_records.append(group[0])
            else:
                # Keep the record with highest data_quality_score
                # If tied, keep the first (deterministic)
                best = max(group, key=lambda r: r.data_quality_score or 0.0)
                unique_records.append(best)
                duplicate_groups.append(group)

        return DeduplicationResult(
            unique_records=unique_records,
            duplicate_groups=duplicate_groups,
            total_input=len(records),
            total_unique=len(unique_records),
            total_duplicates=len(records) - len(unique_records),
        )


def deduplicate_records(
    records: list[DatasetRecord],
    match_fields: list[str] | None = None,
    exact_match_fields: list[str] | None = None,
) -> DeduplicationResult:
    """Convenience function to deduplicate records."""
    deduplicator = Deduplicator(match_fields=match_fields, exact_match_fields=exact_match_fields)
    return deduplicator.deduplicate(records)
