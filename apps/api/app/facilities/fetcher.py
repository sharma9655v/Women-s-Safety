from __future__ import annotations

from typing import Any

import httpx

DEFAULT_OVERPASS_URL = "https://overpass-api.de/api/interpreter"
USER_AGENT = "map-for-women/0.1 (dev; safety-facilities fetcher)"

# (tag key, tag value regex) -> facility type per data-model.md
FACILITY_MATCHERS: tuple[tuple[str, str, str], ...] = (
    ("amenity", "police", "police"),
    ("amenity", "hospital", "hospital"),
    ("amenity", "pharmacy", "pharmacy"),
    ("amenity", "fire_station", "fire_station"),
    ("highway", "bus_stop", "transit_stop"),
    ("railway", "^(station|tram_stop)$", "transit_stop"),
    ("amenity", "community_centre", "public_place"),
    ("leisure", "park", "public_place"),
)

QUERY_TEMPLATE = """\
[out:json][timeout:60];
(
{clauses}
);
out body;
"""


def build_query(min_lon: float, min_lat: float, max_lon: float, max_lat: float) -> str:
    clauses = []
    for key, value, _ in FACILITY_MATCHERS:
        if value.startswith("^"):
            clause = f'node["{key}"~"{value}"]({min_lat},{min_lon},{max_lat},{max_lon});'
        else:
            clause = f'node["{key}"="{value}"]({min_lat},{min_lon},{max_lat},{max_lon});'
        clauses.append(clause)
    return QUERY_TEMPLATE.format(clauses="\n".join(clauses))


def classify(tags: dict[str, Any]) -> str | None:
    for key, value, facility_type in FACILITY_MATCHERS:
        if value.startswith("^"):
            import re

            if re.fullmatch(value, str(tags.get(key, ""))):
                return facility_type
        elif tags.get(key) == value:
            return facility_type
    return None


class FacilityFetcher:
    def __init__(
        self,
        base_url: str = DEFAULT_OVERPASS_URL,
        transport: httpx.BaseTransport | None = None,
        timeout: float = 90.0,
    ) -> None:
        self._client = httpx.Client(
            base_url=base_url,
            timeout=timeout,
            transport=transport,
            headers={"User-Agent": USER_AGENT},
        )

    def close(self) -> None:
        self._client.close()

    def fetch(
        self, min_lon: float, min_lat: float, max_lon: float, max_lat: float
    ) -> dict[str, Any]:
        query = build_query(min_lon, min_lat, max_lon, max_lat)
        resp = self._client.post("/", data={"data": query})
        if resp.status_code == 429:
            raise httpx.HTTPStatusError(
                "Overpass rate-limited this query (HTTP 429). "
                "Wait a minute or shrink the bbox and retry.",
                request=resp.request,
                response=resp,
            )
        resp.raise_for_status()
        return self._to_feature_collection(resp.json())

    def _to_feature_collection(self, payload: dict[str, Any]) -> dict[str, Any]:
        features: list[dict[str, Any]] = []
        for element in payload.get("elements", []):
            if element.get("type") != "node":
                continue
            tags = element.get("tags", {}) or {}
            facility_type = classify(tags)
            if facility_type is None:
                continue
            lon = element.get("lon")
            lat = element.get("lat")
            if lon is None or lat is None:
                continue
            features.append(
                {
                    "type": "Feature",
                    "id": element.get("id"),
                    "properties": {
                        "osm_id": element.get("id"),
                        "type": facility_type,
                        "name": tags.get("name"),
                    },
                    "geometry": {"type": "Point", "coordinates": [lon, lat]},
                }
            )
        return {"type": "FeatureCollection", "features": features}


def validate_bbox(min_lon: float, min_lat: float, max_lon: float, max_lat: float) -> None:
    if not (-180 <= min_lon <= 180 and -180 <= max_lon <= 180):
        raise ValueError("longitudes out of range")
    if not (-90 <= min_lat <= 90 and -90 <= max_lat <= 90):
        raise ValueError("latitudes out of range")
    if min_lon >= max_lon or min_lat >= max_lat:
        raise ValueError("bbox must be min < max on both axes")
