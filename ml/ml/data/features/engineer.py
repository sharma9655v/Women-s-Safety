"""Feature engineering for ML dataset."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import numpy as np

from ml.data.config.schema import DatasetRecord


@dataclass(frozen=True)
class FeatureConfig:
    """Configuration for feature engineering."""

    include_temporal: bool = True
    include_spatial: bool = True
    include_environmental: bool = True
    temporal_window_days: int = 90
    spatial_radius_km: float = 1.0


class FeatureEngineer:
    """Generate ML features from normalized records."""

    def __init__(self, config: FeatureConfig | None = None):
        self.config = config or FeatureConfig()

    def engineer_features(self, records: list[DatasetRecord]) -> dict[str, dict[str, float]]:
        """Generate features for each record."""
        features = {}

        for record in records:
            record_features = {}

            # Temporal features
            if self.config.include_temporal:
                record_features.update(self._temporal_features(record))

            # Spatial features (requires spatial index)
            if self.config.include_spatial:
                record_features.update(self._spatial_features(record, records))

            # Environmental features (placeholder - needs external data)
            if self.config.include_environmental:
                record_features.update(self._environmental_features(record))

            # Source reliability
            record_features["source_reliability"] = 0.0  # Will be filled from source registry

            features[record.record_id] = record_features

        return features

    def _temporal_features(self, record: DatasetRecord) -> dict[str, float]:
        """Extract temporal features."""
        features = {}

        try:
            dt = datetime.strptime(record.incident_date, "%Y-%m-%d")
            features["year"] = float(dt.year)
            features["month"] = float(dt.month)
            features["day_of_week"] = float(dt.weekday())  # 0=Monday
            features["day_of_year"] = float(dt.timetuple().tm_yday)
            features["week_of_year"] = float(dt.isocalendar()[1])
            features["is_weekend"] = 1.0 if dt.weekday() >= 5 else 0.0

            # Season (Northern hemisphere)
            month = dt.month
            if month in [12, 1, 2]:
                features["season"] = 0.0  # Winter
            elif month in [3, 4, 5]:
                features["season"] = 1.0  # Spring
            elif month in [6, 7, 8]:
                features["season"] = 2.0  # Summer
            else:
                features["season"] = 3.0  # Autumn

            # Hour if available
            if record.incident_time:
                try:
                    hour = int(record.incident_time.split(":")[0])
                    features["hour"] = float(hour)
                    features["is_night"] = 1.0 if hour < 6 or hour >= 20 else 0.0
                    features["is_rush_hour"] = (
                        1.0 if (7 <= hour <= 9) or (17 <= hour <= 19) else 0.0
                    )
                except Exception:
                    features["hour"] = -1.0
                    features["is_night"] = 0.0
                    features["is_rush_hour"] = 0.0
            else:
                features["hour"] = -1.0
                features["is_night"] = 0.0
                features["is_rush_hour"] = 0.0

        except Exception:
            features.update(
                {
                    "year": 0.0,
                    "month": 0.0,
                    "day_of_week": 0.0,
                    "day_of_year": 0.0,
                    "week_of_year": 0.0,
                    "is_weekend": 0.0,
                    "season": 0.0,
                    "hour": -1.0,
                    "is_night": 0.0,
                    "is_rush_hour": 0.0,
                }
            )

        return features

    def _spatial_features(
        self, record: DatasetRecord, all_records: list[DatasetRecord]
    ) -> dict[str, float]:
        """Extract spatial features (simplified - needs spatial index for efficiency)."""
        features = {}

        if record.latitude is None or record.longitude is None:
            return {
                "incident_count": 0.0,
                "crime_density": 0.0,
                "verified_ratio": 0.0,
                "category_diversity": 0.0,
            }

        # Find nearby records (naive O(n) - use spatial index in production)
        nearby = []
        for other in all_records:
            if other.record_id == record.record_id:
                continue
            if other.latitude is None or other.longitude is None:
                continue

            dist = self._haversine_distance(
                record.latitude, record.longitude, other.latitude, other.longitude
            )
            if dist <= self.config.spatial_radius_km:
                nearby.append(other)

        features["incident_count"] = float(len(nearby))

        if nearby:
            features["crime_density"] = len(nearby) / (np.pi * self.config.spatial_radius_km**2)
            verified = sum(1 for r in nearby if r.verification_state == "VERIFIED")
            features["verified_ratio"] = verified / len(nearby)
            features["category_diversity"] = float(len(set(r.crime_category for r in nearby)))
        else:
            features["crime_density"] = 0.0
            features["verified_ratio"] = 0.0
            features["category_diversity"] = 0.0

        return features

    def _environmental_features(self, record: DatasetRecord) -> dict[str, float]:
        """Environmental features (placeholder - requires external data)."""
        # In production, these would come from:
        # - Police station locations
        # - Hospital locations
        # - Transit stops
        # - Streetlight data (OSM)
        # - Road network
        # - Land use
        return {
            "dist_to_police": -1.0,
            "dist_to_hospital": -1.0,
            "dist_to_transit": -1.0,
            "streetlight_density": -1.0,
            "road_density": -1.0,
            "commercial_area": 0.0,
            "residential_area": 0.0,
            "park_area": 0.0,
        }

    @staticmethod
    def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points in km."""
        R = 6371.0  # Earth radius in km
        lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
        c = 2 * np.arcsin(np.sqrt(a))
        return R * c


def generate_targets(
    records: list[DatasetRecord],
    target_type: str = "future_incident_density",
    prediction_horizon_days: int = 90,
) -> dict[str, float]:
    """Generate ML targets from historical records.

    This is a placeholder - actual implementation requires:
    1. Temporal split (train on past, predict future)
    2. Spatial aggregation to grid cells
    3. Time series of incident counts per cell
    """
    # Placeholder - returns empty dict
    # Real implementation would:
    # 1. Aggregate records to spatial cells + time bins
    # 2. Create time series per cell
    # 3. Define target as future incident count/density
    return {}


def split_temporal(
    records: list[DatasetRecord],
    train_end: str,
    validation_end: str,
    test_start: str,
) -> tuple[list[DatasetRecord], list[DatasetRecord], list[DatasetRecord]]:
    """Split records temporally to avoid leakage."""
    train_end_dt = datetime.strptime(train_end, "%Y-%m-%d")
    validation_end_dt = datetime.strptime(validation_end, "%Y-%m-%d")

    train = []
    validation = []
    test = []

    for record in records:
        try:
            dt = datetime.strptime(record.incident_date, "%Y-%m-%d")
            if dt <= train_end_dt:
                train.append(record)
            elif dt <= validation_end_dt:
                validation.append(record)
            else:
                test.append(record)
        except Exception:
            train.append(record)  # Default to train if date parsing fails

    return train, validation, test
