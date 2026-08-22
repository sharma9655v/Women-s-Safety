"""GIS layer: configuration-driven city definitions + multi-city validation.

- cities.py     — city registry (bboxes), coordinate membership helpers
- validation.py — per-city validation pipeline, cross-city report, CLI

The routing/risk/evidence layers stay city-agnostic: cities are only used
for validation scoping, feed bounding boxes, and coverage reporting.
"""

from app.gis.cities import (
    CITY_REGISTRY,
    City,
    city_for_coords,
    covers_coords,
    get_city,
    list_cities,
)
from app.gis.validation import (
    CityStats,
    CityValidationReport,
    build_fixture,
    main,
    render_table,
    run_validation,
    validate_city,
    write_report,
)

__all__ = [
    "CITY_REGISTRY",
    "City",
    "CityStats",
    "CityValidationReport",
    "build_fixture",
    "city_for_coords",
    "covers_coords",
    "get_city",
    "list_cities",
    "main",
    "render_table",
    "run_validation",
    "validate_city",
    "write_report",
]
