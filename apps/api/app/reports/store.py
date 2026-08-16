from __future__ import annotations

import dataclasses
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

from sqlalchemy import Engine, text

from app.evidence.engine import Observation, compute_states
from app.evidence.states import VerificationState
from app.evidence.store import (
    USER_REPORT_RELIABILITY,
    EvidenceStore,
    PostgresEvidenceStore,
)

DEFAULT_REPORT_CONFIDENCE = 0.5


@dataclass(frozen=True)
class StoredReport:
    id: int
    segment_id: int
    category: str
    description_redacted: str | None
    client_hash: str
    image_encrypted: bytes | None
    reported_at: datetime
    verification_state: VerificationState
    confidence: float


class ReportStore(Protocol):
    """Writes anonymous reports and recomputes verification states.

    Privacy contract: only redacted descriptions and pseudonymous client
    hashes are stored; identity is never accepted.
    """

    def segment_exists(self, segment_id: int) -> bool: ...

    def insert_report(
        self,
        segment_id: int,
        category: str,
        description_redacted: str | None,
        client_hash: str,
        image_encrypted: bytes | None,
        reported_at: datetime | None = None,
    ) -> int: ...

    def recompute_segment(self, segment_id: int, now: datetime | None = None) -> int: ...

    def recompute_all(self, now: datetime | None = None) -> tuple[int, int]: ...

    def audit(self, action: str, admin_hash: str, details: dict[str, object]) -> None: ...

    def list_reports(self, limit: int = 50) -> list[StoredReport]: ...

    def set_verification(self, report_id: int, state: VerificationState) -> StoredReport | None: ...


class MemoryReportStore:
    def __init__(self, evidence: EvidenceStore) -> None:
        self._evidence = evidence
        self._reports: dict[int, StoredReport] = {}
        self._next_id = 1
        self._audit_log: list[dict[str, object]] = []

    def segment_exists(self, segment_id: int) -> bool:
        return self._evidence.segment_exists(segment_id)

    def insert_report(
        self,
        segment_id: int,
        category: str,
        description_redacted: str | None,
        client_hash: str,
        image_encrypted: bytes | None,
        reported_at: datetime | None = None,
    ) -> int:
        report_id = self._next_id
        self._next_id += 1
        self._reports[report_id] = StoredReport(
            id=report_id,
            segment_id=segment_id,
            category=category,
            description_redacted=description_redacted,
            client_hash=client_hash,
            image_encrypted=image_encrypted,
            reported_at=reported_at or datetime.now(UTC),
            verification_state=VerificationState.REPORTED,
            confidence=DEFAULT_REPORT_CONFIDENCE,
        )
        return report_id

    def _report_observations(self, segment_id: int) -> list[Observation]:
        return [
            Observation(
                id=rep.id,
                segment_id=rep.segment_id,
                source_type="user_report",
                observation_type=rep.category,
                observed_at=rep.reported_at,
                source_reliability=USER_REPORT_RELIABILITY,
                value={},
                confidence=rep.confidence,
                state=rep.verification_state,
                ingested_at=rep.reported_at,
                is_report=True,
            )
            for rep in self._reports.values()
            if rep.segment_id == segment_id
        ]

    def _update_state(self, report_id: int, state: VerificationState) -> None:
        rep = self._reports[report_id]
        self._reports[report_id] = dataclasses.replace(rep, verification_state=state)

    def recompute_segment(self, segment_id: int, now: datetime | None = None) -> int:
        items = [
            *self._evidence.observations_for_segment(segment_id),
            *self._report_observations(segment_id),
        ]
        finalized = compute_states(items, now)
        changed = 0
        for item, final in zip(items, finalized, strict=True):
            if final.state != item.state and item.is_report:
                assert item.id is not None
                self._update_state(item.id, final.state)
                changed += 1
        return changed

    def recompute_all(self, now: datetime | None = None) -> tuple[int, int]:
        segment_ids = sorted({r.segment_id for r in self._reports.values()})
        total = 0
        for segment_id in segment_ids:
            total += self.recompute_segment(segment_id, now)
        return total, len(segment_ids)

    def audit(self, action: str, admin_hash: str, details: dict[str, object]) -> None:
        self._audit_log.append(
            {
                "action": action,
                "admin_hash": admin_hash,
                "details": details,
                "performed_at": datetime.now(UTC).isoformat(),
            }
        )

    def list_reports(self, limit: int = 50) -> list[StoredReport]:
        return sorted(self._reports.values(), key=lambda r: r.reported_at, reverse=True)[:limit]

    def set_verification(self, report_id: int, state: VerificationState) -> StoredReport | None:
        if report_id not in self._reports:
            return None
        self._update_state(report_id, state)
        return self._reports[report_id]


