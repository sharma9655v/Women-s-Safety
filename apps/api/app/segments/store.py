from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

from sqlalchemy import Engine, text

from app.segments.matcher import RoadSegment


def _overlaps_bbox(
    geometry: tuple[tuple[float, float], ...],
    min_lon: float,
    min_lat: float,
    max_lon: float,
    max_lat: float,
) -> bool:
    return any(min_lon <= lon <= max_lon and min_lat <= lat <= max_lat for lon, lat in geometry)


class SegmentStore:
    """Interface for segment sources. Implementations: memory (GeoJSON)
    and PostGIS (once the database is available)."""

    def all(self) -> Sequence[RoadSegment]:
        raise NotImplementedError

    def count(self) -> int:
        raise NotImplementedError

    def within_bbox(
        self, min_lon: float, min_lat: float, max_lon: float, max_lat: float
    ) -> Sequence[RoadSegment]:
        raise NotImplementedError

    def dataset_versions(self) -> list[str]:
        """Dataset versions present in the segment store (for model audit)."""
        raise NotImplementedError


class MemorySegmentStore(SegmentStore):
    def __init__(self, segments: Sequence[RoadSegment]) -> None:
        self._segments = list(segments)

    @classmethod
    def empty(cls) -> MemorySegmentStore:
        return cls([])

    @classmethod
    def from_geojson(cls, path: str | Path) -> MemorySegmentStore:
        with open(path, encoding="utf-8") as fh:
            payload = json.load(fh)
        return cls.from_geojson_dict(payload)

    @classmethod
    def from_geojson_dict(cls, payload: dict[str, object]) -> MemorySegmentStore:
        segments: list[RoadSegment] = []
        features = payload.get("features", [])
        if not isinstance(features, list):
            return cls(segments)
        for raw_feature in features:
            if not isinstance(raw_feature, dict):
                continue
            properties = raw_feature.get("properties", {}) or {}
            if not isinstance(properties, dict):
                properties = {}
            raw_geometry = raw_feature.get("geometry", {}) or {}
            if not isinstance(raw_geometry, dict):
                continue
            coordinates = raw_geometry.get("coordinates", [])
            if not isinstance(coordinates, list) or len(coordinates) < 2:
                continue
            segments.append(
                RoadSegment(
                    id=int(properties.get("id") or properties.get("osm_way_id") or 0),
                    geometry=tuple(tuple(coord) for coord in coordinates),
                    road_type=properties.get("road_type"),
                    lit=properties.get("lit"),
                )
            )
        return cls(segments)

    def all(self) -> Sequence[RoadSegment]:
        return self._segments

    def count(self) -> int:
        return len(self._segments)

    def within_bbox(
        self, min_lon: float, min_lat: float, max_lon: float, max_lat: float
    ) -> Sequence[RoadSegment]:
        return [
            seg
            for seg in self._segments
            if _overlaps_bbox(seg.geometry, min_lon, min_lat, max_lon, max_lat)
        ]

    def dataset_versions(self) -> list[str]:
        return []


class PostgisSegmentStore(SegmentStore):
    """Reads road_segments from PostGIS via SQLAlchemy.

    The production store behind the same interface as the memory store.
    """

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    @staticmethod
    def _rows_to_segments(rows: Sequence[object]) -> list[RoadSegment]:
        segments: list[RoadSegment] = []
        for row in rows:
            coordinates = json.loads(row.geom)["coordinates"]  # type: ignore[attr-defined]
            if len(coordinates) < 2:
                continue
            segments.append(
                RoadSegment(
                    id=int(row.id),  # type: ignore[attr-defined]
                    geometry=tuple(tuple(coord) for coord in coordinates),
                    road_type=row.road_type,  # type: ignore[attr-defined]
                    lit=row.lit,  # type: ignore[attr-defined]
                )
            )
        return segments

    def all(self) -> Sequence[RoadSegment]:
        stmt = text("SELECT id, ST_AsGeoJSON(geometry) AS geom, road_type, lit FROM road_segments")
        with self._engine.connect() as conn:
            rows = conn.execute(stmt).fetchall()
        return self._rows_to_segments(rows)

    def count(self) -> int:
        with self._engine.connect() as conn:
            return int(conn.execute(text("SELECT count(*) FROM road_segments")).scalar_one())

    def within_bbox(
        self, min_lon: float, min_lat: float, max_lon: float, max_lat: float
    ) -> Sequence[RoadSegment]:
        stmt = text(
            "SELECT id, ST_AsGeoJSON(geometry) AS geom, road_type, lit "
            "FROM road_segments "
            "WHERE geometry && ST_MakeEnvelope(:min_lon, :min_lat, :max_lon, :max_lat, 4326)"
        )
        params = {
            "min_lon": min_lon,
            "min_lat": min_lat,
            "max_lon": max_lon,
            "max_lat": max_lat,
        }
        with self._engine.connect() as conn:
            rows = conn.execute(stmt, params).fetchall()
        return self._rows_to_segments(rows)

    def dataset_versions(self) -> list[str]:
        with self._engine.connect() as conn:
            rows = conn.execute(
                text("SELECT DISTINCT dataset_version FROM road_segments ORDER BY dataset_version")
            ).fetchall()
        return [str(row.dataset_version) for row in rows]
