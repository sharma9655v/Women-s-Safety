"""Model registry conventions.

Active-model negotiation lives in the API (app/api/models.py). The registry
is a JSON file (`models/registry.json`) that records every trained model's
name, version, dataset_version, metrics and status. Empty until the Phase 6
gate opens — the API then serves the deterministic baseline.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REGISTRY_PATH = Path(__file__).resolve().parents[2] / "models" / "registry.json"

SCHEMA = {
    "schema_version": 1,
    "models": [
        {
            "name": "str",
            "version": "str",
            "dataset_version": "str",
            "metrics": {"brier": 0.0, "ece": 0.0, "roc_auc": 0.0, "pr_auc": 0.0, "f1": 0.0},
            "trained_at": "ISO-8601",
            "artifact_path": "str",
            "status": "active|archived",
        }
    ],
}


def load_registry(path: Path = REGISTRY_PATH) -> dict[str, Any]:
    if not path.exists():
        return {"schema_version": 1, "models": []}
    return json.loads(path.read_text(encoding="utf-8"))


def active_model(path: Path = REGISTRY_PATH) -> dict[str, Any] | None:
    for entry in load_registry(path)["models"]:
        if entry.get("status") == "active":
            return entry
    return None


def register_model(
    entry: dict[str, Any], path: Path = REGISTRY_PATH, overwrite: bool = False
) -> None:
    """Append a trained-model record (or replace the active one)."""
    registry = load_registry(path)
    entry = dict(entry)
    entry.setdefault("trained_at", datetime.now(UTC).isoformat(timespec="seconds"))
    existing = [m for m in registry["models"] if m["name"] == entry["name"]]
    if existing and not overwrite:
        raise ValueError(f"model {entry['name']!r} already registered")
    if existing:
        registry["models"] = [m for m in registry["models"] if m["name"] != entry["name"]]
    registry["models"].append(entry)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")
