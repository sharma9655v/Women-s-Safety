from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from datetime import datetime

from app.evidence.freshness import expires_at as type_expires_at
from app.evidence.freshness import freshness, utc_now
from app.evidence.states import OBSERVATION_TYPES, VerificationState

# --- evidence_hash ---------------------------------------------------------
# Canonical identity of an observation: same inputs -> same hash, so the
# database can dedupe (unique constraint) and history rows stay verifiable.
# Never includes reporter identity.


def evidence_hash(
    segment_id: int, source_type: str, observation_type: str, value: object, observed_at: datetime
) -> str:
    payload = {
        "segment_id": segment_id,
        "source_type": source_type,
        "observation_type": observation_type,
        "value": value,
        "observed_at": observed_at.isoformat(),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# --- observation -----------------------------------------------------------


@dataclass(frozen=True)
class Observation:
    segment_id: int
    source_type: str
    observation_type: str
    observed_at: datetime
    source_reliability: float
    value: dict[str, object] = field(default_factory=dict)
    confidence: float = 0.5
    state: VerificationState = VerificationState.REPORTED
    ingested_at: datetime | None = None
    expires_at: datetime | None = None
    id: int | None = None
    is_report: bool = False

    @property
    def active(self) -> bool:
        return self.state not in (VerificationState.EXPIRED, VerificationState.REJECTED)


# --- conflict detection ----------------------------------------------------
# Per-type boolean/nominal keys whose disagreeing values signal CONFLICTING
# evidence. Incident types (harassment, ...) are events: extra events
# corroborate, they never conflict.

CONFLICT_KEYS: dict[str, tuple[str, ...]] = {
    "streetlight_not_working": ("working",),
    "poor_lighting": ("poor",),
    "blocked_sidewalk": ("blocked",),
}


def _conflicts(a: Observation, b: Observation) -> bool:
    if a.observation_type != b.observation_type:
        return False
    keys = CONFLICT_KEYS.get(a.observation_type, ())
    if not keys:
        return False
    return any(key in a.value and key in b.value and a.value[key] != b.value[key] for key in keys)


# --- state machine ---------------------------------------------------------


def compute_states(
    items: Sequence[Observation],
    now: datetime | None = None,
) -> list[Observation]:
    """Deterministic state transitions. Returns NEW observations; inputs are
    never mutated (old evidence is never overwritten).

    Rules per observation:
      - REJECTED stays REJECTED.
      - Past expires_at -> EXPIRED.
      - VERIFIED stays VERIFIED.
      - Otherwise, among active same-type siblings on the same segment:
          * any conflicting pair -> CONFLICTING
          * >= 2 distinct source types, or >= 3 items (majority proxy for
            independence, since reporter identity is never stored) ->
            CORROBORATED
          * else REPORTED
    """
    by_segment_type: dict[tuple[int, str], list[Observation]] = {}
    for item in items:
        by_segment_type.setdefault((item.segment_id, item.observation_type), []).append(item)

    if now is None:
        now = utc_now()

    finalized: list[Observation] = []
    for item in items:
        state = item.state
        if state not in (VerificationState.REJECTED, VerificationState.VERIFIED):
            effective_expiry = item.expires_at or type_expires_at(
                item.observed_at, item.observation_type
            )
            if now > effective_expiry:
                state = VerificationState.EXPIRED
            else:
                siblings = [
                    other
                    for other in by_segment_type[(item.segment_id, item.observation_type)]
                    if other.active and other is not item
                ]
                if any(_conflicts(item, other) for other in siblings):
                    state = VerificationState.CONFLICTING
                elif (
                    len({item.source_type, *(s.source_type for s in siblings)}) >= 2
                    or len(siblings) + 1 >= 3
                ):
                    state = VerificationState.CORROBORATED
                else:
                    state = VerificationState.REPORTED
        finalized.append(replace(item, state=state) if state != item.state else item)
    return finalized


# --- aggregation -----------------------------------------------------------


@dataclass(frozen=True)
class TypeSummary:
    observation_type: str
    count: int
    score: float
    freshness: float
    confidence: float
    conflicts: bool
    source_counts: dict[str, int]
    state_counts: dict[str, int]
    distinct_source_types: int = 0
    corroborated: bool = False


@dataclass(frozen=True)
class SegmentEvidence:
    segment_id: int
    total_observations: int
    overall_freshness: float
    overall_confidence: float
    conflicts: list[str]
    by_type: dict[str, TypeSummary]
    model_version: str = "evidence-baseline-v1"


_CONFIDENCE_K = 2.0
_CONFIDENCE_CAP = 0.95
_CONFLICT_PENALTY = 0.5


def _type_confidence(score: float, conflicting: bool) -> float:
    confidence = 1.0 - math.exp(-_CONFIDENCE_K * score)
    confidence = min(_CONFIDENCE_CAP, confidence)
    if conflicting:
        confidence *= _CONFLICT_PENALTY
    return confidence


def aggregate(
    segment_id: int,
    items: Sequence[Observation],
    now: datetime | None = None,
) -> SegmentEvidence:
    """Recency-weighted per-type aggregation. Active = not expired/rejected.
    Expired/rejected items appear in state_counts but never in counts/score.
    """
    now = now or utc_now()
    items = compute_states(items, now)
    active = [item for item in items if item.active]

    by_type: dict[str, list[Observation]] = {}
    for item in active:
        by_type.setdefault(item.observation_type, []).append(item)

    summaries: dict[str, TypeSummary] = {}
    for obs_type in OBSERVATION_TYPES:
        type_items = by_type.get(obs_type, [])
        if not type_items:
            continue
        score = sum(
            freshness(item.observed_at, now, obs_type) * item.source_reliability
            for item in type_items
        )
        conflicting = any(
            _conflicts(a, b) for i, a in enumerate(type_items) for b in type_items[i + 1 :]
        )
        source_counts = dict(Counter(item.source_type for item in type_items))
        distinct_sources = len(source_counts)
        summaries[obs_type] = TypeSummary(
            observation_type=obs_type,
            count=len(type_items),
            score=score,
            freshness=max(freshness(item.observed_at, now, obs_type) for item in type_items),
            confidence=_type_confidence(score, conflicting),
            conflicts=conflicting,
            source_counts=source_counts,
            state_counts=dict(
                Counter(item.state.value for item in items if item.observation_type == obs_type)
            ),
            distinct_source_types=distinct_sources,
            # Same independence proxy as compute_states: >= 2 distinct source
            # types OR >= 3 items.
            corroborated=distinct_sources >= 2 or len(type_items) >= 3,
        )

    confidences = [s.confidence for s in summaries.values()]
    return SegmentEvidence(
        segment_id=segment_id,
        total_observations=len(active),
        overall_freshness=max((s.freshness for s in summaries.values()), default=0.0),
        overall_confidence=(sum(confidences) / len(confidences)) if confidences else 0.0,
        conflicts=[obs_type for obs_type, s in summaries.items() if s.conflicts],
        by_type=summaries,
    )
