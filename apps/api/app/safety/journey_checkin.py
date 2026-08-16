"""Journey check-ins (Phase 11): standalone safety check-ins outside Guardian mode.

Rules (mirrored by the API layer):
  - One active journey check-in per client at a time.
  - The owner checks in periodically; the deadline is the expected arrival
    (if set) or the last check-in, plus a grace period.
  - Missed check-ins escalate in stages: 1 = checkin_missed, 2 =
    checkin_escalated (status ESCALATED). Notifications are emitted exactly
    once per stage (notified_stage watermark).
  - Trusted contacts can be designated but no automatic emergency is triggered.
  - Sessions are readable only by their owning client_id."""
from __future__ import annotations

import json
import logging
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
class JourneyCheckinSession:
    id: str
    client_id: str
    status: str  # ACTIVE | COMPLETED | CANCELLED | ESCALATED | MISSED
    started_at: datetime
    ended_at: datetime | None
    end_reason: str | None
    destination_name: str | None
    destination_lat: float | None
    destination_lon: float | None
    expected_arrival_at: datetime | None
    checkin_interval_s: int
    checkin_grace_s: int
    last_checkin_at: datetime | None
    next_checkin_at: datetime | None
    contact_ids: list[int]
    escalation_stage: int
    notified_stage: int
    latitude: float | None
    longitude: float | None
    last_known_at: datetime | None


def _to_journey_checkin(row: Row[Any]) -> JourneyCheckinSession:
    return JourneyCheckinSession(
        id=str(row[0]),
        client_id=str(row[1]),
        status=str(row[2]),
        started_at=row[3],
        ended_at=row[4],
        end_reason=row[5],
        destination_name=row[6],
        destination_lat=float(row[7]) if row[7] is not None else None,
        destination_lon=float(row[8]) if row[8] is not None else None,
        expected_arrival_at=row[9],
        checkin_interval_s=int(row[10]),
        checkin_grace_s=int(row[11]),
        last_checkin_at=row[12],
        next_checkin_at=row[13],
        contact_ids=[int(i) for i in (row[14] or [])],
        escalation_stage=int(row[15]),
        notified_stage=int(row[16]),
        latitude=float(row[17]) if row[17] is not None else None,
        longitude=float(row[18]) if row[18] is not None else None,
        last_known_at=row[19],
    )


class JourneyCheckinStore:
    def create_journey_checkin(
        self,
        client_id_value: str,
        *,
        destination_name: str,
        destination_lat: float | None,
        destination_lon: float | None,
        expected_arrival_at: datetime | None,
        checkin_interval_s: int,
        checkin_grace_s: int,
        contact_ids: Sequence[int],
    ) -> JourneyCheckinSession:
        raise NotImplementedError

    def active_journey_checkin(self, client_id_value: str) -> JourneyCheckinSession | None:
        raise NotImplementedError

    def checkin_journey(
        self, client_id_value: str, session_id: str
    ) -> tuple[JourneyCheckinSession | None, list[tuple[str, dict[str, object]]]]:
        raise NotImplementedError

    def end_journey_checkin(
        self, client_id_value: str, session_id: str, reason: str
    ) -> tuple[JourneyCheckinSession | None, list[tuple[str, dict[str, object]]]]:
        raise NotImplementedError


class MemoryJourneyCheckinStore(JourneyCheckinStore):
    def __init__(self) -> None:
        self._checkins: dict[str, JourneyCheckinSession] = {}

    def create_journey_checkin(
        self,
        client_id_value: str,
        *,
        destination_name: str,
        destination_lat: float | None,
        destination_lon: float | None,
        expected_arrival_at: datetime | None,
        checkin_interval_s: int,
        checkin_grace_s: int,
        contact_ids: Sequence[int],
    ) -> JourneyCheckinSession:
        now = _now()
        next_checkin = now + timedelta(seconds=checkin_interval_s)
        session = JourneyCheckinSession(
            id=str(uuid.uuid4()),
            client_id=client_id_value,
            status="ACTIVE",
            started_at=now,
            ended_at=None,
            end_reason=None,
            destination_name=destination_name,
            destination_lat=destination_lat,
            destination_lon=destination_lon,
            expected_arrival_at=expected_arrival_at,
            checkin_interval_s=checkin_interval_s,
            checkin_grace_s=checkin_grace_s,
            last_checkin_at=None,
            next_checkin_at=next_checkin,
            contact_ids=list(contact_ids),
            escalation_stage=0,
            notified_stage=0,
            latitude=None,
            longitude=None,
            last_known_at=None,
        )
        self._checkins[session.id] = session
        return session

    def active_journey_checkin(self, client_id_value: str) -> JourneyCheckinSession | None:
        for session in self._checkins.values():
            if session.client_id == client_id_value and session.status in ("ACTIVE", "ESCALATED"):
                return session
        return None

    def checkin_journey(
        self, client_id_value: str, session_id: str
    ) -> tuple[JourneyCheckinSession | None, list[tuple[str, dict[str, object]]]]:
        session = self._checkins.get(session_id)
        if session is None or session.client_id != client_id_value:
            return None, []
        if session.status not in ("ACTIVE", "ESCALATED"):
            return None, []
        now = _now()
        updated = JourneyCheckinSession(
            id=session.id,
            client_id=session.client_id,
            status="ACTIVE",
            started_at=session.started_at,
            ended_at=session.ended_at,
            end_reason=session.end_reason,
            destination_name=session.destination_name,
            destination_lat=session.destination_lat,
            destination_lon=session.destination_lon,
            expected_arrival_at=None,  # superseded by the fresh check-in
            checkin_interval_s=session.checkin_interval_s,
            checkin_grace_s=session.checkin_grace_s,
            last_checkin_at=now,
            next_checkin_at=now + timedelta(seconds=session.checkin_interval_s),
            contact_ids=session.contact_ids,
            escalation_stage=0,
            notified_stage=0,
            latitude=session.latitude,
            longitude=session.longitude,
            last_known_at=session.last_known_at,
        )
        self._checkins[session_id] = updated
        return updated, []

    def end_journey_checkin(
        self, client_id_value: str, session_id: str, reason: str
    ) -> tuple[JourneyCheckinSession | None, list[tuple[str, dict[str, object]]]]:
        session = self._checkins.get(session_id)
        if session is None or session.client_id != client_id_value:
            return None, []
        if session.status not in ("ACTIVE", "ESCALATED"):
            return None, []
        status = "COMPLETED" if reason == "arrived" else "CANCELLED"
        updated = JourneyCheckinSession(
            id=session.id,
            client_id=session.client_id,
            status=status,
            started_at=session.started_at,
            ended_at=_now(),
            end_reason=reason,
            destination_name=session.destination_name,
            destination_lat=session.destination_lat,
            destination_lon=session.destination_lon,
            expected_arrival_at=session.expected_arrival_at,
            checkin_interval_s=session.checkin_interval_s,
            checkin_grace_s=session.checkin_grace_s,
            last_checkin_at=session.last_checkin_at,
            next_checkin_at=None,
            contact_ids=session.contact_ids,
            escalation_stage=session.escalation_stage,
            notified_stage=session.notified_stage,
            latitude=session.latitude,
            longitude=session.longitude,
            last_known_at=session.last_known_at,
        )
        self._checkins[session_id] = updated
        return updated, []


