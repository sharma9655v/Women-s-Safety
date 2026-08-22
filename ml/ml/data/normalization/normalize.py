"""Normalization pipeline for converting raw records to canonical schema."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from ml.data.config.schema import (
    CRIME_CATEGORY_MAPPING,
    CrimeCategory,
    GeocodingMethod,
    SourceType,
    VerificationState,
)


@dataclass(frozen=True)
class NormalizedRecord:
    """Intermediate normalized record before final validation."""

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
    original_category: str | None
    original_source_record_id: str | None
    processing_version: str = "1.0.0"


class NormalizationError(Exception):
    """Raised when normalization fails for a record."""

    pass


class Normalizer:
    """Normalize raw source records to canonical schema."""

    def __init__(
        self, dataset_version: str, source_mapping: dict[str, CrimeCategory] | None = None
    ):
        self.dataset_version = dataset_version
        self.source_mapping = source_mapping or {}
        self.collection_timestamp = datetime.now(UTC).isoformat() + "Z"

    def normalize(
        self, raw_record: dict[str, Any], source_config: dict[str, Any]
    ) -> NormalizedRecord:
        """Normalize a single raw record."""
        source_id = source_config["source_id"]
        source_type = SourceType(source_config.get("source_type", "official"))

        # Generate record ID
        record_id = self._generate_record_id(source_id, raw_record)

        # Normalize crime category
        crime_category, crime_subcategory, original_category = self._normalize_category(
            raw_record, source_config
        )

        # Normalize dates
        incident_date, incident_time = self._normalize_datetime(raw_record, source_config)

        # Normalize coordinates
        latitude, longitude = self._normalize_coordinates(raw_record, source_config)

        # Normalize administrative areas
        district, city, state, country = self._normalize_admin(raw_record, source_config)

        # Description availability
        description_available = self._check_description(raw_record)

        # Verification state
        verification_state = self._normalize_verification_state(raw_record, source_config)

        # Source URL
        source_url = self._extract_source_url(raw_record, source_config)

        # Geocoding info
        geocoding_method, geocoding_confidence, spatial_precision = self._normalize_geocoding(
            raw_record, source_config
        )

        # Data quality score
        data_quality_score = self._compute_quality_score(
            latitude,
            longitude,
            incident_date,
            crime_category,
            verification_state,
            description_available,
        )

        return NormalizedRecord(
            record_id=record_id,
            source_id=source_id,
            source_name=source_config["source_name"],
            source_type=source_type,
            crime_category=crime_category,
            crime_subcategory=crime_subcategory,
            incident_date=incident_date,
            incident_time=incident_time,
            latitude=latitude,
            longitude=longitude,
            district=district,
            city=city,
            state=state,
            country=country,
            description_available=description_available,
            verification_state=verification_state,
            source_url=source_url,
            collection_timestamp=self.collection_timestamp,
            geocoding_method=geocoding_method,
            geocoding_confidence=geocoding_confidence,
            spatial_precision=spatial_precision,
            data_quality_score=data_quality_score,
            dataset_version=self.dataset_version,
            original_category=original_category,
            original_source_record_id=self._extract_source_record_id(raw_record, source_config),
        )

    def _generate_record_id(self, source_id: str, raw_record: dict[str, Any]) -> str:
        import hashlib

        source_rec_id = self._extract_source_record_id(raw_record, {"source_id": source_id})
        if source_rec_id:
            base = f"{source_id}:{source_rec_id}"
        else:
            import json

            digest = hashlib.sha256(json.dumps(raw_record, sort_keys=True).encode()).hexdigest()[
                :16
            ]
            base = f"{source_id}:{digest}"
        return hashlib.sha256(base.encode()).hexdigest()[:32]

    def _extract_source_record_id(
        self, raw_record: dict[str, Any], source_config: dict[str, Any]
    ) -> str | None:
        for field in ["id", "record_id", "uuid", "incident_id", "case_id", "fir_no"]:
            if field in raw_record and raw_record[field]:
                return str(raw_record[field])
        return None

    def _normalize_category(
        self, raw_record: dict[str, Any], source_config: dict[str, Any]
    ) -> tuple[CrimeCategory, str | None, str | None]:
        source_id = source_config["source_id"]
        mapping = CRIME_CATEGORY_MAPPING.get(source_id, {})

        category_fields = ["category", "crime_category", "offense_type", "incident_type", "type"]
        original_category = None
        for field in category_fields:
            if field in raw_record and raw_record[field]:
                original_category = str(raw_record[field]).strip().lower()
                break

        if not original_category:
            return CrimeCategory.OTHER, None, None

        normalized = mapping.get(original_category)
        if normalized:
            return normalized, original_category, original_category

        for src_cat, norm_cat in mapping.items():
            if src_cat.lower() in original_category or original_category in src_cat.lower():
                return norm_cat, original_category, original_category

        try:
            return CrimeCategory(original_category), original_category, original_category
        except ValueError:
            pass

        return CrimeCategory.OTHER, original_category, original_category

    def _normalize_datetime(
        self, raw_record: dict[str, Any], source_config: dict[str, Any]
    ) -> tuple[str, str | None]:
        date_fields = [
            "date",
            "incident_date",
            "occurred_date",
            "reported_date",
            "datetime",
            "timestamp",
        ]
        time_fields = ["time", "incident_time", "occurred_time", "reported_time"]

        incident_date = None
        incident_time = None

        for field in date_fields:
            if field in raw_record and raw_record[field]:
                try:
                    parsed = self._parse_date(str(raw_record[field]))
                    if parsed:
                        incident_date = parsed.strftime("%Y-%m-%d")
                        if isinstance(raw_record[field], str) and "T" in raw_record[field]:
                            time_part = raw_record[field].split("T")[1]
                            if ":" in time_part:
                                incident_time = time_part[:8]
                        break
                except Exception:
                    continue

        if not incident_time:
            for field in time_fields:
                if field in raw_record and raw_record[field]:
                    try:
                        parsed_time = self._parse_time(str(raw_record[field]))
                        if parsed_time:
                            incident_time = parsed_time.strftime("%H:%M:%S")
                            break
                    except Exception:
                        continue

        # No date -> empty string. Validation rejects it (fail loud).
        # Never substitute collection time for incident time: that would
        # fabricate a temporal fact.
        if not incident_date:
            incident_date = ""

        return incident_date, incident_time

    def _parse_date(self, date_str: str) -> datetime | None:
        formats = [
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%d-%m-%Y",
            "%d/%m/%Y",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%d %H:%M:%S",
            "%d-%m-%Y %H:%M:%S",
            "%B %d, %Y",
            "%b %d, %Y",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except ValueError:
                continue
        return None

    def _parse_time(self, time_str: str) -> datetime | None:
        formats = [
            "%H:%M:%S",
            "%H:%M",
            "%I:%M:%S %p",
            "%I:%M %p",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(time_str.strip(), fmt)
            except ValueError:
                continue
        return None

    def _normalize_coordinates(
        self, raw_record: dict[str, Any], source_config: dict[str, Any]
    ) -> tuple[float | None, float | None]:
        lat = None
        lon = None

        lat_fields = ["latitude", "lat", "y", "y_coord"]
        lon_fields = ["longitude", "lon", "lng", "x", "x_coord"]

        for field in lat_fields:
            if field in raw_record and raw_record[field] is not None:
                try:
                    lat = float(raw_record[field])
                    break
                except (ValueError, TypeError):
                    continue

        for field in lon_fields:
            if field in raw_record and raw_record[field] is not None:
                try:
                    lon = float(raw_record[field])
                    break
                except (ValueError, TypeError):
                    continue

        if lat is not None and (lat < -90 or lat > 90):
            lat = None
        if lon is not None and (lon < -180 or lon > 180):
            lon = None

        return lat, lon

    def _normalize_admin(
        self, raw_record: dict[str, Any], source_config: dict[str, Any]
    ) -> tuple[str | None, str | None, str | None, str | None]:
        district = raw_record.get("district") or raw_record.get("district_name")
        city = (
            raw_record.get("city") or raw_record.get("city_name") or raw_record.get("municipality")
        )
        state = (
            raw_record.get("state") or raw_record.get("state_name") or raw_record.get("province")
        )
        country = raw_record.get("country") or raw_record.get("country_name") or "India"

        if state:
            state = self._normalize_state(state)

        return district, city, state, country

    def _normalize_state(self, state_name: str) -> str:
        state_map = {
            "delhi": "Delhi",
            "nct of delhi": "Delhi",
            "new delhi": "Delhi",
            "maharashtra": "Maharashtra",
            "karnataka": "Karnataka",
            "tamil nadu": "Tamil Nadu",
            "uttar pradesh": "Uttar Pradesh",
            "west bengal": "West Bengal",
            "gujarat": "Gujarat",
            "rajasthan": "Rajasthan",
            "madhya pradesh": "Madhya Pradesh",
            "bihar": "Bihar",
            "andhra pradesh": "Andhra Pradesh",
            "telangana": "Telangana",
            "kerala": "Kerala",
            "odisha": "Odisha",
            "punjab": "Punjab",
            "haryana": "Haryana",
            "assam": "Assam",
            "jharkhand": "Jharkhand",
            "chhattisgarh": "Chhattisgarh",
            "uttarakhand": "Uttarakhand",
            "himachal pradesh": "Himachal Pradesh",
            "goa": "Goa",
            "jammu and kashmir": "Jammu and Kashmir",
            "ladakh": "Ladakh",
        }
        normalized = state_name.strip().lower()
        return state_map.get(normalized, state_name.title())

    def _check_description(self, raw_record: dict[str, Any]) -> bool:
        desc_fields = ["description", "details", "narrative", "summary", "text"]
        for field in desc_fields:
            if field in raw_record and raw_record[field]:
                val = str(raw_record[field]).strip()
                if val and len(val) > 10:
                    return True
        return False

    def _normalize_verification_state(
        self, raw_record: dict[str, Any], source_config: dict[str, Any]
    ) -> VerificationState:
        state_fields = ["verification_state", "status", "verification", "case_status"]
        for field in state_fields:
            if field in raw_record and raw_record[field]:
                val = str(raw_record[field]).strip().upper()
                try:
                    return VerificationState(val)
                except ValueError:
                    mapping = {
                        "CONFIRMED": VerificationState.VERIFIED,
                        "VERIFIED": VerificationState.VERIFIED,
                        "REPORTED": VerificationState.REPORTED,
                        "PENDING": VerificationState.REPORTED,
                        "UNDER_INVESTIGATION": VerificationState.REPORTED,
                        "CLOSED": VerificationState.VERIFIED,
                        "RESOLVED": VerificationState.VERIFIED,
                        "REJECTED": VerificationState.REJECTED,
                        "FALSE": VerificationState.REJECTED,
                        "UNFOUNDED": VerificationState.REJECTED,
                    }
                    return mapping.get(val, VerificationState.REPORTED)
        return VerificationState.REPORTED

    def _extract_source_url(
        self, raw_record: dict[str, Any], source_config: dict[str, Any]
    ) -> str | None:
        url_fields = ["source_url", "url", "link", "reference_url", "permalink"]
        for field in url_fields:
            if field in raw_record and raw_record[field]:
                return str(raw_record[field])
        return source_config.get("source_url")

    def _normalize_geocoding(
        self, raw_record: dict[str, Any], source_config: dict[str, Any]
    ) -> tuple[GeocodingMethod, float | None, str | None]:
        has_source_coords = "latitude" in raw_record and "longitude" in raw_record
        geocoded = raw_record.get("geocoded", False)

        if has_source_coords and not geocoded:
            return GeocodingMethod.SOURCE_PROVIDED, 1.0, "exact"
        if geocoded:
            confidence = raw_record.get("geocoding_confidence")
            return (
                GeocodingMethod.GEOCODED_API,
                float(confidence) if confidence else 0.8,
                "approximate",
            )

        if raw_record.get("district") or raw_record.get("city"):
            return GeocodingMethod.ADMINISTRATIVE_CENTROID, 0.5, "administrative"

        return GeocodingMethod.UNKNOWN, None, "unknown"

    def _compute_quality_score(
        self,
        latitude: float | None,
        longitude: float | None,
        incident_date: str,
        crime_category: CrimeCategory,
        verification_state: VerificationState,
        description_available: bool,
    ) -> float:
        score = 0.0

        if latitude is not None and longitude is not None:
            score += 0.25

        try:
            datetime.strptime(incident_date, "%Y-%m-%d")
            score += 0.2
        except ValueError:
            pass

        if crime_category != CrimeCategory.OTHER:
            score += 0.2

        if verification_state == VerificationState.VERIFIED:
            score += 0.2
        elif verification_state in (VerificationState.CORROBORATED, VerificationState.CONFLICTING):
            score += 0.15
        else:
            score += 0.1

        if description_available:
            score += 0.15

        return min(1.0, score)


def normalize_records(
    raw_records: list[dict[str, Any]], source_config: dict[str, Any], dataset_version: str
) -> list[NormalizedRecord]:
    normalizer = Normalizer(dataset_version)
    normalized = []
    for raw in raw_records:
        try:
            normalized.append(normalizer.normalize(raw, source_config))
        except Exception as e:
            import logging

            logging.warning(f"Failed to normalize record: {e}")
            continue
    return normalized
