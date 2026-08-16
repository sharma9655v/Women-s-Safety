from __future__ import annotations

from collections.abc import Iterator
from functools import lru_cache
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.config import settings
from app.evidence import EvidenceStore, aggregate, get_evidence_store
from app.facilities import FacilityStore, get_facilities_store
from app.reports.limiter import RateLimiter, client_key, get_rate_limiter
from app.risk import (
    MODEL_VERSION,
    ScoredRoute,
    assign_route_types,
    compute_segment_risk,
    nearest_emergency_m,
    route_warnings,
    score_candidate,
    segment_length_m,
)
from app.routing import OsrmClient, OsrmError
from app.schemas import RouteCandidate, RouteRequest, RouteResult, RoutesResponse, RouteType
from app.segments import SegmentStore, get_segments_store, map_match, nearest_road_distance_m
from app.segments.matcher import RoadSegment

router = APIRouter(prefix="/api")

# IST = UTC + 5:30 (design.md time/day feature).
TIMEZONE_OFFSET_HOURS = 5.5

# Padding (degrees) around the route bbox for facility queries.
FACILITY_BBOX_PAD_DEG = 0.02

EMERGENCY_FACILITY_TYPES = ("police", "hospital", "fire_station")

# Endpoints farther than this from the nearest mapped road get an honest
# "off the road network" warning on every route.
OFF_NETWORK_THRESHOLD_M = 150.0

# Output order matches design.md outputs 1..3.
_ROUTE_TYPES: tuple[RouteType, RouteType, RouteType] = (
    "safety_priority",
    "balanced",
    "time_priority",
)


@lru_cache(maxsize=1)
def get_route_rate_limiter() -> RateLimiter:
    return get_rate_limiter(
        prefix="route_ratelimit",
        limit=settings.route_rate_limit_per_minute,
        window_s=60,
    )


def get_osrm() -> Iterator[OsrmClient]:
    client = OsrmClient(settings.osrm_base_url)
    try:
        yield client
    finally:
        client.close()


def _ist_hour() -> int:
    from datetime import UTC, datetime, timedelta

    return (datetime.now(UTC) + timedelta(hours=TIMEZONE_OFFSET_HOURS)).hour


@router.post(
    "/routes",
    response_model=RoutesResponse,
    responses={
        status.HTTP_502_BAD_GATEWAY: {"description": "OSRM rejected the request"},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "OSRM is unreachable"},
    },
)
def get_routes(
    req: RouteRequest,
    request: Request,
    client: Annotated[OsrmClient, Depends(get_osrm)],
    segments: Annotated[SegmentStore, Depends(get_segments_store)],
    evidence: Annotated[EvidenceStore, Depends(get_evidence_store)],
    facilities: Annotated[FacilityStore, Depends(get_facilities_store)],
    limiter: Annotated[RateLimiter, Depends(get_route_rate_limiter)],
) -> RoutesResponse:
    """Three ranked, explainable route types: Safety Priority / Balanced /
    Time Priority. Never fabricates a route and never claims safety.

    Every route carries risk probability, confidence, uncertainty, reasons,
    warnings and the deterministic model version. Requests are rate-limited
    per pseudonymous client (same pattern as reports).
    """
    if not limiter.allow(client_key(request)):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS, "Too many routing requests — try again later"
        )

    try:
        candidates = client.routes(req.origin, req.destination, req.mode)
    except OsrmError as exc:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            detail=f"Routing service rejected the request: {exc.code}",
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Routing service is unreachable",
        ) from exc

    if not candidates:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            detail="Routing service returned no route between these points",
        )

    matched, nearby_by_id = _match_all(candidates, segments)
    nearby_segments = list(nearby_by_id.values())
    endpoint_warnings = [
        *(_off_network_warning("Origin", req.origin.lon, req.origin.lat, nearby_segments)),
        *(
            _off_network_warning(
                "Destination", req.destination.lon, req.destination.lat, nearby_segments
            )
        ),
    ]
    all_segment_ids = [seg_id for ids in matched for seg_id in ids]
    observations = evidence.observations_for_segments(all_segment_ids)
    evidence_by_segment = {
        seg_id: aggregate(seg_id, observations.get(seg_id, [])) for seg_id in all_segment_ids
    }

    facility_bbox = _facility_bbox(candidates)
    nearby_facilities = facilities.within_bbox(*facility_bbox, types=EMERGENCY_FACILITY_TYPES)

    hour_ist = req.hour_ist if req.hour_ist is not None else _ist_hour()
    scored: list[ScoredRoute] = []
    for candidate, segment_ids in zip(candidates, matched, strict=True):
        risks = []
        lengths = []
        for seg_id in segment_ids:
            road_segment = nearby_by_id.get(seg_id)
            if road_segment is None:
                risks.append(
                    compute_segment_risk(
                        segment_id=seg_id,
                        evidence=evidence_by_segment.get(seg_id),
                        road_type=None,
                        lit=None,
                        nearest_emergency_m=None,
                        hour_ist=hour_ist,
                    )
                )
                lengths.append(0.0)
                continue
            length = segment_length_m(road_segment.geometry)
            midpoint = _midpoint(road_segment.geometry)
            facility_distance = (
                nearest_emergency_m(midpoint[0], midpoint[1], nearby_facilities)
                if midpoint
                else None
            )
            risks.append(
                compute_segment_risk(
                    segment_id=seg_id,
                    evidence=evidence_by_segment.get(seg_id),
                    road_type=road_segment.road_type,
                    lit=road_segment.lit,
                    nearest_emergency_m=facility_distance,
                    hour_ist=hour_ist,
                )
            )
            lengths.append(length)
        scored.append(
            score_candidate(
                candidate_index=candidate.index,
                distance_m=candidate.distance_m,
                duration_s=candidate.duration_s,
                segment_lengths=lengths,
                segment_risks=risks,
            )
        )

    chosen = assign_route_types(scored)
    routes: list[RouteResult] = []
    for route_type in _ROUTE_TYPES:
        chosen_route = chosen[route_type]
        candidate_index = chosen_route.candidate_index
        candidate = candidates[candidate_index]
        routes.append(
            RouteResult(
                route_type=route_type,
                distance_m=candidate.distance_m,
                duration_s=candidate.duration_s,
                risk_probability=chosen_route.risk_probability,
                estimated_safety=round((1.0 - chosen_route.risk_probability) * 100),
                confidence=chosen_route.confidence,
                uncertainty=chosen_route.uncertainty,
                high_risk_fraction=chosen_route.high_risk_fraction,
                risk_exposure_m=chosen_route.risk_exposure_m,
                warnings=[*endpoint_warnings, *route_warnings(chosen_route)],
                reasons=list(chosen_route.reasons),
                model_version=MODEL_VERSION,
                segment_ids=matched[candidate_index],
                geometry=candidate.geometry,
            )
        )
    return RoutesResponse(routes=routes)


