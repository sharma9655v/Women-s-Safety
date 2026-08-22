from __future__ import annotations

import json
from datetime import datetime
from functools import lru_cache

from app.config import settings
from app.db import make_engine
from app.evidence.engine import Observation
from app.evidence.states import VerificationState
from app.evidence.store import EvidenceStore, MemoryEvidenceStore, PostgresEvidenceStore


def _load_seed_observations(path: str) -> list[Observation]:
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    observations: list[Observation] = []
    for item in raw.get("observations", []):
        observations.append(
            Observation(
                segment_id=int(item["segment_id"]),
                source_type=item.get("source_type", "demo_seed"),
                observation_type=item["observation_type"],
                observed_at=datetime.fromisoformat(item["observed_at"]),
                source_reliability=0.55,
                value={"working": item["working"]} if item.get("working") is not None else {},
                confidence=0.5,
                state=VerificationState(item.get("verification_state", "REPORTED")),
                ingested_at=None,
                expires_at=None,
            )
        )
    return observations


@lru_cache(maxsize=1)
def get_evidence_store() -> EvidenceStore:
    """Return the configured evidence store.

    Priority: PostGIS when DATABASE_URL is reachable, otherwise the seeded
    demo snapshot (EVIDENCE_SEED_JSON) so the offline demo still scores
    routes, otherwise an empty memory store (dev/test path).
    """
    if settings.database_url and settings.database_url != "":
        try:
            engine = make_engine()
            with engine.connect():
                pass
        except Exception:
            engine = None
        if engine is not None:
            return PostgresEvidenceStore(engine)
    if settings.evidence_seed_json:
        try:
            return MemoryEvidenceStore(_load_seed_observations(settings.evidence_seed_json))
        except OSError:
            pass
    return MemoryEvidenceStore()
