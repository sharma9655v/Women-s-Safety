from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.overlays import OverlayStore, get_overlay_store
from app.overlays.store import DEFAULT_BBOX

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
):
    return store.incidents(bbox, limit)


@router.get("/lighting")
def get_lighting(
    store: Annotated[OverlayStore, Depends(get_overlay_store)],
    bbox: Annotated[tuple[float, float, float, float], Depends(_bbox)],
    limit: int = Query(default=500, ge=1, le=2000),
):
    return store.lighting(bbox, limit)


@router.get("/alerts")
def get_alerts(
    store: Annotated[OverlayStore, Depends(get_overlay_store)],
    limit: int = Query(default=20, ge=1, le=100),
):
    return store.alerts(limit)


@router.get("/safety/area")
def get_area_safety(
    store: Annotated[OverlayStore, Depends(get_overlay_store)],
    name: str = Query(default="connaught-place"),
):
    area = store.area_safety(name)
    if area is None:
        return {
            "area_name": name.replace("-", " ").title(),
            "score": None,
            "recent_incidents": 0,
            "lighting_summary": "Limited evidence",
            "crowd": "low",
            "by_time_of_day": [],
        }
    return area


@router.get("/safety/heatmap")
def get_heatmap(
    store: Annotated[OverlayStore, Depends(get_overlay_store)],
    bbox: Annotated[tuple[float, float, float, float], Depends(_bbox)],
):
    return store.heatmap(bbox)
