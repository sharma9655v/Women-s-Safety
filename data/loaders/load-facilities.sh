#!/usr/bin/env bash
# Load facilities GeoJSON (from `python -m app.facilities`) into PostGIS.
# Requires: ogr2ogr with PostgreSQL driver, running PostGIS.
#
# Usage:
#   DATABASE_URL=postgresql://postgres:postgres@localhost:5432/mapforwomen \
#   DATASET_VERSION=$(date +%Y%m%d) \
#   bash data/loaders/load-facilities.sh facilities.geojson
set -euo pipefail

GEOJSON="${1:?usage: $0 <facilities.geojson>}"
DATABASE_URL="${DATABASE_URL:-postgresql://postgres:postgres@localhost:5432/mapforwomen}"
DATASET_VERSION="${DATASET_VERSION:-$(date +%Y%m%d)}"
PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

echo "[load-facilities] loading $GEOJSON into $DATABASE_URL (version $DATASET_VERSION)"

# Apply schema first (idempotent).
psql "$DATABASE_URL" -f "$PROJECT_ROOT/apps/api/app/db/schema.sql"

# Properties are kept as-is; columns map to facilities table fields.
ogr2ogr -f PostgreSQL \
  -lco GEOMETRY_NAME=geometry -lco SRID=4326 \
  -nln facilities -append \
  -dialect SQLite -sql "SELECT properties->'osm_id' AS osm_id, properties->'type' AS type, properties->'name' AS name, geometry FROM '$GEOJSON'" \
  "PG:${DATABASE_URL}" \
  -fieldTypeToString All

psql "$DATABASE_URL" -v version="$DATASET_VERSION" \
  -c "UPDATE facilities SET dataset_version = :'version' WHERE dataset_version = 'unknown';"

echo "[load-facilities] done. Facilities:"
psql "$DATABASE_URL" -tAc "SELECT type, count(*) FROM facilities GROUP BY type ORDER BY type;"