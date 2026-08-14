import json
from pathlib import Path

import pytest

from ml.gate import MIN_SPAN_DAYS, MIN_VERIFIED_OBSERVATIONS, GateReport, write_report
from ml.model_registry import active_model, load_registry, register_model
from ml.train import main


def test_gate_closed_without_data(monkeypatch) -> None:
    def fake_check() -> GateReport:
        return GateReport(
            verified_observations=0,
            total_observations=0,
            span_days=0.0,
            threshold_observations=MIN_VERIFIED_OBSERVATIONS,
            threshold_span_days=MIN_SPAN_DAYS,
            open=False,
            reason="verified observations 0 < 1000",
            checked_at="2026-08-14T00:00:00+00:00",
        )

    monkeypatch.setattr("ml.train.check_gate", fake_check)
    assert main() == 3  # training refused


def test_gate_open_passes(monkeypatch) -> None:
    def fake_check() -> GateReport:
        return GateReport(
            verified_observations=1200,
            total_observations=2000,
            span_days=150.0,
            threshold_observations=MIN_VERIFIED_OBSERVATIONS,
            threshold_span_days=MIN_SPAN_DAYS,
            open=True,
            reason="gate open",
            checked_at="2026-08-14T00:00:00+00:00",
        )

    monkeypatch.setattr("ml.train.check_gate", fake_check)
    assert main() == 0


def test_gate_report_roundtrip(tmp_path: Path) -> None:
    report = GateReport(
        verified_observations=0,
        total_observations=10,
        span_days=1.0,
        threshold_observations=MIN_VERIFIED_OBSERVATIONS,
        threshold_span_days=MIN_SPAN_DAYS,
        open=False,
        reason="not enough",
        checked_at="2026-08-14T00:00:00+00:00",
    )
    out = write_report(report, tmp_path / "gate-report.json")
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded["open"] is False
    assert loaded["reason"] == "not enough"


def test_registry_empty_and_no_active_model(tmp_path: Path) -> None:
    path = tmp_path / "registry.json"
    assert load_registry(path)["models"] == []
    assert active_model(path) is None


def test_register_model_rejects_duplicate(tmp_path: Path) -> None:
    path = tmp_path / "registry.json"
    entry = {
        "name": "xgboost",
        "version": "v1",
        "dataset_version": "d1",
        "metrics": {},
        "status": "active",
        "artifact_path": "x",
    }
    register_model(entry, path)
    with pytest.raises(ValueError):
        register_model(entry, path)
    assert active_model(path)["name"] == "xgboost"


def test_register_model_overwrite_ok(tmp_path: Path) -> None:
    path = tmp_path / "registry.json"
    register_model({"name": "m", "version": "v1", "status": "archived"}, path)
    register_model({"name": "m", "version": "v2", "status": "active"}, path, overwrite=True)
    registry = load_registry(path)
    assert len(registry["models"]) == 1
    assert active_model(path)["version"] == "v2"
