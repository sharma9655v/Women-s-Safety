from __future__ import annotations

from urllib.parse import urlencode

import httpx

from app.schemas import LatLon, RouteCandidate, RouteGeometry

MODE_PROFILE = {
    "walking": "foot",
    "driving": "car",
    "cycling": "bicycle",
}

# OSRM supports up to 3 alternatives; alternatives=2 gives 3 candidates total.
MAX_ALTERNATIVES = 2
MAX_CANDIDATES = 3


class OsrmError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(f"OSRM error {code}: {message}")


def build_route_url(
    base_url: str,
    origin: LatLon,
    destination: LatLon,
    mode: str,
    alternatives: int = MAX_ALTERNATIVES,
) -> str:
    profile = MODE_PROFILE[mode]
    coords = f"{origin.lon},{origin.lat};{destination.lon},{destination.lat}"
    query = urlencode(
        {
            "alternatives": alternatives,
            "overview": "full",
            "geometries": "geojson",
            "steps": "false",
        }
    )
    return f"{base_url.rstrip('/')}/route/v1/{profile}/{coords}?{query}"


class OsrmClient:
    def __init__(
        self,
        base_url: str,
        timeout: float = 15.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._client = httpx.Client(base_url=base_url, timeout=timeout, transport=transport)

    def close(self) -> None:
        self._client.close()

    def routes(self, origin: LatLon, destination: LatLon, mode: str) -> list[RouteCandidate]:
        url = build_route_url(self._base_url, origin, destination, mode)
        resp = self._client.get(url)
        if resp.status_code != 200:
            payload = resp.json()
            raise OsrmError(payload.get("code", "unknown"), payload.get("message", ""))
        return self._parse_routes(resp.json())

    def _parse_routes(self, payload: dict[str, object]) -> list[RouteCandidate]:
        candidates: list[RouteCandidate] = []
        routes = payload.get("routes", [])
        if not isinstance(routes, list):
            routes = []
        for index, route in enumerate(routes[:MAX_CANDIDATES]):
            if not isinstance(route, dict):
                continue
            geometry = route.get("geometry", {})
            coordinates = geometry.get("coordinates", []) if isinstance(geometry, dict) else []
            candidates.append(
                RouteCandidate(
                    index=index,
                    distance_m=float(route.get("distance", 0.0) or 0.0),
                    duration_s=float(route.get("duration", 0.0) or 0.0),
                    geometry=RouteGeometry(coordinates=coordinates),
                )
            )
        return candidates
