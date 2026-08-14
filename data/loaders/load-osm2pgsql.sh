#!/usr/bin/env bash
# Load an OSM PBF into PostGIS via osm2pgsql (flex output).
# Requires: osm2pgsql (>= 1.11), running PostGIS (docker compose -f infra/compose.yaml up postgis)
#
# Usage:
#   DATABASE_URL=postgresql://postgres:postgres@localhost:5432/mapforwomen \
#   DATASET_VERSION=$(date +%Y%m%d) \
#   bash data/loaders/load-osm2pgsql.sh data/northern-zone-latest.osm.pbf
set -euo pipefail

PBF="${1:?usage: $0 <extract.osm.pbf>}"
DATABASE_URL="${DATABASE_URL:-postgresql://postgres:postgres@localhost:5432/mapforwomen}"
DATASET_VERSION="${DATASET_VERSION:-$(date +%Y%m%d)}"
PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

# Parse host/port/db from DATABASE_URL (postgresql://user:pass@host:port/db)
URL_NOPROTO="${DATABASE_URL#*://}"
CREDS="${URL_NOPROTO%%@*}"
HOSTPORT="${URL_NOPROTO#*@}"
HOST="${HOSTPORT%%:*}"
PORT="${HOSTPORT##*:}"
PORT="${PORT%%/*}"
DB="${HOSTPORT##*/}"
USER="${CREDS%%:*}"
PASS="${CREDS#*:}"

export PGPASSWORD="$PASS"

echo "[load-osm2pgsql] loading $PBF into $DB@$HOST:$PORT (version $DATASET_VERSION)"

osm2pgsql \
  -d "$DB" -U "$USER" -H "$HOST" -P "$PORT" \
  -O flex \
  --style "$PROJECT_ROOT/infra/osm2pgsql/roads-flex.lua" \
  --slim --drop \
  "$PBF"

# stamp the version only on newly inserted rows
psql "postgresql://$USER:$PASS@$HOST:$PORT/$DB" \
  -v version="$DATASET_VERSION" \
  -c "UPDATE road_segments SET dataset_version = :'version' WHERE dataset_version = 'unknown';"

echo "[load-osm2pgsql] done. Segments:"
psql "postgresql://$USER:$PASS@$HOST:$PORT/$DB" -tAc "SELECT count(*) FROM road_segments;"