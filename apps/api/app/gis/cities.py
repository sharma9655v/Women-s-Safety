"""Configuration-driven city definitions for multi-city validation.

No city-specific logic is hardcoded anywhere else: the routing, risk, and
evidence layers operate on coordinates; cities here are bounding boxes used
for validation, feed scoping, and coverage reporting.

Bounding boxes are approximate administrative envelopes (WGS84). They are
sufficient for validation coverage checks, not for legal boundaries.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class City:
    name: str
    state: str
    # (south, west, north, east) in decimal degrees (WGS84).
    bbox: tuple[float, float, float, float]
    notes: str = ""


def _b(s: float, w: float, n: float, e: float) -> tuple[float, float, float, float]:
    return (s, w, n, e)


CITY_REGISTRY: tuple[City, ...] = (
    City("delhi", "NCT Delhi", _b(28.35, 76.75, 28.95, 77.40), "NCT Delhi (default graph extract)"),
    City("mumbai", "Maharashtra", _b(18.85, 72.75, 19.35, 73.05)),
    City("bengaluru", "Karnataka", _b(12.80, 77.40, 13.20, 77.85)),
    City("hyderabad", "Telangana", _b(17.25, 78.25, 17.65, 78.70)),
    City("chennai", "Tamil Nadu", _b(12.85, 80.10, 13.25, 80.40)),
    City("kolkata", "West Bengal", _b(22.40, 88.20, 22.75, 88.55)),
    City("pune", "Maharashtra", _b(18.35, 73.70, 18.75, 74.05)),
    City("noida", "Uttar Pradesh", _b(28.40, 77.25, 28.70, 77.55), "Part of Delhi NCR"),
    City("ghaziabad", "Uttar Pradesh", _b(28.55, 77.30, 28.80, 77.60), "Part of Delhi NCR"),
    City("jaipur", "Rajasthan", _b(26.70, 75.60, 27.10, 76.00)),
)


def get_city(name: str) -> City:
    normalized = name.strip().lower()
    for city in CITY_REGISTRY:
        if city.name == normalized:
            return city
    raise KeyError(f"unknown city {name!r}; supported: {', '.join(c.name for c in CITY_REGISTRY)}")


def list_cities() -> list[City]:
    return list(CITY_REGISTRY)


def city_for_coords(lat: float, lon: float) -> City | None:
    """Return the first city whose bbox contains the coordinate, else None."""
    for city in CITY_REGISTRY:
        south, west, north, east = city.bbox
        if south <= lat <= north and west <= lon <= east:
            return city
    return None


def covers_coords(city: City, lat: float, lon: float) -> bool:
    south, west, north, east = city.bbox
    return south <= lat <= north and west <= lon <= east
