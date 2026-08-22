"""Canonical dataset schema for Women Safety ML dataset.

Defines the normalized record schema, source registry schema,
and all validation rules. Do not modify without updating version.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class CrimeCategory(StrEnum):
    # Normalized categories; every source mapping must be explicit + traceable.

    SEXUAL_ASSAULT = "sexual_assault"
    RAPE = "rape"
    HARASSMENT = "harassment"
    STALKING = "stalking"
    KIDNAPPING = "kidnapping"
    DOMESTIC_VIOLENCE = "domestic_violence"
    MOLESTATION = "molestation"
    ROBBERY = "robbery"
    ASSAULT = "assault"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    POOR_LIGHTING = "poor_lighting"
    STREETLIGHT_NOT_WORKING = "streetlight_not_working"
    BLOCKED_SIDEWALK = "blocked_sidewalk"
    ROAD_HAZARD = "road_hazard"
    UNSAFE_TRANSPORT = "unsafe_transport"
    OTHER = "other"


class SourceType(StrEnum):
    # Classification aligned with the evidence engine's data_sources table.

    OFFICIAL = "official"
    RESEARCH = "research"
    COMMUNITY = "community"
    AGGREGATED = "aggregated"
    DEMO_SEED = "demo_seed"
    OSM = "osm"
    GOVERNMENT = "government"
    NCRB = "ncrb"
    MUNICIPAL = "municipal"


class VerificationState(StrEnum):
    # States produced by apps/api evidence engine (schema.sql CHECK).

    VERIFIED = "VERIFIED"
    REPORTED = "REPORTED"
    CORROBORATED = "CORROBORATED"
    CONFLICTING = "CONFLICTING"
    EXPIRED = "EXPIRED"
    REJECTED = "REJECTED"


class GeocodingMethod(StrEnum):
    # Provenance of latitude/longitude for a record.

    SOURCE_PROVIDED = "source_provided"
    GEOCODED_API = "geocoded_api"
    GEOCODED_MANUAL = "geocoded_manual"
    ADMINISTRATIVE_CENTROID = "administrative_centroid"
    GRID_CENTROID = "grid_centroid"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class DatasetRecord:
    """Canonical normalized dataset record."""

    record_id: str
    source_id: str
    source_name: str
    source_type: SourceType
    crime_category: CrimeCategory
    crime_subcategory: str | None
    incident_date: str
    incident_time: str | None
    latitude: float | None
    longitude: float | None
    district: str | None
    city: str | None
    state: str | None
    country: str | None
    description_available: bool
    verification_state: VerificationState
    source_url: str | None
    collection_timestamp: str
    geocoding_method: GeocodingMethod
    geocoding_confidence: float | None
    spatial_precision: str | None
    data_quality_score: float | None
    dataset_version: str

    # Original fields for traceability
    original_category: str | None = None
    original_source_record_id: str | None = None
    processing_version: str = "1.0.0"

    @staticmethod
    def _value(field: Any) -> Any:
        """Accept enum or plain string for serialized fields."""
        return getattr(field, "value", field)

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "source_id": self.source_id,
            "source_name": self.source_name,
            "source_type": self._value(self.source_type),
            "crime_category": self._value(self.crime_category),
            "crime_subcategory": self.crime_subcategory,
            "incident_date": self.incident_date,
            "incident_time": self.incident_time,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "district": self.district,
            "city": self.city,
            "state": self.state,
            "country": self.country,
            "description_available": self.description_available,
            "verification_state": self._value(self.verification_state),
            "source_url": self.source_url,
            "collection_timestamp": self.collection_timestamp,
            "geocoding_method": self._value(self.geocoding_method),
            "geocoding_confidence": self.geocoding_confidence,
            "spatial_precision": self.spatial_precision,
            "data_quality_score": self.data_quality_score,
            "dataset_version": self.dataset_version,
            "original_category": self.original_category,
            "original_source_record_id": self.original_source_record_id,
            "processing_version": self.processing_version,
        }

    @classmethod
    def field_names(cls) -> list[str]:
        return [
            "record_id",
            "source_id",
            "source_name",
            "source_type",
            "crime_category",
            "crime_subcategory",
            "incident_date",
            "incident_time",
            "latitude",
            "longitude",
            "district",
            "city",
            "state",
            "country",
            "description_available",
            "verification_state",
            "source_url",
            "collection_timestamp",
            "geocoding_method",
            "geocoding_confidence",
            "spatial_precision",
            "data_quality_score",
            "dataset_version",
            "original_category",
            "original_source_record_id",
            "processing_version",
        ]


@dataclass(frozen=True)
class SourceRegistryEntry:
    """Source registry entry with licensing and provenance."""

    source_id: str
    source_name: str
    source_type: SourceType
    publisher: str
    license: str
    source_url: str
    geographical_coverage: str
    temporal_coverage: str
    update_frequency: str
    allowed_usage: str
    reliability_level: float
    parser: str
    enabled: bool = True
    checksum: str | None = None
    last_checked: str | None = None
    last_updated: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "source_name": self.source_name,
            "source_type": self.source_type.value,
            "publisher": self.publisher,
            "license": self.license,
            "source_url": self.source_url,
            "geographical_coverage": self.geographical_coverage,
            "temporal_coverage": self.temporal_coverage,
            "update_frequency": self.update_frequency,
            "allowed_usage": self.allowed_usage,
            "reliability_level": self.reliability_level,
            "parser": self.parser,
            "enabled": self.enabled,
            "checksum": self.checksum,
            "last_checked": self.last_checked,
            "last_updated": self.last_updated,
        }


# Crime category mapping configuration
# Each source category must be explicitly mapped
CRIME_CATEGORY_MAPPING: dict[str, dict[str, CrimeCategory]] = {
    "ncrb": {
        "rape": CrimeCategory.RAPE,
        "sexual_assault": CrimeCategory.SEXUAL_ASSAULT,
        "harassment": CrimeCategory.HARASSMENT,
        "stalking": CrimeCategory.STALKING,
        "kidnapping": CrimeCategory.KIDNAPPING,
        "domestic_violence": CrimeCategory.DOMESTIC_VIOLENCE,
        "molestation": CrimeCategory.MOLESTATION,
        "robbery": CrimeCategory.ROBBERY,
        "assault": CrimeCategory.ASSAULT,
    },
    "municipal": {
        "streetlight_not_working": CrimeCategory.STREETLIGHT_NOT_WORKING,
        "poor_lighting": CrimeCategory.POOR_LIGHTING,
        "blocked_sidewalk": CrimeCategory.BLOCKED_SIDEWALK,
        "road_hazard": CrimeCategory.ROAD_HAZARD,
        "harassment": CrimeCategory.HARASSMENT,
        "suspicious_activity": CrimeCategory.SUSPICIOUS_ACTIVITY,
    },
    "osm": {
        "streetlight_not_working": CrimeCategory.STREETLIGHT_NOT_WORKING,
        "poor_lighting": CrimeCategory.POOR_LIGHTING,
    },
    "research": {
        # To be defined per dataset
    },
}


# Required fields for a valid record
REQUIRED_FIELDS = [
    "record_id",
    "source_id",
    "source_name",
    "source_type",
    "crime_category",
    "incident_date",
    "verification_state",
    "collection_timestamp",
    "dataset_version",
]


# Validation rules
VALIDATION_RULES = {
    "latitude": {"type": "float", "min": -90, "max": 90, "required": False},
    "longitude": {"type": "float", "min": -180, "max": 180, "required": False},
    "geocoding_confidence": {"type": "float", "min": 0.0, "max": 1.0, "required": False},
    "data_quality_score": {"type": "float", "min": 0.0, "max": 1.0, "required": False},
    "reliability_level": {"type": "float", "min": 0.0, "max": 1.0, "required": True},
    "incident_date": {"type": "date", "format": "%Y-%m-%d", "required": True},
    "incident_time": {"type": "time", "format": "%H:%M:%S", "required": False},
}
