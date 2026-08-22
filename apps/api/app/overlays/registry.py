from __future__ import annotations

import json
from functools import lru_cache

from app.config import settings
from app.db import make_engine
from app.overlays.store import (
    DEMO_SOURCE,
    MemoryOverlayStore,
    OverlayPoint,
    OverlayStore,
    PostgresOverlayStore,
)


def _load_snapshot(path: str) -> list[OverlayPoint]:
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    points: list[OverlayPoint] = []
    for item in raw.get("observations", []):
        points.append(
            OverlayPoint(
                observation_id=item.get("observation_id"),
                segment_id=int(item["segment_id"]),
                observation_type=item["observation_type"],
                source_type=item.get("source_type", DEMO_SOURCE),
                observed_at=item["observed_at"],
                verification_state=item.get("verification_state", "REPORTED"),
                working=item.get("working"),
                lat=float(item["lat"]),
                lon=float(item["lon"]),
                area_name=item.get("area_name", ""),
            )
        )
    return points


@lru_cache(maxsize=1)
def get_overlay_store() -> OverlayStore:
    """PostGIS when reachable; otherwise a memory store backed by the demo
    evidence snapshot (offline demo path)."""
    if settings.database_url and settings.database_url != "":
        try:
            engine = make_engine()
            with engine.connect():
                pass
        except Exception:
            engine = None
        if engine is not None:
            return PostgresOverlayStore(engine)
    if settings.evidence_seed_json:
        try:
            return MemoryOverlayStore(_load_snapshot(settings.evidence_seed_json))
        except OSError:
            pass
    return MemoryOverlayStore()
