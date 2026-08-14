from __future__ import annotations

from functools import lru_cache

from sqlalchemy import create_engine

from app.config import settings
from app.evidence.registry import get_evidence_store
from app.evidence.store import PostgresEvidenceStore
from app.reports.store import MemoryReportStore, PostgresReportStore, ReportStore


@lru_cache(maxsize=1)
def get_reports_store() -> ReportStore:
    """Priority: PostGIS when reachable, otherwise an in-memory store (tests)."""
    evidence = get_evidence_store()
    if isinstance(evidence, PostgresEvidenceStore) and settings.database_url:
        try:
            engine = create_engine(settings.database_url)
            with engine.connect():
                pass
            return PostgresReportStore(engine, evidence)
        except Exception:
            pass
    return MemoryReportStore(evidence)
