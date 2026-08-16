from __future__ import annotations

from sqlalchemy import create_engine

from app.config import settings

# Bounded TCP connect so a dropped (firewalled) PostGIS host fails fast and
# the memory-store fallback kicks in, instead of stalling every request for
# the OS connect timeout, once per store probe.
CONNECT_TIMEOUT_S = 5


def make_engine() -> object:
    """Create the PostGIS engine with a bounded connect timeout."""
    return create_engine(
        settings.database_url,
        connect_args={"connect_timeout": CONNECT_TIMEOUT_S},
    )