# Padding (degrees) around the route bbox when querying the segment store.
_MATCH_BBOX_PAD_DEG = 0.003


def _match_all(
    candidates: list[RouteCandidate], segments: SegmentStore
) -> tuple[list[list[int]], dict[int, RoadSegment]]:
    """Map-match all candidates against one union-bbox segment query.

    A single bbox query serves every candidate (PostGIS GIST index), and the
    returned segments are reused for per-segment risk features, so no full
    table scan ever happens on the production store.
    """
    coords = [coord for candidate in candidates for coord in candidate.geometry.coordinates]
    min_lon = min(lon for lon, _ in coords)
    max_lon = max(lon for lon, _ in coords)
    min_lat = min(lat for _, lat in coords)
    max_lat = max(lat for _, lat in coords)
    try:
        nearby = segments.within_bbox(
            min_lon - _MATCH_BBOX_PAD_DEG,
            min_lat - _MATCH_BBOX_PAD_DEG,
            max_lon + _MATCH_BBOX_PAD_DEG,
            max_lat + _MATCH_BBOX_PAD_DEG,
        )
    except NotImplementedError:
        nearby = segments.all()
    nearby_by_id = {seg.id: seg for seg in nearby}
    return (
        [map_match(candidate.geometry.coordinates, nearby) for candidate in candidates],
        nearby_by_id,
    )


def _facility_bbox(candidates: list[RouteCandidate]) -> tuple[float, float, float, float]:
    coords = [coord for candidate in candidates for coord in candidate.geometry.coordinates]
    min_lon = min(lon for lon, _ in coords)
    max_lon = max(lon for lon, _ in coords)
    min_lat = min(lat for _, lat in coords)
    max_lat = max(lat for _, lat in coords)
    return (
        min_lon - FACILITY_BBOX_PAD_DEG,
        min_lat - FACILITY_BBOX_PAD_DEG,
        max_lon + FACILITY_BBOX_PAD_DEG,
        max_lat + FACILITY_BBOX_PAD_DEG,
    )


def _midpoint(coords: tuple[tuple[float, float], ...]) -> tuple[float, float] | None:
    if not coords:
        return None
    return coords[len(coords) // 2]


def _off_network_warning(
    label: str, lon: float, lat: float, nearby: list[RoadSegment]
) -> list[str]:
    """Honest warning when an endpoint is far from the mapped road network.

    We do not snap the endpoint or fabricate a closer start: the route is
    returned as-is, with the distance surfaced so users know the start/end
    may be approximate.
    """
    distance_m = nearest_road_distance_m(lon, lat, nearby)
    if distance_m is None or distance_m <= OFF_NETWORK_THRESHOLD_M:
        return []
    return [
        f"{label} is ~{round(distance_m)} m from the nearest mapped road"
        " — the route may be approximate"
    ]
