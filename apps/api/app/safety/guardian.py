"""Guardian journeys: a trusted contact watches a planned journey.

Rules (mirrored by the API layer):
  - One active guardian session per client at a time.
  - The owner checks in periodically; the deadline is the expected arrival
    (if set) or the last check-in, plus a grace period.
  - Missed check-ins escalate in stages: 1 = checkin_missed, 2 =
    checkin_escalated (status ESCALATED). Notifications are emitted exactly
    once per stage (notified_stage watermark).
  - Route deviation is detected only against the geometry the owner provided
    at start — never from invented data.
  - Sessions are readable only by their owning client_id.
"""

from __future__ import annotations

import json
import logging
import math
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from typing import Any

from sqlalchemy import Engine, Row, text

from app.db import make_engine

from app.config import settings

logger = logging.getLogger(__name__)

PolylinePoint = tuple[float, float]  # (lon, lat)


def _now() -> datetime:
    return datetime.now(UTC)


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in metres between two coordinates."""
    r = 6371000.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _point_segment_m(
    lat: float, lon: float, lat_a: float, lon_a: float, lat_b: float, lon_b: float
) -> float:
    """Haversine distance from a point to a great-circle segment (metres)."""
    # Project to a local equirectangular plane: x = lon * cos(lat), y = lat.
    cos_lat = math.cos(math.radians((lat_a + lat_b + lat) / 3))
    x, y = lon * cos_lat, lat
    xa, ya = lon_a * cos_lat, lat_a
    xb, yb = lon_b * cos_lat, lat_b
    dx, dy = xb - xa, yb - ya
    length_sq = dx * dx + dy * dy
    if length_sq == 0:
        proj = 0.0
    else:
        t = ((x - xa) * dx + (y - ya) * dy) / length_sq
        proj = max(0.0, min(1.0, t))
    # Closest point on the segment back to (lon, lat) coordinates.
    px = xa + proj * dx
    py = ya + proj * dy
    return _haversine_m(lat, lon, py, px / cos_lat if cos_lat else px)


def deviation_m(lat: float, lon: float, polyline: Sequence[PolylinePoint]) -> float:
    """Minimum distance (metres) from a point to a polyline of (lon, lat)."""
    if not polyline:
        return 0.0
    if len(polyline) == 1:
        lon1, lat1 = polyline[0]
        return _haversine_m(lat, lon, lat1, lon1)
    best = math.inf
    for (lon_a, lat_a), (lon_b, lat_b) in zip(polyline, polyline[1:], strict=False):
        best = min(best, _point_segment_m(lat, lon, lat_a, lon_a, lat_b, lon_b))
    return best


@dataclass(frozen=True)
class GuardianSession:
    id: str
    client_id: str
    status: str  # ACTIVE | COMPLETED | CANCELLED | ESCALATED
    started_at: datetime
    ended_at: datetime | None
    end_reason: str | None
    guardian_contact_ids: list[int]
    expected_arrival_at: datetime | None
    planned_geometry: list[PolylinePoint] | None
    checkin_grace_s: int
    last_checkin_at: datetime | None
    latitude: float | None
    longitude: float | None
    last_known_at: datetime | None
    deviation_detected: bool
    first_deviation_at: datetime | None
    escalation_stage: int  # computed: 0 ok, 1 missed, 2 escalated
    notified_stage: int  # watermark of already-emitted notifications

    @property
    def checkin_deadline(self) -> datetime:
        base = self.expected_arrival_at or self.last_checkin_at or self.started_at
        return base + timedelta(seconds=self.checkin_grace_s)


def _to_guardian(row: Row[Any]) -> GuardianSession:
    return GuardianSession(
        id=str(row[0]),
        client_id=str(row[1]),
        status=str(row[2]),
        started_at=row[3],
        ended_at=row[4],
        end_reason=row[5],
        guardian_contact_ids=[int(i) for i in (row[6] or [])],
        expected_arrival_at=row[7],
        planned_geometry=[tuple(p) for p in (row[8] or [])] if row[8] else None,
        checkin_grace_s=int(row[9]),
        last_checkin_at=row[10],
        latitude=float(row[11]) if row[11] is not None else None,
        longitude=float(row[12]) if row[12] is not None else None,
        last_known_at=row[13],
        deviation_detected=bool(row[14]),
        first_deviation_at=row[15],
        escalation_stage=int(row[16]),
        notified_stage=int(row[17]),
    )


class GuardianStore:
    def create_guardian(
        self,
        client_id_value: str,
        *,
        guardian_contact_ids: Sequence[int],
        expected_arrival_at: datetime | None,
        planned_geometry: Sequence[PolylinePoint] | None,
        checkin_grace_s: int,
    ) -> GuardianSession:
        raise NotImplementedError

    def active_guardian(
        self, client_id_value: str
    ) -> tuple[GuardianSession | None, list[tuple[str, dict[str, object]]]]:
        raise NotImplementedError

    def get_guardian(
        self, client_id_value: str, session_id: str
    ) -> tuple[GuardianSession | None, list[tuple[str, dict[str, object]]]]:
        raise NotImplementedError

    def update_guardian_location(
        self,
        client_id_value: str,
        session_id: str,
        latitude: float,
        longitude: float,
    ) -> tuple[GuardianSession | None, list[tuple[str, dict[str, object]]]]:
        raise NotImplementedError

    def checkin(
        self, client_id_value: str, session_id: str
    ) -> tuple[GuardianSession | None, list[tuple[str, dict[str, object]]]]:
        raise NotImplementedError

    def end_guardian(
        self, client_id_value: str, session_id: str, reason: str
    ) -> tuple[GuardianSession | None, list[tuple[str, dict[str, object]]]]:
        raise NotImplementedError

    @staticmethod
    def _evaluate(
        session: GuardianSession,
        *,
        now: datetime,
        store: GuardianStore,
        persisted: bool = False,
    ) -> tuple[GuardianSession, list[tuple[str, dict[str, object]]]]:
        """Compute escalation stage and emit exactly-once notifications."""
        events: list[tuple[str, dict[str, object]]] = []
        if session.status not in ("ACTIVE", "ESCALATED"):
            return session, events
        stage = 0
        if now >= session.checkin_deadline:
            stage = 1
        if now >= session.checkin_deadline + timedelta(
            seconds=settings.guardian_escalation_delay_s
        ):
            stage = 2
        if stage == session.escalation_stage:
            return session, events
        for s in range(session.notified_stage + 1, stage + 1):
            if s == 1:
                events.append(("checkin_missed", {"session_id": session.id}))
            elif s == 2:
                events.append(
                    (
                        "checkin_escalated",
                        {
                            "session_id": session.id,
                            "missed_since": session.checkin_deadline.isoformat(),
                        },
                    )
                )
        updated = GuardianSession(
            id=session.id,
            client_id=session.client_id,
            status="ESCALATED" if stage >= 2 else "ACTIVE",
            started_at=session.started_at,
            ended_at=session.ended_at,
            end_reason=session.end_reason,
            guardian_contact_ids=session.guardian_contact_ids,
            expected_arrival_at=session.expected_arrival_at,
            planned_geometry=session.planned_geometry,
            checkin_grace_s=session.checkin_grace_s,
            last_checkin_at=session.last_checkin_at,
            latitude=session.latitude,
            longitude=session.longitude,
            last_known_at=session.last_known_at,
            deviation_detected=session.deviation_detected,
            first_deviation_at=session.first_deviation_at,
            escalation_stage=stage,
            notified_stage=stage,
        )
        if persisted:
            store._persist_guardian(updated)
        return updated, events

    def _persist_guardian(self, session: GuardianSession) -> None:
        raise NotImplementedError


class MemoryGuardianStore(GuardianStore):
    def __init__(self) -> None:
        self._guardian: dict[str, GuardianSession] = {}

    def create_guardian(
        self,
        client_id_value: str,
        *,
        guardian_contact_ids: Sequence[int],
        expected_arrival_at: datetime | None,
        planned_geometry: Sequence[PolylinePoint] | None,
        checkin_grace_s: int,
    ) -> GuardianSession:
        session = GuardianSession(
            id=str(uuid.uuid4()),
            client_id=client_id_value,
            status="ACTIVE",
            started_at=_now(),
            ended_at=None,
            end_reason=None,
            guardian_contact_ids=list(guardian_contact_ids),
            expected_arrival_at=expected_arrival_at,
            planned_geometry=list(planned_geometry) if planned_geometry else None,
            checkin_grace_s=checkin_grace_s,
            last_checkin_at=None,
            latitude=None,
            longitude=None,
            last_known_at=None,
            deviation_detected=False,
            first_deviation_at=None,
            escalation_stage=0,
            notified_stage=0,
        )
        self._guardian[session.id] = session
        return session

    def active_guardian(
        self, client_id_value: str
    ) -> tuple[GuardianSession | None, list[tuple[str, dict[str, object]]]]:
        for session in self._guardian.values():
            if session.client_id == client_id_value and session.status in ("ACTIVE", "ESCALATED"):
                return GuardianStore._evaluate(session, now=_now(), store=self, persisted=True)
        return None, []

    def get_guardian(
        self, client_id_value: str, session_id: str
    ) -> tuple[GuardianSession | None, list[tuple[str, dict[str, object]]]]:
        session = self._guardian.get(session_id)
        if session is None or session.client_id != client_id_value:
            return None, []
        return GuardianStore._evaluate(session, now=_now(), store=self, persisted=True)

    def update_guardian_location(
        self,
        client_id_value: str,
        session_id: str,
        latitude: float,
        longitude: float,
    ) -> tuple[GuardianSession | None, list[tuple[str, dict[str, object]]]]:
        session = self._guardian.get(session_id)
        if session is None or session.client_id != client_id_value:
            return None, []
        if session.status not in ("ACTIVE", "ESCALATED"):
            return None, []
        events: list[tuple[str, dict[str, object]]] = []
        now = _now()
        deviation = (
            deviation_m(latitude, longitude, session.planned_geometry)
            if session.planned_geometry
            else 0.0
        )
        detected = session.deviation_detected or (
            deviation > settings.guardian_deviation_threshold_m
        )
        if detected and not session.deviation_detected:
            events.append(
                ("route_changed", {"session_id": session.id, "deviation_m": round(deviation, 1)})
            )
        updated = GuardianSession(
            id=session.id,
            client_id=session.client_id,
            status=session.status,
            started_at=session.started_at,
            ended_at=session.ended_at,
            end_reason=session.end_reason,
            guardian_contact_ids=session.guardian_contact_ids,
            expected_arrival_at=session.expected_arrival_at,
            planned_geometry=session.planned_geometry,
            checkin_grace_s=session.checkin_grace_s,
            last_checkin_at=session.last_checkin_at,
            latitude=latitude,
            longitude=longitude,
            last_known_at=now,
            deviation_detected=detected,
            first_deviation_at=(
                now if detected and not session.deviation_detected else session.first_deviation_at
            ),
            escalation_stage=session.escalation_stage,
            notified_stage=session.notified_stage,
        )
        self._guardian[session_id] = updated
        return updated, events

    def checkin(
        self, client_id_value: str, session_id: str
    ) -> tuple[GuardianSession | None, list[tuple[str, dict[str, object]]]]:
        session = self._guardian.get(session_id)
        if session is None or session.client_id != client_id_value:
            return None, []
        if session.status not in ("ACTIVE", "ESCALATED"):
            return None, []
        now = _now()
        updated = GuardianSession(
            id=session.id,
            client_id=session.client_id,
            status="ACTIVE",
            started_at=session.started_at,
            ended_at=session.ended_at,
            end_reason=session.end_reason,
            guardian_contact_ids=session.guardian_contact_ids,
            expected_arrival_at=None,  # superseded by the fresh check-in
            planned_geometry=session.planned_geometry,
            checkin_grace_s=session.checkin_grace_s,
            last_checkin_at=now,
            latitude=session.latitude,
            longitude=session.longitude,
            last_known_at=session.last_known_at,
            deviation_detected=session.deviation_detected,
            first_deviation_at=session.first_deviation_at,
            escalation_stage=0,
            notified_stage=0,
        )
        self._guardian[session_id] = updated
        return updated, []

    def end_guardian(
        self, client_id_value: str, session_id: str, reason: str
    ) -> tuple[GuardianSession | None, list[tuple[str, dict[str, object]]]]:
        session = self._guardian.get(session_id)
        if session is None or session.client_id != client_id_value:
            return None, []
        if session.status not in ("ACTIVE", "ESCALATED"):
            return None, []
        status = "COMPLETED" if reason == "arrived" else "CANCELLED"
        updated = GuardianSession(
            id=session.id,
            client_id=session.client_id,
            status=status,
            started_at=session.started_at,
            ended_at=_now(),
            end_reason=reason,
            guardian_contact_ids=session.guardian_contact_ids,
            expected_arrival_at=session.expected_arrival_at,
            planned_geometry=session.planned_geometry,
            checkin_grace_s=session.checkin_grace_s,
            last_checkin_at=session.last_checkin_at,
            latitude=session.latitude,
            longitude=session.longitude,
            last_known_at=session.last_known_at,
            deviation_detected=session.deviation_detected,
            first_deviation_at=session.first_deviation_at,
            escalation_stage=session.escalation_stage,
            notified_stage=session.notified_stage,
        )
        self._guardian[session_id] = updated
        return updated, []

    def _persist_guardian(self, session: GuardianSession) -> None:
        self._guardian[session.id] = session


_GUARDIAN_COLUMNS = (
    "id, client_id, status, started_at, ended_at, end_reason, guardian_contact_ids, "
    "expected_arrival_at, planned_geometry, checkin_grace_s, last_checkin_at, latitude, "
    "longitude, last_known_at, deviation_detected, first_deviation_at, escalation_stage, "
    "notified_stage"
)


class PostgresGuardianStore(GuardianStore):
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def create_guardian(
        self,
        client_id_value: str,
        *,
        guardian_contact_ids: Sequence[int],
        expected_arrival_at: datetime | None,
        planned_geometry: Sequence[PolylinePoint] | None,
        checkin_grace_s: int,
    ) -> GuardianSession:
        with self._engine.begin() as conn:
            row = conn.execute(
                text(
                    f"INSERT INTO guardian_sessions (client_id, guardian_contact_ids, "
                    f"expected_arrival_at, planned_geometry, checkin_grace_s) "
                    f"VALUES (:cid, :ids, :arrival, :geometry, :grace) "
                    f"RETURNING {_GUARDIAN_COLUMNS}"
                ),
                {
                    "cid": client_id_value,
                    "ids": json.dumps(list(guardian_contact_ids)),
                    "arrival": expected_arrival_at,
                    "geometry": (
                        json.dumps([[lon, lat] for lon, lat in planned_geometry])
                        if planned_geometry
                        else None
                    ),
                    "grace": checkin_grace_s,
                },
            ).one()
        return _to_guardian(row)

    def active_guardian(
        self, client_id_value: str
    ) -> tuple[GuardianSession | None, list[tuple[str, dict[str, object]]]]:
        with self._engine.connect() as conn:
            row = conn.execute(
                text(
                    f"SELECT {_GUARDIAN_COLUMNS} FROM guardian_sessions "
                    "WHERE client_id = :cid AND status IN ('ACTIVE', 'ESCALATED') "
                    "ORDER BY started_at DESC LIMIT 1"
                ),
                {"cid": client_id_value},
            ).one_or_none()
        if row is None:
            return None, []
        session = _to_guardian(row)
        return GuardianStore._evaluate(session, now=_now(), store=self, persisted=True)

    def get_guardian(
        self, client_id_value: str, session_id: str
    ) -> tuple[GuardianSession | None, list[tuple[str, dict[str, object]]]]:
        with self._engine.connect() as conn:
            row = conn.execute(
                text(
                    f"SELECT {_GUARDIAN_COLUMNS} FROM guardian_sessions "
                    "WHERE id = :id AND client_id = :cid"
                ),
                {"id": session_id, "cid": client_id_value},
            ).one_or_none()
        if row is None:
            return None, []
        session = _to_guardian(row)
        return GuardianStore._evaluate(session, now=_now(), store=self, persisted=True)

    def update_guardian_location(
        self,
        client_id_value: str,
        session_id: str,
        latitude: float,
        longitude: float,
    ) -> tuple[GuardianSession | None, list[tuple[str, dict[str, object]]]]:
        session, _ = self.get_guardian(client_id_value, session_id)
        if session is None:
            return None, []
        if session.status not in ("ACTIVE", "ESCALATED"):
            return None, []
        events: list[tuple[str, dict[str, object]]] = []
        deviation = (
            deviation_m(latitude, longitude, session.planned_geometry)
            if session.planned_geometry
            else 0.0
        )
        detected = session.deviation_detected or (
            deviation > settings.guardian_deviation_threshold_m
        )
        if detected and not session.deviation_detected:
            events.append(
                ("route_changed", {"session_id": session.id, "deviation_m": round(deviation, 1)})
            )
        with self._engine.begin() as conn:
            row = conn.execute(
                text(
                    f"UPDATE guardian_sessions SET latitude = :lat, longitude = :lon, "
                    f"last_known_at = now(), deviation_detected = :det, "
                    f"first_deviation_at = COALESCE(first_deviation_at, now()) "
                    f"WHERE id = :id AND client_id = :cid AND status IN ('ACTIVE', 'ESCALATED') "
                    f"RETURNING {_GUARDIAN_COLUMNS}"
                ),
                {
                    "id": session_id,
                    "cid": client_id_value,
                    "lat": latitude,
                    "lon": longitude,
                    "det": detected,
                },
            ).one_or_none()
        if row is None:
            return None, []
        return _to_guardian(row), events

    def checkin(
        self, client_id_value: str, session_id: str
    ) -> tuple[GuardianSession | None, list[tuple[str, dict[str, object]]]]:
        with self._engine.begin() as conn:
            row = conn.execute(
                text(
                    f"UPDATE guardian_sessions SET last_checkin_at = now(), "
                    f"expected_arrival_at = NULL, "
                    f"status = 'ACTIVE', escalation_stage = 0, notified_stage = 0 "
                    f"WHERE id = :id AND client_id = :cid AND status IN ('ACTIVE', 'ESCALATED') "
                    f"RETURNING {_GUARDIAN_COLUMNS}"
                ),
                {"id": session_id, "cid": client_id_value},
            ).one_or_none()
        return (_to_guardian(row), []) if row is not None else (None, [])

    def end_guardian(
        self, client_id_value: str, session_id: str, reason: str
    ) -> tuple[GuardianSession | None, list[tuple[str, dict[str, object]]]]:
        status = "COMPLETED" if reason == "arrived" else "CANCELLED"
        with self._engine.begin() as conn:
            row = conn.execute(
                text(
                    f"UPDATE guardian_sessions SET status = :status, ended_at = now(), "
                    f"end_reason = :reason WHERE id = :id AND client_id = :cid AND "
                    f"status IN ('ACTIVE', 'ESCALATED') RETURNING {_GUARDIAN_COLUMNS}"
                ),
                {
                    "id": session_id,
                    "cid": client_id_value,
                    "status": status,
                    "reason": reason,
                },
            ).one_or_none()
        return (_to_guardian(row), []) if row is not None else (None, [])

    def _persist_guardian(self, session: GuardianSession) -> None:
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    "UPDATE guardian_sessions SET status = :status, escalation_stage = :stage, "
                    "notified_stage = :notified WHERE id = :id"
                ),
                {
                    "id": session.id,
                    "status": session.status,
                    "stage": session.escalation_stage,
                    "notified": session.notified_stage,
                },
            )


def _make_engine() -> Engine:
    return make_engine()


@lru_cache(maxsize=4)
def get_guardian_store() -> GuardianStore:
    try:
        engine = _make_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1 FROM guardian_sessions LIMIT 1"))
        return PostgresGuardianStore(engine)
    except Exception as exc:
        logger.warning("PostGIS unavailable for guardians; using memory store: %s", exc)
        return MemoryGuardianStore()
