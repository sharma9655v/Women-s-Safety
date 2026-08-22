"""Spatial feature engineering and aggregation."""

from __future__ import annotations

from dataclasses import dataclass

import h3
import numpy as np

from ml.data.config.schema import DatasetRecord


@dataclass(frozen=True)
class SpatialConfig:
    """Configuration for spatial processing."""

    aggregation_method: str = "h3"  # "h3", "geohash", "grid", "administrative"
    h3_resolution: int = 8
    geohash_precision: int = 7
    grid_size_km: float = 1.0
    admin_level: str = "district"
    sensitive_categories: tuple[str, ...] = (
        "sexual_assault",
        "rape",
        "domestic_violence",
        "molestation",
        "kidnapping",
    )


class SpatialProcessor:
    """Generate spatial features and handle privacy-preserving aggregation."""

    def __init__(self, config: SpatialConfig | None = None):
        self.config = config or SpatialConfig()

    def get_cell_id(self, record: DatasetRecord) -> str | None:
        """Get spatial cell ID for a record."""
        if record.latitude is None or record.longitude is None:
            return None

        if self.config.aggregation_method == "h3":
            return h3.latlng_to_cell(record.latitude, record.longitude, self.config.h3_resolution)
        elif self.config.aggregation_method == "geohash":
            return self._geohash(record.latitude, record.longitude, self.config.geohash_precision)
        elif self.config.aggregation_method == "grid":
            return self._grid_cell(record.latitude, record.longitude, self.config.grid_size_km)
        elif self.config.aggregation_method == "administrative":
            return record.district or record.city or "unknown"
        return None

    def _geohash(self, lat: float, lon: float, precision: int) -> str:
        """Simple geohash implementation."""

        # This is a simplified version; use geohash2 or similar in production
        lat_range = [-90.0, 90.0]
        lon_range = [-180.0, 180.0]
        geohash = ""
        bits = [16, 8, 4, 2, 1]
        bit = 0
        ch = 0
        even = True

        while len(geohash) < precision:
            if even:
                mid = (lon_range[0] + lon_range[1]) / 2
                if lon > mid:
                    ch |= bits[bit]
                    lon_range[0] = mid
                else:
                    lon_range[1] = mid
            else:
                mid = (lat_range[0] + lat_range[1]) / 2
                if lat > mid:
                    ch |= bits[bit]
                    lat_range[0] = mid
                else:
                    lat_range[1] = mid

            bit += 1
            if bit == 5:
                base32 = "0123456789bcdefghjkmnpqrstuvwxyz"
                geohash += base32[ch]
                bit = 0
                ch = 0
            even = not even

        return geohash

    def _grid_cell(self, lat: float, lon: float, size_km: float) -> str:
        """Simple grid cell."""
        # Approximate degrees per km at equator
        deg_per_km = 1.0 / 111.0
        lat_cell = int(lat / (size_km * deg_per_km))
        lon_cell = int(lon / (size_km * deg_per_km / np.cos(np.radians(lat))))
        return f"grid_{lat_cell}_{lon_cell}"

    def generalize_coordinates(self, record: DatasetRecord) -> tuple[float | None, float | None]:
        """Generalize coordinates for privacy (sensitive categories)."""
        if not record.crime_category:
            return record.latitude, record.longitude

        if record.crime_category in self.config.sensitive_categories:
            # Return cell centroid instead of exact coordinates
            cell_id = self.get_cell_id(record)
            if cell_id and self.config.aggregation_method == "h3":
                centroid = h3.cell_to_latlng(cell_id)
                return centroid[0], centroid[1]
        return record.latitude, record.longitude

    def compute_spatial_features(
        self, records: list[DatasetRecord], radius_km: float = 1.0
    ) -> dict[str, dict[str, float]]:
        """Compute spatial features for each record."""
        # Build spatial index
        cell_to_records: dict[str, list[DatasetRecord]] = {}
        for record in records:
            cell_id = self.get_cell_id(record)
            if cell_id:
                cell_to_records.setdefault(cell_id, []).append(record)

        features = {}
        for record in records:
            cell_id = self.get_cell_id(record)
            if not cell_id:
                continue

            # Get neighboring cells
            neighbors = self._get_neighbors(cell_id, radius_km)
            neighbor_records = []
            for n_cell in neighbors:
                neighbor_records.extend(cell_to_records.get(n_cell, []))

            # Compute features
            record_features = {
                "incident_count": len(neighbor_records),
                "crime_density": len(neighbor_records) / max(1, len(neighbors)),
                "unique_categories": len(set(r.crime_category for r in neighbor_records)),
                "verified_count": sum(
                    1 for r in neighbor_records if r.verification_state == "VERIFIED"
                ),
                "avg_quality": np.mean([r.data_quality_score or 0 for r in neighbor_records])
                if neighbor_records
                else 0.0,
            }

            # Category-specific densities
            for cat in [
                "harassment",
                "poor_lighting",
                "streetlight_not_working",
                "suspicious_activity",
            ]:
                cat_count = sum(1 for r in neighbor_records if r.crime_category == cat)
                record_features[f"{cat}_density"] = cat_count / max(1, len(neighbor_records))

            features[record.record_id] = record_features

        return features

    def _get_neighbors(self, cell_id: str, radius_km: float) -> list[str]:
        """Get neighboring H3 cells within radius."""
        if self.config.aggregation_method != "h3":
            return [cell_id]

        try:
            # Convert radius to H3 grid-disk distance.
            # Approximate: resolution 8 hexagon edge ~ 0.74km
            k = max(1, int(radius_km / 0.74))
            return list(h3.grid_disk(cell_id, k))
        except Exception:
            return [cell_id]


def add_spatial_features(
    records: list[DatasetRecord], config: SpatialConfig | None = None
) -> list[DatasetRecord]:
    """Return privacy-generalized copies of records.

    DatasetRecord is frozen, so generalization is applied by the export stage
    via SpatialProcessor.generalize_coordinates; this helper exists for
    callers that want a pre-generalized record list.
    """
    processor = SpatialProcessor(config)
    generalized = []
    for record in records:
        gen_lat, gen_lon = processor.generalize_coordinates(record)
        if (gen_lat, gen_lon) == (record.latitude, record.longitude):
            generalized.append(record)
        else:
            from dataclasses import replace

            generalized.append(replace(record, latitude=gen_lat, longitude=gen_lon))
    return generalized