def _make_engine() -> Engine:
    return make_engine()


@lru_cache(maxsize=4)
def get_journey_checkin_store() -> JourneyCheckinStore:
    try:
        engine = _make_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1 FROM journey_checkins LIMIT 1"))
        return PostgresJourneyCheckinStore(engine)
    except Exception as exc:
        logger.warning("PostGIS unavailable for journey checkins; using memory store: %s", exc)
        return MemoryJourneyCheckinStore()


class PostgresJourneyCheckinStore(JourneyCheckinStore):
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def create_journey_checkin(
        self,
        client_id_value: str,
        *,
        destination_name: str,
        destination_lat: float | None,
        destination_lon: float | None,
        expected_arrival_at: datetime | None,
        checkin_interval_s: int,
        checkin_grace_s: int,
        contact_ids: Sequence[int],
    ) -> JourneyCheckinSession:
        with self._engine.begin() as conn:
            row = conn.execute(
                text(
                    f"INSERT INTO journey_checkins (client_id, destination_name, destination_lat, "
                    f"destination_lon, expected_arrival_at, checkin_interval_s, checkin_grace_s, "
                    f"contact_ids) VALUES (:cid, :dest_name, :dest_lat, :dest_lon, :arrival, "
                    f":interval, :grace, :ids) RETURNING *"
                ),
                {
                    "cid": client_id_value,
                    "dest_name": destination_name,
                    "dest_lat": destination_lat,
                    "dest_lon": destination_lon,
                    "arrival": expected_arrival_at,
                    "interval": checkin_interval_s,
                    "grace": checkin_grace_s,
                    "ids": json.dumps(list(contact_ids)),
                },
            ).one()
        return _to_journey_checkin(row)

    def active_journey_checkin(self, client_id_value: str) -> JourneyCheckinSession | None:
        with self._engine.connect() as conn:
            row = conn.execute(
                text(
                    f"SELECT * FROM journey_checkins WHERE client_id = :cid AND status IN ('ACTIVE', 'ESCALATED') ORDER BY started_at DESC LIMIT 1"
                ),
                {"cid": client_id_value},
            ).one_or_none()
        if row is None:
            return None
        return _to_journey_checkin(row)

    def checkin_journey(
        self, client_id_value: str, session_id: str
    ) -> tuple[JourneyCheckinSession | None, list[tuple[str, dict[str, object]]]]:
        with self._engine.begin() as conn:
            row = conn.execute(
                text(
                    f"UPDATE journey_checkins SET last_checkin_at = now(), "
                    f"next_checkin_at = now() + checkin_interval_s * interval '1 second', "
                    f"escalation_stage = 0, notified_stage = 0 "
                    f"WHERE id = :id AND client_id = :cid AND status IN ('ACTIVE', 'ESCALATED') "
                    f"RETURNING *"
                ),
                {"id": session_id, "cid": client_id_value},
            ).one_or_none()
        if row is None:
            return None, []
        return _to_journey_checkin(row), []

    def end_journey_checkin(
        self, client_id_value: str, session_id: str, reason: str
    ) -> tuple[JourneyCheckinSession | None, list[tuple[str, dict[str, object]]]]:
        status = "COMPLETED" if reason == "arrived" else "CANCELLED"
        with self._engine.begin() as conn:
            row = conn.execute(
                text(
                    f"UPDATE journey_checkins SET status = :status, ended_at = now(), "
                    f"end_reason = :reason WHERE id = :id AND client_id = :cid AND "
                    f"status IN ('ACTIVE', 'ESCALATED') RETURNING *"
                ),
                {"id": session_id, "cid": client_id_value, "status": status, "reason": reason},
            ).one_or_none()
        if row is None:
            return None, []
        return _to_journey_checkin(row), []