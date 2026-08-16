from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from app.db import make_engine

from app.config import settings
from app.segments.store import MemorySegmentStore, PostgisSegmentStore, SegmentStore


@lru_cache(maxsize=1)
def get_segments_store() -> SegmentStore:
    """Return the configured segment store.

    Priority: PostGIS when DATABASE_URL is set and reachable, then
    SEGMENTS_GEOJSON file (dev/test), then an empty store.
    """
    if settings.database_url and settings.database_url != "":
        try:
            engine = make_engine()
            with engine.connect():
                pass
        except Exception:
            engine = None
        if engine is not None:
            return PostgisSegmentStore(engine)
    path = settings.segments_geojson
    if path and Path(path).exists():
        return MemorySegmentStore.from_geojson(path)
    return MemorySegmentStore.empty()
