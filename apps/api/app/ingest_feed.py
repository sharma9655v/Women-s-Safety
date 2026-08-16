"""Validated ingestion harness for real civic/NGO data feeds (P2 groundwork).

This is infrastructure ONLY: it ships with zero real data. It provides the
validated path for real feeds when they arrive, and enforces the project's
integrity rules on every row before anything is written:

  - required schema with strict type checks,
  - observation types limited to the evidence model's vocabulary,
  - reliability in [0, 1], observed_at in the past (never future-dated),
  - reporter identity is never accepted: PII/description columns are dropped
    with a warning or cause an error (never stored),
  - duplicate rows are dropped via the canonical evidence_hash,
  - provenance is mandatory (--source feed name + --licence) and recorded in
    a versioned manifest (sha256),
  - DB writes require an explicit --write flag; the default is a dry run.

Rows with source_type != demo_seed count toward the ML gate once VERIFIED —
the harness prints that warning on every run. It cannot be used to silently
inflate the dataset: each inserted row is keyed by evidence_hash
(ON CONFLICT DO NOTHING), same as the demo seeder.

Usage:
    uv run python -m app.ingest_feed feeds/my-feed.csv --source my_feed --licence "CC BY 4.0"
    uv run python -m app.ingest_feed feeds/my-feed.jsonl --source my_feed --write

Exit codes: 0 ok, 2 unreachable PostGIS on --write, 3 validation failed.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from sqlalchemy import text

from app.db import make_engine

from app.config import settings
from app.evidence.engine import evidence_hash
from app.evidence.states import OBSERVATION_TYPES, VerificationState

REPO_ROOT = Path(__file__).resolve().parents[3]

REQUIRED_COLUMNS = {
    "segment_id": "int",
    "observation_type": "str",
    "value_json": "json_object",
    "observed_at": "iso_datetime",
    "source_reliability": "float01",
    "verification_state": "state",
}

# Columns that could carry reporter identity or free text. Never stored;
# dropped with a warning (or an error without --drop-columns).
PII_OR_TEXT_COLUMNS = {
    "description",
    "text",
    "notes",
    "comment",
    "reporter",
    "name",
    "email",
    "phone",
    "user_id",
    "image",
    "photo",
    "address",
}

VALID_STATES = {state.value for state in VerificationState}


@dataclass
class RowError:
    row_number: int
    column: str
    reason: str


@dataclass
class ValidationReport:
    valid: list[dict[str, object]] = field(default_factory=list)
    errors: list[RowError] = field(default_factory=list)
    duplicates_dropped: int = 0
    dropped_columns: list[str] = field(default_factory=list)
    pii_columns_dropped: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def _parse_iso_datetime(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


def _coerce(column: str, value: object) -> tuple[object, str | None]:
    """Type-check one cell. Returns (coerced_value, error_reason)."""
    if value is None or (isinstance(value, str) and value.strip() == ""):
        return None, "empty value"
    if column == "segment_id":
        try:
            return int(str(value)), None
        except (TypeError, ValueError):
            return None, "must be an integer"
    if column == "observation_type":
        if value not in OBSERVATION_TYPES:
            return None, f"unknown observation type '{value}'"
        return value, None
    if column == "value_json":
        if isinstance(value, dict):
            return value, None
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError:
                return None, "value_json is not valid JSON"
            if not isinstance(parsed, dict):
                return None, "value_json must be a JSON object"
            return parsed, None
        return None, "value_json must be a JSON object"
    if column == "observed_at":
        parsed = _parse_iso_datetime(value)
        if parsed is None:
            return None, "must be an ISO-8601 datetime"
        return parsed, None
    if column == "source_reliability":
        try:
            reliability = float(str(value))
        except (TypeError, ValueError):
            return None, "must be a number"
        if not 0.0 <= reliability <= 1.0:
            return None, "reliability must be in [0, 1]"
        return reliability, None
    if column == "verification_state":
        if value not in VALID_STATES:
            return None, f"unknown verification state '{value}'"
        return value, None
    return value, None


def validate_rows(
    rows: list[dict[str, object]],
    source_type: str,
    *,
    drop_columns: bool = False,
    now: datetime | None = None,
) -> ValidationReport:
    """Validate parsed feed rows against the evidence schema."""
    now = now or datetime.now(UTC)
    report = ValidationReport()
    seen_hashes: set[str] = set()

    for row_number, row in enumerate(rows, start=2):  # row 1 = header
        # Unknown columns: error by default; with --drop-columns they are
        # dropped. PII/text columns are never stored under any flag.
        unknown = [col for col in row if col not in REQUIRED_COLUMNS]
        for col in unknown:
            if col.lower() in PII_OR_TEXT_COLUMNS:
                report.pii_columns_dropped.append(col)
            else:
                report.dropped_columns.append(col)
            if not drop_columns and col.lower() not in PII_OR_TEXT_COLUMNS:
                report.errors.append(
                    RowError(row_number, col, f"unknown column (use --drop-columns to drop): {col}")
                )
            if col.lower() in PII_OR_TEXT_COLUMNS:
                row.pop(col, None)

        cleaned: dict[str, object] = {}
        valid = True
        for column in REQUIRED_COLUMNS:
            if column not in row:
                report.errors.append(RowError(row_number, column, "missing required column"))
                valid = False
                continue
            coerced, reason = _coerce(column, row[column])
            if reason is not None:
                report.errors.append(RowError(row_number, column, reason))
                valid = False
                continue
            cleaned[column] = coerced
        if not valid:
            continue

        # Future-dated observations are rejected: never store what cannot
        # yet be true.
        segment_id = cast(int, cleaned["segment_id"])
        observation_type = cast(str, cleaned["observation_type"])
        value = cast(dict[str, object], cleaned["value_json"])
        observed_at = cast(datetime, cleaned["observed_at"])
        if observed_at > now:
            report.errors.append(RowError(row_number, "observed_at", "must not be in the future"))
            continue

        hash_value = evidence_hash(
            segment_id,
            source_type,
            observation_type,
            value,
            observed_at,
        )
        if hash_value in seen_hashes:
            report.duplicates_dropped += 1
            continue
        seen_hashes.add(hash_value)
        cleaned["evidence_hash"] = hash_value
        report.valid.append(cleaned)

    report.dropped_columns = sorted(set(report.dropped_columns))
    report.pii_columns_dropped = sorted(set(report.pii_columns_dropped))
    return report


def read_feed(path: Path) -> list[dict[str, object]]:
    """Parse CSV or JSON-lines. CSV cells are kept as strings (coerced by
    validate_rows); JSON-lines values keep native types."""
    raw = path.read_text(encoding="utf-8-sig")
    if path.suffix.lower() == ".jsonl":
        rows: list[dict[str, object]] = []
        for line in raw.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            parsed = json.loads(stripped)
            if not isinstance(parsed, dict):
                raise ValueError(f"JSONL line is not an object: {line[:80]}")
            rows.append(parsed)
        return rows
    if path.suffix.lower() in (".csv", ""):
        reader = csv.DictReader(io.StringIO(raw))
        if not reader.fieldnames:
            raise ValueError("CSV has no header row")
        return [dict(row) for row in reader]
    raise ValueError(f"unsupported feed format: {path.suffix}")


def run_ingest(
    feed_path: Path,
    source_type: str,
    licence: str,
    *,
    drop_columns: bool = False,
    write: bool = False,
    out_dir: Path | None = None,
    now: datetime | None = None,
) -> dict[str, object]:
    """Validate and (optionally) persist a feed. Returns the run report."""
    now = now or datetime.now(UTC)
    source_type = source_type.strip().lower().replace(" ", "_")
    if source_type == "demo_seed":
        raise ValueError("source_type 'demo_seed' is reserved for the demo seeder")
    if "demo" in source_type:
        raise ValueError("feed source_type must not contain 'demo'")

    rows = read_feed(feed_path)
    report = validate_rows(rows, source_type, drop_columns=drop_columns, now=now)

    result: dict[str, object] = {
        "feed": feed_path.name,
        "source_type": source_type,
        "licence": licence,
        "validated_at": now.isoformat(timespec="seconds"),
        "rows_read": len(rows),
        "rows_valid": len(report.valid),
        "rows_rejected": len(report.errors),
        "duplicates_dropped": report.duplicates_dropped,
        "dropped_columns": report.dropped_columns,
        "pii_columns_dropped": report.pii_columns_dropped,
        "errors": [
            {"row": e.row_number, "column": e.column, "reason": e.reason} for e in report.errors
        ],
        "written_to_db": False,
        "manifest_path": None,
        "snapshot_path": None,
        "note": "Infrastructure harness only: this run ships no real data by "
        "itself. Rows with source_type != demo_seed count toward the ML gate "
        "once VERIFIED.",
    }

    if not report.ok:
        result["error"] = "validation failed; nothing was written"
        return result

    out_dir = out_dir or REPO_ROOT / "data" / "versions"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = now.strftime("%Y%m%dT%H%M%S")

    payload = {
        "description": f"Validated feed '{source_type}' ({licence}). "
        "Counts toward the ML gate only when VERIFIED.",
        "generated_at": now.isoformat(),
        "count": len(report.valid),
        "source_type": source_type,
        "observations": [
            {
                "segment_id": cast(int, v["segment_id"]),
                "observation_type": v["observation_type"],
                "value": v["value_json"],
                "observed_at": cast(datetime, v["observed_at"]).isoformat(),
                "source_reliability": cast(float, v["source_reliability"]),
                "verification_state": v["verification_state"],
            }
            for v in report.valid
        ],
    }
    manifest = {
        "name": f"feed-{source_type}",
        "generated_at": now.isoformat(),
        "observation_count": len(report.valid),
        "rows_rejected": len(report.errors),
        "duplicates_dropped": report.duplicates_dropped,
        "source_type": source_type,
        "licence": licence,
        "feed_file": feed_path.name,
        "sha256": hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest(),
    }

    snapshot_path = out_dir / f"feed-{source_type}-{ts}.json"
    snapshot_path.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
    manifest_path = out_dir / f"feed-{source_type}-{ts}.manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8")
    result["manifest_path"] = str(manifest_path)
    result["snapshot_path"] = str(snapshot_path)

    if write:
        engine = make_engine()
        try:
            with engine.begin() as conn:
                conn.execute(text("SELECT 1"))
        except Exception as exc:
            result["error"] = f"PostGIS unreachable: {exc}"
            return result
        with engine.begin() as conn:
            inserted = 0
            for row in report.valid:
                conn.execute(
                    text(
                        "INSERT INTO safety_observations "
                        "(segment_id, source_type, observation_type, value_json, observed_at, "
                        "source_reliability, confidence, verification_state, evidence_hash) "
                        "VALUES (:segment_id, :source_type, :observation_type, :value_json, "
                        ":observed_at, :source_reliability, :confidence, :verification_state, "
                        ":evidence_hash) ON CONFLICT (evidence_hash) DO NOTHING"
                    ),
                    {
                        "segment_id": cast(int, row["segment_id"]),
                        "source_type": source_type,
                        "observation_type": row["observation_type"],
                        "value_json": json.dumps(row["value_json"], sort_keys=True),
                        "observed_at": cast(datetime, row["observed_at"]),
                        "source_reliability": cast(float, row["source_reliability"]),
                        "confidence": 0.5,
                        "verification_state": row["verification_state"],
                        "evidence_hash": row["evidence_hash"],
                    },
                )
                inserted += 1
        result["written_to_db"] = True
        result["inserted"] = inserted

    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate and ingest a real data feed.")
    parser.add_argument("feed", type=Path, help="CSV or JSONL feed file")
    parser.add_argument("--source", required=True, help="feed name (becomes source_type)")
    parser.add_argument("--licence", required=True, help="licence/attribution for the feed")
    parser.add_argument("--drop-columns", action="store_true", help="drop unknown columns")
    parser.add_argument("--write", action="store_true", help="write validated rows to PostGIS")
    args = parser.parse_args()

    try:
        result = run_ingest(
            args.feed,
            args.source,
            args.licence,
            drop_columns=args.drop_columns,
            write=args.write,
        )
    except (ValueError, OSError) as exc:
        print(f"ERROR: {exc}")
        return 3

    print(json.dumps(result, indent=1))
    if "error" in result:
        if "PostGIS" in str(result["error"]):
            return 2
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
