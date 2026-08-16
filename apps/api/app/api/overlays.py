from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.facilities import FacilityStore, get_facilities_store
from app.overlays import OverlayStore, get_overlay_store
from app.overlays.store import (
    DEFAULT_BBOX,
    AreaSafety,
    HeatZone,
    IncidentMarker,
    LightingMarker,
)

router = APIRouter(prefix="/api")


def _bbox(
    min_lon: float = Query(default=DEFAULT_BBOX[0], ge=-180, le=180),
    min_lat: float = Query(default=DEFAULT_BBOX[1], ge=-90, le=90),
    max_lon: float = Query(default=DEFAULT_BBOX[2], ge=-180, le=180),
    max_lat: float = Query(default=DEFAULT_BBOX[3], ge=-90, le=90),
) -> tuple[float, float, float, float]:
    return (min_lon, min_lat, max_lon, max_lat)


@router.get("/incidents")
def get_incidents(
    store: Annotated[OverlayStore, Depends(get_overlay_store)],
    bbox: Annotated[tuple[float, float, float, float], Depends(_bbox)],
    limit: int = Query(default=500, ge=1, le=2000),
) -> list[IncidentMarker]:
    return store.incidents(bbox, limit)


@router.get("/lighting")
def get_lighting(
    store: Annotated[OverlayStore, Depends(get_overlay_store)],
    bbox: Annotated[tuple[float, float, float, float], Depends(_bbox)],
    limit: int = Query(default=500, ge=1, le=2000),
) -> list[LightingMarker]:
    return store.lighting(bbox, limit)


@router.get("/facilities")
def get_facilities(
    store: Annotated[FacilityStore, Depends(get_facilities_store)],
    bbox: Annotated[tuple[float, float, float, float], Depends(_bbox)],
    limit: int = Query(default=500, ge=1, le=2000),
) -> list[dict[str, object]]:
    rows = store.within_bbox(*bbox)[:limit]
    return [
        {
            "id": str(row.id),
            "type": row.type,
            "name": row.name or row.type.replace("_", " "),
            "lat": row.lat,
            "lon": row.lon,
            "distance_m": None,
        }
        for row in rows
    ]


@router.get("/alerts")
def get_alerts(
    store: Annotated[OverlayStore, Depends(get_overlay_store)],
    limit: int = Query(default=20, ge=1, le=100),
) -> list[IncidentMarker]:
    return store.alerts(limit)


@router.get("/safety/area")
def get_area_safety(
    store: Annotated[OverlayStore, Depends(get_overlay_store)],
    name: str = Query(default="connaught-place"),
) -> AreaSafety | dict[str, object]:
    area = store.area_safety(name)
    if area is None:
        return {
            "area_name": name.replace("-", " ").title(),
            "score": None,
            "recent_incidents": 0,
            "lighting_summary": "Limited evidence",
            # Honest: no crowd data source exists.
            "crowd": None,
            "by_time_of_day": [],
        }
    return area


@router.get("/safety/heatmap")
def get_heatmap(
    store: Annotated[OverlayStore, Depends(get_overlay_store)],
    bbox: Annotated[tuple[float, float, float, float], Depends(_bbox)],
) -> list[HeatZone]:
    return store.heatmap(bbox)


@router.get("/safety/areas")
def get_areas(
    store: Annotated[OverlayStore, Depends(get_overlay_store)],
) -> list[AreaSafety]:
    return store.all_areas()