class PostgresReportStore:
    def __init__(self, engine: Engine, evidence: PostgresEvidenceStore) -> None:
        self._engine = engine
        self._evidence = evidence

    def segment_exists(self, segment_id: int) -> bool:
        return self._evidence.segment_exists(segment_id)

    def insert_report(
        self,
        segment_id: int,
        category: str,
        description_redacted: str | None,
        client_hash: str,
        image_encrypted: bytes | None,
        reported_at: datetime | None = None,
    ) -> int:
        stmt = text(
            "INSERT INTO safety_reports (segment_id, category, description_redacted, "
            "client_hash, evidence_image_encrypted, reported_at, verification_state, confidence) "
            "VALUES (:segment_id, :category, :description_redacted, :client_hash, :image, "
            ":reported_at, 'REPORTED', :confidence) RETURNING id"
        )
        with self._engine.begin() as conn:
            row = conn.execute(
                stmt,
                {
                    "segment_id": segment_id,
                    "category": category,
                    "description_redacted": description_redacted,
                    "client_hash": client_hash,
                    "image": image_encrypted,
                    "reported_at": reported_at or datetime.now(UTC),
                    "confidence": DEFAULT_REPORT_CONFIDENCE,
                },
            ).one()
        return int(row.id)

    def _update_state(
        self, segment_id: int, item_id: int, state: VerificationState, is_report: bool
    ) -> None:
        table = "safety_reports" if is_report else "safety_observations"
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    f"UPDATE {table} SET verification_state = :state "
                    "WHERE id = :item_id AND segment_id = :segment_id"
                ),
                {"state": state, "item_id": item_id, "segment_id": segment_id},
            )

    def recompute_segment(self, segment_id: int, now: datetime | None = None) -> int:
        items = self._evidence.observations_for_segment(segment_id)
        finalized = compute_states(items, now)
        changed = 0
        for item, final in zip(items, finalized, strict=True):
            if final.state != item.state:
                assert item.id is not None
                self._update_state(segment_id, item.id, final.state, item.is_report)
                changed += 1
        return changed

    def recompute_all(self, now: datetime | None = None) -> tuple[int, int]:
        stmt = text(
            "SELECT segment_id FROM safety_observations UNION SELECT segment_id FROM safety_reports"
        )
        with self._engine.connect() as conn:
            segment_ids = [int(row.segment_id) for row in conn.execute(stmt).fetchall()]
        total = 0
        for segment_id in segment_ids:
            total += self.recompute_segment(segment_id, now)
        return total, len(segment_ids)

    def audit(self, action: str, admin_hash: str, details: dict[str, object]) -> None:
        stmt = text(
            "INSERT INTO admin_audit_log (action, admin_hash, details_json) "
            "VALUES (:action, :admin_hash, CAST(:details AS JSONB))"
        )
        with self._engine.begin() as conn:
            conn.execute(
                stmt,
                {
                    "action": action,
                    "admin_hash": admin_hash,
                    "details": json.dumps(details, default=str),
                },
            )

    def list_reports(self, limit: int = 50) -> list[StoredReport]:
        stmt = text(
            "SELECT id, segment_id, category, description_redacted, client_hash, "
            "evidence_image_encrypted, reported_at, verification_state, confidence "
            "FROM safety_reports ORDER BY reported_at DESC LIMIT :limit"
        )
        with self._engine.connect() as conn:
            rows = conn.execute(stmt, {"limit": limit}).fetchall()
        return [
            StoredReport(
                id=int(row.id),
                segment_id=int(row.segment_id),
                category=row.category,
                description_redacted=row.description_redacted,
                client_hash=row.client_hash,
                image_encrypted=row.evidence_image_encrypted,
                reported_at=row.reported_at,
                verification_state=VerificationState(row.verification_state),
                confidence=float(row.confidence),
            )
            for row in rows
        ]

    def set_verification(self, report_id: int, state: VerificationState) -> StoredReport | None:
        stmt = text(
            "UPDATE safety_reports SET verification_state = :state WHERE id = :report_id "
            "RETURNING id, segment_id, category, description_redacted, client_hash, "
            "evidence_image_encrypted, reported_at, verification_state, confidence"
        )
        with self._engine.begin() as conn:
            row = conn.execute(stmt, {"state": state, "report_id": report_id}).one_or_none()
        if row is None:
            return None
        return StoredReport(
            id=int(row.id),
            segment_id=int(row.segment_id),
            category=row.category,
            description_redacted=row.description_redacted,
            client_hash=row.client_hash,
            image_encrypted=row.evidence_image_encrypted,
            reported_at=row.reported_at,
            verification_state=VerificationState(row.verification_state),
            confidence=float(row.confidence),
        )
