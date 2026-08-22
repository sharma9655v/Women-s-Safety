from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import Engine, text


@dataclass(frozen=True)
class Facility:
    """A point facility (police, hospital, transit stop, ...)."""

    id: int
    type: str
    name: str | None
    lon: float
    lat: float


class FacilityStore:
    """Interface for facility sources (memory and PostGIS)."""

    def within_bbox(
        self,
        min_lon: float,
        min_lat: float,
        max_lon: float,
        max_lat: float,
        types: Sequence[str] | None = None,
    ) -> Sequence[Facility]:
        raise NotImplementedError

    def search(self, query: str, limit: int = 10) -> Sequence[Facility]:
        raise NotImplementedError

    def count(self) -> int:
        raise NotImplementedError


class MemoryFacilityStore(FacilityStore):
    def __init__(self, facilities: Sequence[Facility] = ()) -> None:
        self._facilities = list(facilities)

    def within_bbox(
        self,
        min_lon: float,
        min_lat: float,
        max_lon: float,
        max_lat: float,
        types: Sequence[str] | None = None,
    ) -> Sequence[Facility]:
        wanted = set(types) if types is not None else None
        return [
            facility
            for facility in self._facilities
            if min_lon <= facility.lon <= max_lon
            and min_lat <= facility.lat <= max_lat
            and (wanted is None or facility.type in wanted)
        ]

    def count(self) -> int:
        return len(self._facilities)

    def search(self, query: str, limit: int = 10) -> Sequence[Facility]:
        needle = query.strip().lower()
        if not needle:
            return []
        return [
            facility
            for facility in self._facilities
            if facility.name is not None and needle in facility.name.lower()
        ][:limit]


class PostgresFacilityStore(FacilityStore):
    """Reads facilities from PostGIS via SQLAlchemy."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def within_bbox(
        self,
        min_lon: float,
        min_lat: float,
        max_lon: float,
        max_lat: float,
        types: Sequence[str] | None = None,
    ) -> Sequence[Facility]:
        stmt = (
            "SELECT id, type, name, ST_X(geometry) AS lon, ST_Y(geometry) AS lat "
            "FROM facilities "
            "WHERE geometry && ST_MakeEnvelope(:min_lon, :min_lat, :max_lon, :max_lat, 4326)"
        )
        params: dict[str, object] = {
            "min_lon": min_lon,
            "min_lat": min_lat,
            "max_lon": max_lon,
            "max_lat": max_lat,
        }
        if types is not None:
            stmt += " AND type = ANY(:types)"
            params["types"] = list(types)
        with self._engine.connect() as conn:
            rows = conn.execute(text(stmt), params).fetchall()
        return [
            Facility(
                id=int(row.id),
                type=row.type,
                name=row.name,
                lon=float(row.lon),
                lat=float(row.lat),
            )
            for row in rows
        ]

    def count(self) -> int:
        with self._engine.connect() as conn:
            return int(conn.execute(text("SELECT count(*) FROM facilities")).scalar_one())

    def search(self, query: str, limit: int = 10) -> Sequence[Facility]:
        stmt = (
            "SELECT id, type, name, ST_X(geometry) AS lon, ST_Y(geometry) AS lat "
            "FROM facilities WHERE name ILIKE '%' || :query || '%' ORDER BY name LIMIT :limit"
        )
        with self._engine.connect() as conn:
            rows = conn.execute(text(stmt), {"query": query.strip(), "limit": limit}).fetchall()
        return [
            Facility(
                id=int(row.id),
                type=row.type,
                name=row.name,
                lon=float(row.lon),
                lat=float(row.lat),
            )
            for row in rows
        ]
