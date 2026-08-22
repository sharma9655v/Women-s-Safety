# Deployment

## Local development (Windows, no Docker)

The API runs fully in-memory (no Postgres, Redis or OSRM) for tests and
most dev work. Prerequisites: Python 3.13, `uv`.

```powershell
# 1. From the repo root, move the .env aside when Postgres is not running.
#    pydantic-settings ignores EMPTY env vars, so DATABASE_URL='' does NOT
#    disable Postgres — the .env must not be present (or Postgres must run).
#    (Make sure to restore .env afterwards.)
Move-Item .env .env.off
uv run --directory apps/api pytest          # 259 tests
uv run --directory apps/api uvicorn app.main:app --port 8000
Move-Item .env.off .env                      # restore
```

Without OSRM running, `/api/routes` returns 503 and `/ready` reports the
OSRM check as failed. Everything else works with the in-memory store.

## Local development with the full stack

```powershell
docker compose -f infra/compose.yaml up -d
# postgis :5432, redis :6379, osrm :5000, api :8000
# api build context: apps/api (Dockerfile in infra/osrm for the router)
```

`infra/osrm/init-osrm.sh` + `infra/osrm/*.lua` build the OSRM graph from a
Geofabrik extract (default: northern-zone, covers Delhi; override
`OSM_PBF_URL` for India-wide).

## Production checklist

1. Set `APP_ENV=production`.
2. Set a real `ADMIN_KEY` (admin endpoints are 503 without one in
   production). Keep `ADMIN_DEV_KEY_ENABLED=0` (default) so the known
   dev key stays inert.
3. `DATABASE_URL` must point to PostGIS (16-3.4 or newer); `SEGMENTS_GEOJSON`
   only for dev/test. Never run production on the in-memory store.
4. `REDIS_URL` set for distributed rate limiting.
5. Reverse proxy must overwrite `X-Forwarded-For`; only then set
   `TRUST_PROXY=1` (default 0 — spoofable header otherwise).
6. Keep `ALLOW_LEGACY_CLIENT_ID=0`.
7. Set `REPORT_ENCRYPTION_KEY` (Fernet, urlsafe-base64, 32 bytes). Without
   it a random per-install key is persisted to `.report_encryption_key`
   (gitignored) — acceptable for a single instance, never for a fleet.
8. Configure `NOTIFY_CHANNEL` + `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID`
   for real guardian/SOS delivery; without them the honest status is
   `no_channel`.
9. Expose `/ready` to the orchestrator for rolling deploys and scrape
   `/metrics` with Prometheus.
10. CV: keep `CV_BACKEND=mock` until a validated checkpoint exists (see
    docs/model-integration.md); then `CV_BACKEND=real` +
    `CV_REAL_BACKEND_MODULE=app.cv.keras_impl`.

## Backups

`infra/backup.ps1` dumps Postgres to `infra/backups/` (gitignored).
Restore with `pg_restore`.

## Android app

Open `android/` in Android Studio (JDK 17+, SDK 34). The Gradle wrapper
is included (`gradlew.bat`). Override the API base URL with
`-PapiBaseUrl=https://...` or the `MAPFW_API_BASE_URL` env var; the
default is `http://10.0.2.2:8000` (emulator loopback). Release builds
minify with `proguard-rules.pro`; keep rules for kotlinx-serialization,
Retrofit, OkHttp and osmdroid.
