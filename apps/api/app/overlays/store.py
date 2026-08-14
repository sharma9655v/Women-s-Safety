from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import TypedDict

from sqlalchemy import Engine, text

from app.evidence.engine import freshness
from app.evidence.freshness import utc_now
from app.evidence.states import VerificationState
from app.risk.model import NIGHT_HOURS, NIGHT_MULTIPLIER

BBox = tuple[float, float, float, float]

DEMO_SOURCE = "demo_seed"

INCIDENT_OBSERVATION_TYPES = ("harassment", "suspicious_activity")

_SEVERITY_BY_TYPE = {
    "harassment": "high",
    "suspicious_activity": "moderate",
    "unsafe_transport": "moderate",
    "road_hazard": "low",
    "blocked_sidewalk": "low",
    "poor_lighting": "low",
    "streetlight_not_working": "low",
    "other": "low",
}

DEFAULT_BBOX = (77.02, 28.35, 77.35, 28.75)


class IncidentMarker(TypedDict):
    id: str
    category: str
    severity: str
    location: dict[str, float | str]
    reported_at: str
    summary: str
    verified: bool
    source: str


class LightingMarker(TypedDict):
    lat: float
    lon: float
    working: bool | None
    status_label: str
    confidence: str
    source: str
    observed_at: str | None


class HeatZone(TypedDict):
    name: str
    lat: float
    lon: float
    level: float


class AreaSafety(TypedDict):
    area_name: str
    score: dict[str, object]
    recent_incidents: int
    lighting_summary: str
    crowd: str
    by_time_of_day: list[dict[str, float | str]]


@dataclass(frozen=True)
class OverlayPoint:
    observation_id: int | None
    segment_id: int
    observation_type: str
    source_type: str
    observed_at: datetime
    verification_state: str
    working: bool | None
    lat: float
    lon: float
    area_name: str


class OverlayStore:
    """Interface for map overlay + area insight queries (PostGIS and memory)."""

    def incidents(
        self, bbox: BBox, limit: int = 500
    ) -> list[IncidentMarker]:
        return [
            _marker_from_point(p)
            for p in self.points(bbox, INCIDENT_OBSERVATION_TYPES, limit)
        ]

    def lighting(self, bbox: BBox, limit: int = 500) -> list[LightingMarker]:
        return [
            _lighting_marker_from_point(p)
            for p in self.points(bbox, ("streetlight_not_working", "poor_lighting"), limit)
        ]

    def points(
        self, bbox: BBox, types: Sequence[str] | None = None, limit: int = 500
    ) -> list[OverlayPoint]:
        raise NotImplementedError

    def area_safety(self, name: str) -> AreaSafety | None:
        raise NotImplementedError

    def heatmap(self, bbox: BBox) -> list[HeatZone]:
        raise NotImplementedError

    def alerts(self, limit: int = 20) -> list[IncidentMarker]:
        raise NotImplementedError


def _severity(observation_type: str, state: VerificationState) -> str:
    return _SEVERITY_BY_TYPE.get(observation_type, "low")


def _summary(observation_type: str, area_name: str) -> str:
    label = observation_type.replace("_", " ")
    return f"{label} reported near {area_name}"


def _marker_from_point(p: OverlayPoint) -> IncidentMarker:
    state = VerificationState(p.verification_state)
    return {
        "id": f"{p.observation_id if p.observation_id is not None else 'obs'}-{p.segment_id}",
        "category": p.observation_type,
        "severity": _severity(p.observation_type, state),
        "location": {"name": p.area_name, "lat": p.lat, "lon": p.lon},
        "reported_at": p.observed_at.isoformat(),
        "summary": _summary(p.observation_type, p.area_name),
        "verified": state == VerificationState.VERIFIED,
        "source": p.source_type,
    }


def _lighting_marker_from_point(p: OverlayPoint) -> LightingMarker:
    if p.observation_type == "streetlight_not_working":
        working = p.working
        if working is True:
            status_label = "Lighting evidence available"
        elif working is False:
            status_label = "Streetlight reported not working"
        else:
            status_label = "Lighting status uncertain"
    else:
        working = False if p.working is False else None
        status_label = (
            "Poor lighting reported" if p.working is False else "Lighting status uncertain"
        )
    confidence = (
        "high"
        if p.verification_state == VerificationState.VERIFIED.value
        else "medium"
        if p.verification_state == VerificationState.CORROBORATED.value
        else "low"
    )
    return {
        "lat": p.lat,
        "lon": p.lon,
        "working": working,
        "status_label": status_label,
        "confidence": confidence,
        "source": p.source_type,
        "observed_at": p.observed_at.isoformat(),
    }


