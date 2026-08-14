#!/usr/bin/env bash
set -euo pipefail

# OSRM bootstrapper for Map for Women.
# Downloads an OSM PBF extract (configurable), builds the walking graph once,
# and starts osrm-routed. A marker file signals that the graph is ready.

DATA_DIR="${DATA_DIR:-/data}"
# Prefix derives from the PBF file name (input.osm.pbf -> input.osrm.*).
OUTPUT_PREFIX="${OUTPUT_PREFIX:-input}"
GRAPH="${DATA_DIR}/${OUTPUT_PREFIX}.osrm"
PROFILE="${PROFILE:-foot.lua}"

# Default: Northern Zone extract (covers Delhi) — small, fast dev bootstrap.
# Switch to the full India extract by setting:
#   OSM_PBF_URL=https://download.geofabrik.de/asia/india-latest.osm.pbf
OSM_PBF_URL="${OSM_PBF_URL:-https://download.geofabrik.de/asia/india/northern-zone-latest.osm.pbf}"
REQUESTED_PORT="${REQUESTED_PORT:-5000}"

mkdir -p "${DATA_DIR}"
PBF_FILE="${DATA_DIR}/input.osm.pbf"
MARKER="${DATA_DIR}/.osrm-ready"

echo "[osrm] data dir: ${DATA_DIR}"
echo "[osrm] pbf url:  ${OSM_PBF_URL}"

if [[ ! -f "${MARKER}" ]]; then
  if [[ ! -f "${PBF_FILE}" ]]; then
    echo "[osrm] downloading extract…"
    curl -fSL --retry 3 -o "${PBF_FILE}" "${OSM_PBF_URL}"
  fi

  echo "[osrm] extracting graph…"
  osrm-extract -p "/opt/${PROFILE}" "${PBF_FILE}" -t "${OSM_THREADS:-4}"

  echo "[osrm] partitioning…"
  osrm-partition "${GRAPH}" -t "${OSM_THREADS:-4}"

  echo "[osrm] customizing…"
  osrm-customize "${GRAPH}"

  touch "${MARKER}"
  echo "[osrm] graph ready."
else
  echo "[osrm] graph already built; skipping."
fi

echo "[osrm] starting osrm-routed on port ${REQUESTED_PORT}"
exec osrm-routed "${GRAPH}" --algorithm mld --port "${REQUESTED_PORT}"