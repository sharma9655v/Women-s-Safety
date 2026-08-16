import json
from datetime import UTC, datetime, timedelta

import pytest

from app.ingest_feed import (
    run_ingest,
    validate_rows,
)
from app.seed_demo import DEMO_SOURCE

NOW = datetime(2026, 8, 15, 12, 0, tzinfo=UTC)

BASE_ROW: dict[str, object] = {
    "segment_id": 456736,
    "observation_type": "harassment",
    "value_json": {"incident": True},
    "observed_at": "2026-08-10T10:00:00Z",
    "source_reliability": 0.7,
    "verification_state": "REPORTED",
}


def _csv(rows: list[dict[str, object]]) -> str:
    header = list(BASE_ROW)
    lines = [",".join(header)]
    for row in rows:
        values = []
        for col in header:
            value = row.get(col, "")
            if col == "value_json":
                value = json.dumps(value)
            values.append(str(value))
        lines.append(",".join(values))
    return "\n".join(lines)


def _write_csv(tmp_path, rows: list[dict[str, object]]):
    path = tmp_path / "feed.csv"
    path.write_text(_csv(rows), encoding="utf-8")
    return path


def test_valid_rows_pass() -> None:
    report = validate_rows([dict(BASE_ROW)], source_type="civic_feed", now=NOW)
    assert report.ok
    assert len(report.valid) == 1
    assert isinstance(report.valid[0]["evidence_hash"], str)
    assert len(report.valid[0]["evidence_hash"]) == 64


def test_duplicates_dropped_via_evidence_hash() -> None:
    report = validate_rows([dict(BASE_ROW), dict(BASE_ROW)], source_type="civic_feed", now=NOW)
    assert len(report.valid) == 1
    assert report.duplicates_dropped == 1


def test_same_observation_different_value_is_not_a_duplicate() -> None:
    other = dict(BASE_ROW)
    other["value_json"] = {"incident": False}
    report = validate_rows([dict(BASE_ROW), other], source_type="civic_feed", now=NOW)
    assert len(report.valid) == 2
    assert report.duplicates_dropped == 0


def test_future_observation_rejected() -> None:
    row = dict(BASE_ROW)
    row["observed_at"] = (NOW + timedelta(days=2)).isoformat()
    report = validate_rows([row], source_type="civic_feed", now=NOW)
    assert not report.ok
    assert report.errors[0].reason == "must not be in the future"


def test_unknown_observation_type_rejected() -> None:
    row = dict(BASE_ROW)
    row["observation_type"] = "alien_sighting"
    report = validate_rows([row], source_type="civic_feed", now=NOW)
    assert not report.ok
    assert "unknown observation type" in report.errors[0].reason


def test_reliability_out_of_range_rejected() -> None:
    for bad in (-0.1, 1.5):
        row = dict(BASE_ROW)
        row["source_reliability"] = bad
        report = validate_rows([row], source_type="civic_feed", now=NOW)
        assert not report.ok
        assert "reliability" in report.errors[0].reason


def test_unknown_column_errors_without_flag() -> None:
    row = dict(BASE_ROW)
    row["mystery_column"] = "x"
    report = validate_rows([row], source_type="civic_feed", now=NOW, drop_columns=False)
    assert not report.ok
    assert "unknown column" in report.errors[0].reason


def test_drop_columns_allows_unknown_non_pii_columns() -> None:
    row = dict(BASE_ROW)
    row["source_url"] = "https://example.in/feed"
    report = validate_rows([row], source_type="civic_feed", now=NOW, drop_columns=True)
    assert report.ok
    assert "source_url" in report.dropped_columns


def test_pii_columns_never_stored_even_with_flag() -> None:
    row = dict(BASE_ROW)
    row["description"] = "woman followed near bus stop"
    row["reporter"] = "A. Singh"
    report = validate_rows([row], source_type="civic_feed", now=NOW, drop_columns=True)
    assert report.ok
    assert "description" in report.pii_columns_dropped
    assert "reporter" in report.pii_columns_dropped
    assert "description" not in report.valid[0]
    assert "reporter" not in report.valid[0]


def test_demo_seed_source_type_is_reserved(tmp_path) -> None:
    path = _write_csv(tmp_path, [dict(BASE_ROW)])
    with pytest.raises(ValueError):
        run_ingest(path, DEMO_SOURCE, "CC BY 4.0", out_dir=tmp_path, now=NOW)


def test_source_type_must_not_contain_demo(tmp_path) -> None:
    path = _write_csv(tmp_path, [dict(BASE_ROW)])
    with pytest.raises(ValueError):
        run_ingest(path, "my_demo_feed", "CC BY 4.0", out_dir=tmp_path, now=NOW)


def test_run_ingest_dry_run_writes_snapshot_and_manifest(tmp_path) -> None:
    path = _write_csv(tmp_path, [dict(BASE_ROW)])
    result = run_ingest(path, "civic_feed", "CC BY 4.0", out_dir=tmp_path, now=NOW)
    assert result["rows_valid"] == 1
    assert result["written_to_db"] is False
    assert result["manifest_path"] is not None
    assert result["snapshot_path"] is not None
    manifest = json.loads(open(result["manifest_path"], encoding="utf-8").read())
    assert manifest["source_type"] == "civic_feed"
    assert manifest["licence"] == "CC BY 4.0"
    assert manifest["observation_count"] == 1


def test_run_ingest_rejects_invalid_feed_without_writing(tmp_path) -> None:
    bad = dict(BASE_ROW)
    bad["observed_at"] = "not-a-date"
    path = _write_csv(tmp_path, [bad])
    result = run_ingest(path, "civic_feed", "CC BY 4.0", out_dir=tmp_path, now=NOW)
    assert "error" in result
    assert result["manifest_path"] is None
    assert result["snapshot_path"] is None


def test_jsonl_feed_supported(tmp_path) -> None:
    path = tmp_path / "feed.jsonl"
    path.write_text(json.dumps(BASE_ROW) + "\n", encoding="utf-8")
    result = run_ingest(path, "civic_feed", "CC BY 4.0", out_dir=tmp_path, now=NOW)
    assert result["rows_valid"] == 1
