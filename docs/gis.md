# GIS: city registry and validation

## City registry — `apps/api/app/gis/cities.py`

Ten monitored cities, each with a bounding box used by the OSM feed and
validation:

| City | bbox (south, west, north, east) |
| --- | --- |
| delhi | 28.40, 76.83, 28.89, 77.35 |
| mumbai | 18.88, 72.77, 19.28, 73.00 |
| bengaluru | 12.84, 77.40, 13.18, 77.80 |
| hyderabad | 17.24, 78.25, 17.59, 78.65 |
| chennai | 12.86, 80.10, 13.22, 80.36 |
| kolkata | 22.43, 88.25, 22.67, 88.48 |
| pune | 18.38, 73.70, 18.65, 73.98 |
| noida | 28.44, 77.26, 28.62, 77.45 |
| ghaziabad | 28.60, 77.37, 28.74, 77.53 |
| jaipur | 26.80, 75.70, 27.05, 76.00 |

API:

- `get_city(name)` — case-insensitive lookup, `None` for unknown.
- `list_cities()` — all registered names.
- `city_for_coords(lat, lon)` — first city whose bbox covers the point.
- `covers_coords(city, lat, lon)` — membership test.

Bboxes are the authoritative coverage claim; if data exists outside a
bbox, the bbox must be widened (never claim coverage you cannot verify).

## Validation — `apps/api/app/gis/validation.py`

```text
usage: python -m app.gis.validation [--city delhi] [--fixture N]
       [--hour-ist H] [--out PATH]
```

- `validate_city(...)` aggregates observations per type and source,
  counts real vs demo vs fixture observations, and computes freshness
  (max age by type), yielding a `CityStats` + `CityValidationReport`.
- `build_fixture(N)` generates deterministic synthetic rows with
  `source_type="fixture"` — clearly labelled, never real, never demo.
- `run_validation` writes the report as a versioned JSON file
  (`data/versions/city-validation-{city}-{date}.json`) and renders a
  terminal table via `render_table`.
- The path resolution uses the repo root (`parents[4]` from the module
  file), so reports always land inside the repository, not the CWD.

## Honesty rules

- Validation reports separate `demo` / `real` / `fixture` observations
  in every counter; aggregations never blend them.
- The ML gate (`ml/ml/gate.py`) mirrors this: only VERIFIED, real
  observations count; fixtures and demos cannot open the gate.
