from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TypedDict

from sqlalchemy import Engine, text

from app.evidence.engine import Observation
from app.evidence.states import VerificationState

USER_REPORT_RELIABILITY = 0.6


class VerificationSummary(TypedDict):
    verified_count: int
    span_days: float | None


def _row_to_observation(row: object) -> Observation:
    return Observation(
        id=int(row.id),  # type: ignore[attr-defined]
        segment_id=int(row.segment_id),  # type: ignore[attr-defined]
        source_type=row.source_type,  # type: ignore[attr-defined]
        observation_type=row.observation_type,  # type: ignore[attr-defined]
        observed_at=row.observed_at,  # type: ignore[attr-defined]
        source_reliability=float(row.source_reliability),  # type: ignore[attr-defined]
        value=dict(row.value_json or {}),  # type: ignore[attr-defined]
        confidence=float(row.confidence),  # type: ignore[attr-defined]
        state=VerificationState(row.verification_state),  # type: ignore[attr-defined]
        ingested_at=row.ingested_at,  # type: ignore[attr-defined]
        expires_at=row.expires_at,  # type: ignore[attr-defined]
    )


def _report_to_observation(row: object) -> Observation:
    return Observation(
        id=int(row.id),  # type: ignore[attr-defined]
        segment_id=int(row.segment_id),  # type: ignore[attr-defined]
        source_type="user_report",
        observation_type=row.category,  # type: ignore[attr-defined]
        observed_at=row.reported_at,  # type: ignore[attr-defined]
        source_reliability=USER_REPORT_RELIABILITY,
        value={},
        confidence=float(row.confidence),  # type: ignore[attr-defined]
        state=VerificationState(row.verification_state),  # type: ignore[attr-defined]
        ingested_at=row.created_at,  # type: ignore[attr-defined]
        is_report=True,
    )


class EvidenceStore:
    """Interface for evidence sources. Never exposes reporter identity:
    stores return observations, not raw report content."""

    def segment_exists(self, segment_id: int) -> bool:
        raise NotImplementedError

    def observations_for_segment(self, segment_id: int) -> Sequence[Observation]:
        raise NotImplementedError

    def observations_for_segments(
        self, segment_ids: Sequence[int]
    ) -> Mapping[int, Sequence[Observation]]:
        raise NotImplementedError

    def verification_summary(self) -> VerificationSummary:
        """Count of VERIFIED observations and the span of their dates.

        Used by the models endpoint to report the ML gate status without
        coupling the API to the ml/ module (thresholds live in ml/ml/gate.py).
        """
        raise NotImplementedError


class MemoryEvidenceStore(EvidenceStore):
    def __init__(
        self,
        observations: Sequence[Observation] = (),
        segment_ids: Sequence[int] = (),
    ) -> None:
        self._observations = list(observations)
        self._segment_ids = set(segment_ids) | {obs.segment_id for obs in self._observations}

    def segment_exists(self, segment_id: int) -> bool:
        return segment_id in self._segment_ids

    def observations_for_segment(self, segment_id: int) -> Sequence[Observation]:
        return [obs for obs in self._observations if obs.segment_id == segment_id]

    def observations_for_segments(
        self, segment_ids: Sequence[int]
    ) -> Mapping[int, Sequence[Observation]]:
        wanted = set(segment_ids)
        grouped: dict[int, list[Observation]] = {seg_id: [] for seg_id in segment_ids}
        for obs in self._observations:
            if obs.segment_id in wanted:
                grouped[obs.segment_id].append(obs)
        return grouped

    def verification_summary(self) -> VerificationSummary:
        verified = [obs for obs in self._observations if obs.state == VerificationState.VERIFIED]
        dates = [obs.observed_at for obs in verified]
        if not dates:
            return {"verified_count": 0, "span_days": None}
        span_days = (max(dates) - min(dates)).total_seconds() / 86400
        return {"verified_count": len(dates), "span_days": span_days}


class PostgresEvidenceStore(EvidenceStore):
    """Reads safety_observations + safety_reports from PostGIS via SQLAlchemy.
    Reports are surfaced as observations with source_type="user_report" and
    empty values: descriptions and identities never leave the database."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def segment_exists(self, segment_id: int) -> bool:
        with self._engine.connect() as conn:
            found = conn.execute(
                text("SELECT 1 FROM road_segments WHERE id = :segment_id"),
                {"segment_id": segment_id},
            ).scalar_one_or_none()
        return found is not None

    def observations_for_segment(self, segment_id: int) -> Sequence[Observation]:
        stmt = text(
            "SELECT id, segment_id, source_type, observation_type, value_json, "
            "observed_at, ingested_at, source_reliability, confidence, "
            "verification_state, expires_at "
            "FROM safety_observations WHERE segment_id = :segment_id"
        )
        report_stmt = text(
            "SELECT id, segment_id, category, reported_at, verification_state, "
            "confidence, created_at "
            "FROM safety_reports WHERE segment_id = :segment_id"
        )
        with self._engine.connect() as conn:
            obs = [
                _row_to_observation(row)
                for row in conn.execute(stmt, {"segment_id": segment_id}).fetchall()
            ]
            reports = [
                _report_to_observation(row)
                for row in conn.execute(report_stmt, {"segment_id": segment_id}).fetchall()
            ]
        return [*obs, *reports]

    def observations_for_segments(
        self, segment_ids: Sequence[int]
    ) -> Mapping[int, Sequence[Observation]]:
        if not segment_ids:
            return {}
        obs_stmt = text(
            "SELECT id, segment_id, source_type, observation_type, value_json, "
            "observed_at, ingested_at, source_reliability, confidence, "
            "verification_state, expires_at "
            "FROM safety_observations WHERE segment_id = ANY(:segment_ids)"
        )
        report_stmt = text(
            "SELECT id, segment_id, category, reported_at, verification_state, "
            "confidence, created_at "
            "FROM safety_reports WHERE segment_id = ANY(:segment_ids)"
        )
        params = {"segment_ids": list(dict.fromkeys(segment_ids))}
        with self._engine.connect() as conn:
            obs_rows = conn.execute(obs_stmt, params).fetchall()
            report_rows = conn.execute(report_stmt, params).fetchall()
        grouped: dict[int, list[Observation]] = {}
        for row in obs_rows:
            grouped.setdefault(int(row.segment_id), []).append(_row_to_observation(row))
        for row in report_rows:
            grouped.setdefault(int(row.segment_id), []).append(_report_to_observation(row))
        return grouped

    def verification_summary(self) -> VerificationSummary:
        stmt = text(
            "SELECT MIN(observed_at) AS min_ts, MAX(observed_at) AS max_ts, "
            "COUNT(*) AS cnt FROM safety_observations WHERE verification_state = 'VERIFIED'"
        )
        report_stmt = text(
            "SELECT COUNT(*) AS cnt FROM safety_reports WHERE verification_state = 'VERIFIED'"
        )
        with self._engine.connect() as conn:
            row = conn.execute(stmt).one()
            verified = int(row.cnt)
            min_ts, max_ts = row.min_ts, row.max_ts
            verified += int(conn.execute(report_stmt).scalar_one())
        if min_ts is None:
            return {"verified_count": 0, "span_days": None}
        span_days = (max_ts - min_ts).total_seconds() / 86400
        return {"verified_count": verified, "span_days": span_days}