class PostgresOverlayStore(OverlayStore):
    """Overlay queries joined over safety_observations x road_segments."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def points(
        self, bbox: BBox, types: Sequence[str] | None = None, limit: int = 500
    ) -> list[OverlayPoint]:
        min_lon, min_lat, max_lon, max_lat = bbox
        type_filter = ""
        params: dict[str, object] = {
            "min_lon": min_lon,
            "min_lat": min_lat,
            "max_lon": max_lon,
            "max_lat": max_lat,
            "limit": limit,
        }
        if types is not None:
            type_filter = " AND o.observation_type = ANY(:types)"
            params["types"] = list(types)
        stmt = text(
            "SELECT o.id, o.segment_id, o.observation_type, o.source_type, o.observed_at, "
            "o.verification_state, o.value_json, "
            "ST_Y(ST_LineInterpolatePoint(s.geometry, 0.5)) AS lat, "
            "ST_X(ST_LineInterpolatePoint(s.geometry, 0.5)) AS lon "
            "FROM safety_observations o JOIN road_segments s ON s.id = o.segment_id "
            "WHERE s.geometry && ST_MakeEnvelope(:min_lon, :min_lat, :max_lon, :max_lat, 4326)"
            f"{type_filter} "
            "ORDER BY o.observed_at DESC LIMIT :limit"
        )
        with self._engine.connect() as conn:
            rows = conn.execute(stmt, params).fetchall()
        return [
            OverlayPoint(
                observation_id=int(row.id),
                segment_id=int(row.segment_id),
                observation_type=row.observation_type,
                source_type=row.source_type,
                observed_at=row.observed_at,
                verification_state=row.verification_state,
                working=_value_bool(row.value_json),
                lat=float(row.lat),
                lon=float(row.lon),
                area_name="",
            )
            for row in rows
        ]

    def incidents(self, bbox: BBox, limit: int = 500) -> list[IncidentMarker]:
        return [
            _marker_from_point(p)
            for p in self.points(bbox, INCIDENT_OBSERVATION_TYPES, limit)
        ]

    def lighting(self, bbox: BBox, limit: int = 500) -> list[LightingMarker]:
        return [
            _lighting_marker_from_point(p)
            for p in self.points(bbox, ("streetlight_not_working", "poor_lighting"), limit)
        ]

    def area_safety(self, name: str) -> AreaSafety | None:
        center = AREA_CENTERS.get(name)
        if center is None:
            return None
        points = self.points(_bbox_around(center, 0.02), None, 2000)
        if not points:
            return None
        return _aggregate_area_safety(name, points)

    def heatmap(self, bbox: BBox) -> list[HeatZone]:
        return heatmap_from_points(self.points(bbox, None, 2000), bbox)

    def alerts(self, limit: int = 20) -> list[IncidentMarker]:
        return self.incidents(DEFAULT_BBOX, limit)


def _value_bool(value_json: object) -> bool | None:
    if not isinstance(value_json, dict):
        return None
    for key in ("working", "poor", "blocked", "incident"):
        if key in value_json and isinstance(value_json[key], bool):
            return bool(value_json[key])
    return None


class MemoryOverlayStore(OverlayStore):
    """Loads a demo-evidence snapshot (JSON) so the full stack works without
    PostGIS â€” the offline demo path. All observations are labeled demo_seed."""

    def __init__(self, observations: Sequence[OverlayPoint] = ()) -> None:
        self._observations = list(observations)

    def points(
        self, bbox: BBox, types: Sequence[str] | None = None, limit: int = 500
    ) -> list[OverlayPoint]:
        min_lon, min_lat, max_lon, max_lat = bbox
        wanted = [
            p
            for p in self._observations
            if min_lon <= p.lon <= max_lon
            and min_lat <= p.lat <= max_lat
            and (types is None or p.observation_type in types)
        ]
        wanted.sort(key=lambda p: p.observed_at, reverse=True)
        return wanted[:limit]

    def incidents(self, bbox: BBox, limit: int = 500) -> list[IncidentMarker]:
        return [
            _marker_from_point(p)
            for p in self.points(bbox, INCIDENT_OBSERVATION_TYPES, limit)
        ]

    def lighting(self, bbox: BBox, limit: int = 500) -> list[LightingMarker]:
        return [
            _lighting_marker_from_point(p)
            for p in self.points(bbox, ("streetlight_not_working", "poor_lighting"), limit)
        ]

    def area_safety(self, name: str) -> AreaSafety | None:
        center = AREA_CENTERS.get(name)
        if center is None:
            return None
        points = [p for p in self._observations if _distance_m(p.lat, p.lon, center) < 2000]
        if not points:
            return None
        return _aggregate_area_safety(name, points)

    def heatmap(self, bbox: BBox) -> list[HeatZone]:
        return heatmap_from_points(self.points(bbox, None, 2000), bbox)

    def alerts(self, limit: int = 20) -> list[IncidentMarker]:
        return self.incidents(DEFAULT_BBOX, limit)


AREA_CENTERS: dict[str, tuple[float, float]] = {
    "connaught-place": (28.6315, 77.2167),
    "india-gate": (28.6129, 77.2295),
    "chandni-chowk": (28.6500, 77.2310),
    "hauz-khas": (28.5494, 77.2001),
    "karol-bagh": (28.6515, 77.1908),
    "lajpat-nagar": (28.5677, 77.2433),
    "saket": (28.5245, 77.2066),
    "dwarka": (28.5563, 77.0579),
    "north-campus": (28.6900, 77.2060),
    "paharganj": (28.6450, 77.2100),
}


def _bbox_around(center: tuple[float, float], pad_deg: float) -> BBox:
    lat, lon = center
    return (lon - pad_deg, lat - pad_deg, lon + pad_deg, lat + pad_deg)


def _distance_m(lat1: float, lon1: float, center: tuple[float, float]) -> float:
    lat2, lon2 = center
    r = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def heatmap_from_points(points: Sequence[OverlayPoint], bbox: BBox) -> list[HeatZone]:
    min_lon, min_lat, max_lon, max_lat = bbox
    cols, rows = 6, 6
    grid: dict[tuple[int, int], list[OverlayPoint]] = {}
    for p in points:
        if not (min_lon <= p.lon <= max_lon and min_lat <= p.lat <= max_lat):
            continue
        col = min(cols - 1, int((p.lon - min_lon) / (max_lon - min_lon) * cols))
        row = min(rows - 1, int((p.lat - min_lat) / (max_lat - min_lat) * rows))
        grid.setdefault((col, row), []).append(p)
    zones: list[HeatZone] = []
    for (col, row), cell_points in grid.items():
        lon = min_lon + (col + 0.5) / cols * (max_lon - min_lon)
        lat = min_lat + (row + 0.5) / rows * (max_lat - min_lat)
        level = min(1.0, 0.15 + 0.85 * min(1.0, len(cell_points) / 6))
        zones.append(
            {
                "name": f"Zone {row * cols + col + 1}",
                "lat": round(lat, 5),
                "lon": round(lon, 5),
                "level": round(level, 3),
            }
        )
    zones.sort(key=lambda z: z["level"], reverse=True)
    return zones[:12]


def _aggregate_area_safety(name: str, points: Sequence[OverlayPoint]) -> AreaSafety:
    """Area estimate from per-segment evidence around the named hotspot.

    Demo-labeled data only ever comes from source_type demo_seed; the same
    computation runs over real observations when they exist.
    """
    now = utc_now()
    incident_points = [p for p in points if p.observation_type in INCIDENT_OBSERVATION_TYPES]
    lighting_points = [
        p for p in points if p.observation_type in ("streetlight_not_working", "poor_lighting")
    ]
    fresh_incidents = [
        p for p in incident_points if freshness(p.observed_at, now, p.observation_type) >= 0.05
    ]

    by_time_of_day: list[dict[str, float | str]] = []
    fresh_points = [p for p in points if freshness(p.observed_at, now, p.observation_type) >= 0.05]
    base_risk = min(1.0, 0.08 + 0.06 * len(fresh_points) / max(1, 10))
    lighting_out_share = (
        sum(1 for p in lighting_points if p.working is False) / max(1, len(lighting_points))
        if lighting_points
        else 0.2
    )
    for hour in range(24):
        is_night = hour in NIGHT_HOURS
        risk = base_risk * (NIGHT_MULTIPLIER if is_night else 1.0)
        risk += lighting_out_share * (0.18 if is_night else 0.05)
        risk = min(1.0, risk)
        score = round(max(0, min(100, (1.0 - risk) * 100)))
        confidence = round(max(0.3, min(0.9, 0.9 - risk)), 2)
        by_time_of_day.append({"hour": hour, "score": score, "confidence": confidence})

    day_score = next((p["score"] for p in by_time_of_day if p["hour"] == 15), 70)
    night_score = next((p["score"] for p in by_time_of_day if p["hour"] == 22), 60)
    recent = min(99, len(fresh_incidents))
    crowd = "high" if recent > 5 else "medium" if recent > 2 else "low"
    lighting_out = sum(1 for p in lighting_points if p.working is False)
    lighting_share = (
        min(1.0, (len(lighting_points) - lighting_out) / max(1, len(lighting_points)))
        if lighting_points
        else None
    )
    lighting_summary = (
        "Mostly lit"
        if lighting_share is not None and lighting_share >= 0.7
        else "Partially lit"
        if lighting_share is not None and lighting_share >= 0.4
        else "Limited lighting evidence"
    )
    score_value = round((day_score + night_score) / 2)
    band = "high" if score_value >= 70 else "moderate" if score_value >= 50 else "low"
    return {
        "area_name": name.replace("-", " ").title(),
        "score": {
            "value": score_value,
            "band": band,
            "confidence": "medium",
            "evidence": {
                "sources": [{"name": "Demo data", "kind": "public", "reliability": 0.55}],
                "confidence": "medium",
                "confidence_value": 0.6,
                "freshness": {
                    "tier": "fresh",
                    "label": "Fresh",
                    "updated_at": now.isoformat(),
                    "detail": "Updated recently",
                },
                "conflicts": [],
                "coverage": 0.6,
            },
        },
        "recent_incidents": recent,
        "lighting_summary": lighting_summary,
        "crowd": crowd,
        "by_time_of_day": by_time_of_day,
    }
