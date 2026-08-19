from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.api.alerts import router as alerts_router
from app.api.auth import router as auth_router
from app.api.community import router as community_router
from app.api.contacts import router as contacts_router
from app.api.cv import router as cv_router
from app.api.discreet_mode import router as discreet_mode_router
from app.api.emergency import router as emergency_router
from app.api.evidence import router as evidence_router
from app.api.fake_call import router as fake_call_router
from app.api.geocode import router as geocode_router
from app.api.guardian import router as guardian_router
from app.api.models import router as models_router
from app.api.notifications import router as notifications_router
from app.api.overlays import router as overlays_router
from app.api.preferences import router as preferences_router
from app.api.privacy import router as privacy_router
from app.api.reports import router as reports_router
from app.api.routes import router as api_router
from app.api.voice_guidance import router as voice_guidance_router
from app.config import settings
from app.metrics import get_metrics, record_request

app = FastAPI(
    title="Map for Women API",
    version="0.1.0",
    description="Safety-aware routing. This API estimates risk; it never guarantees safety.",
)

logger = logging.getLogger("app.access")


@app.middleware("http")
async def request_id_and_access_log(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Assign an X-Request-Id (client-supplied ids are honored) and log one
    structured line per request: request_id, method, path, status, duration_ms.

    No PII is logged: the query string and body are never included.
    """
    request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception(
            "request failed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
            },
        )
        raise
    duration_ms = round((time.perf_counter() - start) * 1000, 1)
    response.headers["X-Request-Id"] = request_id
    logger.info(
        "request completed",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "duration_ms": duration_ms,
        },
    )
    record_request(
        path=request.url.path,
        method=request.method,
        status_code=response.status_code,
        duration_s=duration_ms / 1000.0,
    )
    return response


def cors_origins_list(raw: str) -> list[str]:
    """Comma-separated CORS origins from settings (whitespace-tolerant)."""
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def _cors_list(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]


app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins_list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=_cors_list(settings.cors_methods),
    allow_headers=_cors_list(settings.cors_headers),
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "env": settings.app_env}


@app.get("/ready")
def ready(request: Request) -> Response:
    """Readiness probe. Reports each component independently and returns 503
    when a required component is unavailable (liveness stays at /health).

    Components: database (only when DATABASE_URL is configured), OSRM
    routing engine, CV inference backend. Never blocks longer than the
    per-component timeout.
    """
    import httpx
    from fastapi.responses import JSONResponse

    components: dict[str, str] = {}

    if settings.database_url:
        try:
            from app.db import make_engine

            engine = make_engine()
            with engine.connect() as conn:
                conn.execute(__import__("sqlalchemy").text("SELECT 1"))
            components["database"] = "ok"
        except Exception as exc:
            logger.warning("readiness: database check failed: %s", exc)
            components["database"] = f"error: {exc}"

    try:
        with httpx.Client(timeout=2.0) as client:
            probe_url = (
                f"{settings.osrm_base_url.rstrip('/')}"
                "/route/v1/walking/77.0,28.6;77.01,28.61?overview=false"
            )
            response = client.get(probe_url)
            components["osrm"] = (
                "ok" if response.status_code < 500 else f"error: http {response.status_code}"
            )
    except Exception as exc:
        components["osrm"] = f"error: {exc}"

    try:
        from app.cv.registry import get_cv_service

        service = get_cv_service()
        components["cv"] = "ok" if service.is_loaded() else "error: not loaded"
    except Exception as exc:
        components["cv"] = f"error: {exc}"

    ready_ok = all(value == "ok" for value in components.values())
    status_code = 200 if ready_ok else 503
    return JSONResponse(
        status_code=status_code,
        content={"status": "ready" if ready_ok else "degraded", "components": components},
    )


@app.get("/metrics", include_in_schema=False)
def metrics() -> Response:
    """Prometheus text-format metrics (request counts, latency histograms,
    error counters, CV/ingestion telemetry, model gauges). No PII."""
    from fastapi.responses import PlainTextResponse

    return PlainTextResponse(get_metrics().render(), media_type="text/plain; version=0.0.4")


app.include_router(api_router)
app.include_router(community_router)
app.include_router(contacts_router)
app.include_router(cv_router)
app.include_router(discreet_mode_router)
app.include_router(emergency_router)
app.include_router(evidence_router)
app.include_router(fake_call_router)
app.include_router(geocode_router)
app.include_router(guardian_router)
app.include_router(models_router)
app.include_router(notifications_router)
app.include_router(overlays_router)
app.include_router(preferences_router)
app.include_router(privacy_router)
app.include_router(reports_router)
app.include_router(alerts_router)
app.include_router(auth_router)
app.include_router(voice_guidance_router)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> Response:
    """Last-resort handler: log server-side, return a sanitized 500 that never
    leaks internals (stack traces, SQL, config)."""

    from fastapi.responses import JSONResponse

    logger.exception(
        "unhandled exception",
        extra={"request_id": request.headers.get("x-request-id", ""), "path": request.url.path},
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )
