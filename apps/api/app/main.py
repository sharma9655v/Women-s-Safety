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


app.include_router(api_router)
app.include_router(community_router)
app.include_router(contacts_router)
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
