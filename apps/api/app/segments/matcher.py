from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from shapely.geometry import LineString


@dataclass(frozen=True)
class RoadSegment:
    """A road segment with its geometry as [(lon, lat), ...]."""

    id: int
    geometry: tuple[tuple[float, float], ...]
    road_type: str | None = None
    lit: str | None = None

    def __post_init__(self) -> None:
        if len(self.geometry) < 2:
            raise ValueError(f"segment {self.id} needs at least 2 coordinates")


def map_match(
    route_coords: Sequence[tuple[float, float]],
    segments: Sequence[RoadSegment],
    threshold_deg: float = 0.0015,
) -> list[int]:
    """Snap a route to the ordered, unique segment ids it traverses.

    Deterministic and pure-geometry: each segment whose distance to the route
    polyline is within ``threshold_deg`` (degrees, ~150 m at Indian latitudes)
    is projected onto the route and the segments are returned in route order.

    This is the Phase 2 baseline matcher; it is deliberately simple and will
    be refined (per-segment thresholds, heading consistency) once PostGIS
    matching data is available. Degrees are a proxy for metres — accepted for
    the deterministic baseline, replaced in later phases.
    """
    if not route_coords or not segments:
        return []

    route_line = LineString(route_coords)
    if route_line.is_empty:
        return []

    matched: list[tuple[float, int]] = []
    for seg in segments:
        seg_line = LineString(seg.geometry)
        if seg_line.is_empty:
            continue
        if route_line.distance(seg_line) > threshold_deg:
            continue
        midpoint = seg_line.interpolate(0.5, normalized=True)
        matched.append((route_line.project(midpoint), seg.id))

    matched.sort(key=lambda item: item[0])
    return [seg_id for _, seg_id in matched]
