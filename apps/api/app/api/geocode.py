from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.facilities import FacilityStore, get_facilities_store
from app.overlays.store import AREA_CENTERS
from app.schemas import GeocodeResponse, GeocodeResult

router = APIRouter(prefix="/api")

MAX_GEOCODE_LIMIT = 10


@router.get("/geocode", response_model=GeocodeResponse)
def geocode(
    facilities: Annotated[FacilityStore, Depends(get_facilities_store)],
    q: str = Query(min_length=1, max_length=80),
    limit: int = Query(default=6, ge=1, le=MAX_GEOCODE_LIMIT),
) -> GeocodeResponse:
    """Deterministic gazetteer search: named facilities + known areas.

    No external geocoder is used — results come from the loaded OSM
    facilities table and the built-in area centers (AREA_CENTERS). Matching
    is case-insensitive substring on names; empty queries return nothing.
    """
    needle = q.strip().lower()
    if not needle:
        return GeocodeResponse(results=[])

    results: list[GeocodeResult] = []
    seen: set[tuple[float, float]] = set()

    for facility in facilities.search(q, limit):
        key = (round(facility.lat, 6), round(facility.lon, 6))
        if key in seen:
            continue
        seen.add(key)
        results.append(
            GeocodeResult(
                name=facility.name or facility.type,
                kind="facility",
                type=facility.type,
                lat=facility.lat,
                lon=facility.lon,
            )
        )
        if len(results) >= limit:
            return GeocodeResponse(results=results)

    for name, (lat, lon) in AREA_CENTERS.items():
        if len(results) >= limit:
            break
        if needle in name.replace("-", " "):
            key = (round(lat, 6), round(lon, 6))
            if key in seen:
                continue
            seen.add(key)
            results.append(
                GeocodeResult(
                    name=name.replace("-", " ").title(),
                    kind="area",
                    lat=lat,
                    lon=lon,
                )
            )
    return GeocodeResponse(results=results)
