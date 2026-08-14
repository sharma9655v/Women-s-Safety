from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.evidence import router as evidence_router
from app.api.models import router as models_router
from app.api.overlays import router as overlays_router
from app.api.reports import router as reports_router
from app.api.routes import router as api_router
from app.config import settings

app = FastAPI(
    title="Map for Women API",
    version="0.1.0",
    description="Safety-aware routing. This API estimates risk; it never guarantees safety.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "env": settings.app_env}


app.include_router(api_router)
app.include_router(evidence_router)
app.include_router(overlays_router)
app.include_router(reports_router)
app.include_router(models_router)
