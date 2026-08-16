from __future__ import annotations

from functools import lru_cache

from app.db import make_engine

from app.config import settings
from app.facilities.store import FacilityStore, MemoryFacilityStore, PostgresFacilityStore


@lru_cache(maxsize=1)
def get_facilities_store() -> FacilityStore:
    """Return the configured facilities store (PostGIS first, else empty)."""
    if settings.database_url and settings.database_url != "":
        try:
            engine = make_engine()
            with engine.connect():
                pass
        except Exception:
            engine = None
        if engine is not None:
            return PostgresFacilityStore(engine)
    return MemoryFacilityStore()
