"""Geocoding utilities for address/place to coordinate conversion.

Uses approved geocoding services only. Respects rate limits and terms.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import requests


@dataclass(frozen=True)
class GeocodeResult:
    """Result of geocoding an address."""

    latitude: float | None
    longitude: float | None
    confidence: float
    method: str
    formatted_address: str | None
    metadata: dict[str, Any] = None


class Geocoder:
    """Base geocoder with rate limiting."""

    def __init__(self, rate_limit: float = 1.0, timeout: int = 10):
        self.rate_limit = rate_limit  # requests per second
        self.timeout = timeout
        self._last_request = 0.0
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "WomenSafetyDatasetPipeline/1.0"})

    def _rate_limit(self) -> None:
        elapsed = time.time() - self._last_request
        if elapsed < (1.0 / self.rate_limit):
            time.sleep((1.0 / self.rate_limit) - elapsed)
        self._last_request = time.time()

    def geocode(self, query: str) -> GeocodeResult:
        raise NotImplementedError


class NominatimGeocoder(Geocoder):
    """OpenStreetMap Nominatim geocoder (free, rate limited to 1 req/sec)."""

    def __init__(self, rate_limit: float = 1.0, timeout: int = 10):
        super().__init__(rate_limit, timeout)
        self.base_url = "https://nominatim.openstreetmap.org/search"

    def geocode(self, query: str, country_codes: str = "in") -> GeocodeResult:
        self._rate_limit()
        params = {
            "q": query,
            "format": "json",
            "limit": 1,
            "countrycodes": country_codes,
            "addressdetails": 1,
        }
        try:
            resp = self.session.get(self.base_url, params=params, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            if data:
                result = data[0]
                return GeocodeResult(
                    latitude=float(result["lat"]),
                    longitude=float(result["lon"]),
                    confidence=float(result.get("importance", 0.5)),
                    method="nominatim",
                    formatted_address=result.get("display_name"),
                    metadata={"place_id": result.get("place_id"), "type": result.get("type")},
                )
        except Exception as e:
            return GeocodeResult(
                latitude=None,
                longitude=None,
                confidence=0.0,
                method="nominatim",
                formatted_address=None,
                metadata={"error": str(e)},
            )
        return GeocodeResult(
            latitude=None,
            longitude=None,
            confidence=0.0,
            method="nominatim",
            formatted_address=None,
            metadata={"error": "no results"},
        )


class PhotonGeocoder(Geocoder):
    """Photon (OSM-based) geocoder."""

    def __init__(self, rate_limit: float = 1.0, timeout: int = 10):
        super().__init__(rate_limit, timeout)
        self.base_url = "https://photon.komoot.io/api/"

    def geocode(self, query: str, lang: str = "en") -> GeocodeResult:
        self._rate_limit()
        params = {"q": query, "limit": 1, "lang": lang}
        try:
            resp = self.session.get(self.base_url, params=params, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            features = data.get("features", [])
            if features:
                feat = features[0]
                coords = feat["geometry"]["coordinates"]
                props = feat["properties"]
                return GeocodeResult(
                    latitude=coords[1],
                    longitude=coords[0],
                    confidence=props.get("confidence", 0.5),
                    method="photon",
                    formatted_address=props.get("name"),
                    metadata={"osm_id": props.get("osm_id"), "type": props.get("type")},
                )
        except Exception as e:
            return GeocodeResult(
                latitude=None,
                longitude=None,
                confidence=0.0,
                method="photon",
                formatted_address=None,
                metadata={"error": str(e)},
            )
        return GeocodeResult(
            latitude=None,
            longitude=None,
            confidence=0.0,
            method="photon",
            formatted_address=None,
            metadata={"error": "no results"},
        )


def get_geocoder(service: str = "nominatim", **kwargs) -> Geocoder:
    """Factory to get geocoder by service name."""
    geocoders = {
        "nominatim": NominatimGeocoder,
        "photon": PhotonGeocoder,
    }
    if service not in geocoders:
        raise ValueError(f"Unknown geocoder: {service}. Available: {list(geocoders.keys())}")
    return geocoders[service](**kwargs)
