"""Emergency and location-sharing sessions.

Lifecycle rules (enforced by the API layer and mirrored here):
  - A session is created ONLY after the client-side countdown completes; the
    backend never creates one for a cancelled SOS.
  - Duplicate active emergency sessions are refused (one at a time).
  - Location sharing requires explicit consent (an explicit start call) and
    always has an expiry; expired sessions are treated as EXPIRED on read.
  - Session rows are readable only by their owning client_id.
"""

from __future__ import annotations

import json
import logging
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


@dataclass(frozen=True)
class EmergencySession:
    id: str
    client_id: str
    status: str
    started_at: datetime
    ended_at: datetime | None
    end_reason: str | None
    latitude: float | None
    longitude: float | None
    last_known_at: datetime | None
    notified_contact_ids: list[int]
    notify_status: str
    location_sharing: str | None


@dataclass(frozen=True)
class SharingSession:
    id: str
    client_id: str
    kind: str
    owner_session: str | None
    status: str
    started_at: datetime
    expires_at: datetime
    stopped_at: datetime | None
    latitude: float | None
    longitude: float | None
    last_updated_at: datetime | None
    recipient_ids: list[int]


def _now() -> datetime:
    return datetime.now(UTC)


def _to_emergency(row: Row[Any]) -> EmergencySession:
    return EmergencySession(
        id=str(row[0]),
        client_id=str(row[1]),
        status=str(row[2]),
        started_at=row[3],
        ended_at=row[4],
        end_reason=row[5],
        latitude=float(row[6]) if row[6] is not None else None,
        longitude=float(row[7]) if row[7] is not None else None,
        last_known_at=row[8],
        notified_contact_ids=[int(i) for i in (row[9] or [])],
        notify_status=str(row[10]),
        location_sharing=str(row[11]) if row[11] is not None else None,
    )


def _to_sharing(row: Row[Any]) -> SharingSession:
    return SharingSession(
        id=str(row[0]),
        client_id=str(row[1]),
        kind=str(row[2]),
        owner_session=str(row[3]) if row[3] is not None else None,
        status=str(row[4]),
        started_at=row[5],
        expires_at=row[6],
        stopped_at=row[7],
        latitude=float(row[8]) if row[8] is not None else None,
        longitude=float(row[9]) if row[9] is not None else None,
        last_updated_at=row[10],
        recipient_ids=[int(i) for i in (row[11] or [])],
    )


class EmergencyStore:
    def create_emergency(
        self,
        client_id_value: str,
        *,
        latitude: float | None,
        longitude: float | None,
        notified_contact_ids: Sequence[int],
        notify_status: str,
    ) -> EmergencySession:
        raise NotImplementedError

    def active_emergency(self, client_id_value: str) -> EmergencySession | None:
        raise NotImplementedError

    def get_emergency(self, client_id_value: str, session_id: str) -> EmergencySession | None:
        raise NotImplementedError

    def end_emergency(
        self, client_id_value: str, session_id: str, reason: str
    ) -> EmergencySession | None:
        raise NotImplementedError

    def update_emergency_location(
        self,
        client_id_value: str,
        session_id: str,
        latitude: float,
        longitude: float,
    ) -> EmergencySession | None:
        raise NotImplementedError

    def start_sharing(
        self,
        client_id_value: str,
        *,
        kind: str,
        owner_session: str | None,
        ttl_s: int,
        recipient_ids: Sequence[int],
    ) -> SharingSession:
        raise NotImplementedError

    def active_sharing(self, client_id_value: str) -> SharingSession | None:
        raise NotImplementedError

    def get_sharing(self, client_id_value: str, session_id: str) -> SharingSession | None:
        raise NotImplementedError

    def update_sharing_location(
        self,
        client_id_value: str,
        session_id: str,
        latitude: float,
        longitude: float,
    ) -> SharingSession | None:
        raise NotImplementedError

    def stop_sharing(self, client_id_value: str, session_id: str) -> SharingSession | None:
        raise NotImplementedError

    def _expire_lazily(self, session: SharingSession) -> SharingSession:
        """Lazy expiry: an ACTIVE sharing past its expiry reads as EXPIRED."""
        if session.status == "ACTIVE" and session.expires_at < _now():
            updated = SharingSession(
                id=session.id,
                client_id=session.client_id,
                kind=session.kind,
                owner_session=session.owner_session,
                status="EXPIRED",
                started_at=session.started_at,
                expires_at=session.expires_at,
                stopped_at=session.stopped_at,
                latitude=session.latitude,
                longitude=session.longitude,
                last_updated_at=session.last_updated_at,
                recipient_ids=session.recipient_ids,
            )
            self._mark_expired(session.id)
            return updated
        return session

    def _mark_expired(self, session_id: str) -> None:
        raise NotImplementedError


class MemoryEmergencyStore(EmergencyStore):
    def __init__(self) -> None:
        self._emergency: dict[str, EmergencySession] = {}
        self._sharing: dict[str, SharingSession] = {}

    def create_emergency(
        self,
        client_id_value: str,
        *,
        latitude: float | None,
        longitude: float | None,
        notified_contact_ids: Sequence[int],
        notify_status: str,
    ) -> EmergencySession:
        now = _now()
        session = EmergencySession(
            id=str(uuid.uuid4()),
            client_id=client_id_value,
            status="ACTIVE",
            started_at=now,
            ended_at=None,
            end_reason=None,
            latitude=latitude,
            longitude=longitude,
            last_known_at=now if latitude is not None else None,
            notified_contact_ids=list(notified_contact_ids),
            notify_status=notify_status,
            location_sharing=None,
        )
        self._emergency[session.id] = session
        return session

    def active_emergency(self, client_id_value: str) -> EmergencySession | None:
        for session in self._emergency.values():
            if session.client_id == client_id_value and session.status == "ACTIVE":
                return session
        return None

    def get_emergency(self, client_id_value: str, session_id: str) -> EmergencySession | None:
        session = self._emergency.get(session_id)
        if session is None or session.client_id != client_id_value:
            return None
        return session

    def end_emergency(
        self, client_id_value: str, session_id: str, reason: str
    ) -> EmergencySession | None:
        session = self.get_emergency(client_id_value, session_id)
        if session is None or session.status != "ACTIVE":
            return None
        updated = EmergencySession(
            id=session.id,
            client_id=session.client_id,
            status="ENDED",
            started_at=session.started_at,
            ended_at=_now(),
            end_reason=reason,
            latitude=session.latitude,
            longitude=session.longitude,
            last_known_at=session.last_known_at,
            notified_contact_ids=session.notified_contact_ids,
            notify_status=session.notify_status,
            location_sharing=session.location_sharing,
        )
        self._emergency[session.id] = updated
        return updated

    def update_emergency_location(
        self,
        client_id_value: str,
        session_id: str,
        latitude: float,
        longitude: float,
    ) -> EmergencySession | None:
        session = self.get_emergency(client_id_value, session_id)
        if session is None or session.status != "ACTIVE":
            return None
        updated = EmergencySession(
            id=session.id,
            client_id=session.client_id,
            status=session.status,
            started_at=session.started_at,
            ended_at=session.ended_at,
            end_reason=session.end_reason,
            latitude=latitude,
            longitude=longitude,
            last_known_at=_now(),
            notified_contact_ids=session.notified_contact_ids,
            notify_status=session.notify_status,
            location_sharing=session.location_sharing,
        )
        self._emergency[session.id] = updated
        return updated

    def start_sharing(
        self,
        client_id_value: str,
        *,
        kind: str,
        owner_session: str | None,
        ttl_s: int,
        recipient_ids: Sequence[int],
    ) -> SharingSession:
        now = _now()
        session = SharingSession(
            id=str(uuid.uuid4()),
            client_id=client_id_value,
            kind=kind,
            owner_session=owner_session,
            status="ACTIVE",
            started_at=now,
            expires_at=now + timedelta(seconds=ttl_s),
            stopped_at=None,
            latitude=None,
            longitude=None,
            last_updated_at=None,
            recipient_ids=list(recipient_ids),
        )
        self._sharing[session.id] = session
        return session

    def active_sharing(self, client_id_value: str) -> SharingSession | None:
        for session in self._sharing.values():
            if session.client_id == client_id_value and session.status == "ACTIVE":
                return self._expire_lazily(session)
        return None

    def get_sharing(self, client_id_value: str, session_id: str) -> SharingSession | None:
        session = self._sharing.get(session_id)
        if session is None or session.client_id != client_id_value:
            return None
        return self._expire_lazily(session)

    def update_sharing_location(
        self,
        client_id_value: str,
        session_id: str,
        latitude: float,
        longitude: float,
    ) -> SharingSession | None:
        session = self.get_sharing(client_id_value, session_id)
        if session is None or session.status != "ACTIVE":
            return None
        updated = SharingSession(
            id=session.id,
            client_id=session.client_id,
            kind=session.kind,
            owner_session=session.owner_session,
            status=session.status,
            started_at=session.started_at,
            expires_at=session.expires_at,
            stopped_at=session.stopped_at,
            latitude=latitude,
            longitude=longitude,
            last_updated_at=_now(),
            recipient_ids=session.recipient_ids,
        )
        self._sharing[session.id] = updated
        return updated

    def stop_sharing(self, client_id_value: str, session_id: str) -> SharingSession | None:
        session = self.get_sharing(client_id_value, session_id)
        if session is None or session.status != "ACTIVE":
            return None
        updated = SharingSession(
            id=session.id,
            client_id=session.client_id,
            kind=session.kind,
            owner_session=session.owner_session,
            status="STOPPED",
            started_at=session.started_at,
            expires_at=session.expires_at,
            stopped_at=_now(),
            latitude=session.latitude,
            longitude=session.longitude,
            last_updated_at=session.last_updated_at,
            recipient_ids=session.recipient_ids,
        )
        self._sharing[session.id] = updated
        return updated

    def _mark_expired(self, session_id: str) -> None:
        session = self._sharing.get(session_id)
        if session is None or session.status != "ACTIVE":
            return
        updated = SharingSession(
            id=session.id,
            client_id=session.client_id,
            kind=session.kind,
            owner_session=session.owner_session,
            status="EXPIRED",
            started_at=session.started_at,
            expires_at=session.expires_at,
            stopped_at=session.stopped_at,
            latitude=session.latitude,
            longitude=session.longitude,
            last_updated_at=session.last_updated_at,
            recipient_ids=session.recipient_ids,
        )
        self._sharing[session.id] = updated


_EMERGENCY_COLUMNS = (
    "id, client_id, status, started_at, ended_at, end_reason, latitude, longitude, "
    "last_known_at, notified_contact_ids, notify_status, location_sharing"
)
_SHARING_COLUMNS = (
    "id, client_id, kind, owner_session, status, started_at, expires_at, stopped_at, "
    "latitude, longitude, last_updated_at, recipient_ids"
)


class PostgresEmergencyStore(EmergencyStore):
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def create_emergency(
        self,
        client_id_value: str,
        *,
        latitude: float | None,
        longitude: float | None,
        notified_contact_ids: Sequence[int],
        notify_status: str,
    ) -> EmergencySession:
        with self._engine.begin() as conn:
            row = conn.execute(
                text(
                    f"INSERT INTO emergency_sessions (client_id, latitude, longitude, "
                    f"last_known_at, notified_contact_ids, notify_status) "
                    f"VALUES (:cid, :lat, :lon, :known, :ids, :status) "
                    f"RETURNING {_EMERGENCY_COLUMNS}"
                ),
                {
                    "cid": client_id_value,
                    "lat": latitude,
                    "lon": longitude,
                    "known": _now() if latitude is not None else None,
                    "ids": json.dumps(list(notified_contact_ids)),
                    "status": notify_status,
                },
            ).one()
        return _to_emergency(row)

    def active_emergency(self, client_id_value: str) -> EmergencySession | None:
        with self._engine.connect() as conn:
            row = conn.execute(
                text(
                    f"SELECT {_EMERGENCY_COLUMNS} FROM emergency_sessions "
                    "WHERE client_id = :cid AND status = 'ACTIVE' ORDER BY started_at DESC LIMIT 1"
                ),
                {"cid": client_id_value},
            ).one_or_none()
        return _to_emergency(row) if row is not None else None

    def get_emergency(self, client_id_value: str, session_id: str) -> EmergencySession | None:
        with self._engine.connect() as conn:
            row = conn.execute(
                text(
                    f"SELECT {_EMERGENCY_COLUMNS} FROM emergency_sessions "
                    "WHERE id = :id AND client_id = :cid"
                ),
                {"id": session_id, "cid": client_id_value},
            ).one_or_none()
        return _to_emergency(row) if row is not None else None

    def end_emergency(
        self, client_id_value: str, session_id: str, reason: str
    ) -> EmergencySession | None:
        with self._engine.begin() as conn:
            row = conn.execute(
                text(
                    f"UPDATE emergency_sessions SET status = 'ENDED', ended_at = now(), "
                    f"end_reason = :reason WHERE id = :id AND client_id = :cid AND "
                    f"status = 'ACTIVE' RETURNING {_EMERGENCY_COLUMNS}"
                ),
                {"id": session_id, "cid": client_id_value, "reason": reason},
            ).one_or_none()
        return _to_emergency(row) if row is not None else None

    def update_emergency_location(
        self,
        client_id_value: str,
        session_id: str,
        latitude: float,
        longitude: float,
    ) -> EmergencySession | None:
        with self._engine.begin() as conn:
            row = conn.execute(
                text(
                    f"UPDATE emergency_sessions SET latitude = :lat, longitude = :lon, "
                    f"last_known_at = now() WHERE id = :id AND client_id = :cid AND "
                    f"status = 'ACTIVE' RETURNING {_EMERGENCY_COLUMNS}"
                ),
                {"id": session_id, "cid": client_id_value, "lat": latitude, "lon": longitude},
            ).one_or_none()
        return _to_emergency(row) if row is not None else None

    def start_sharing(
        self,
        client_id_value: str,
        *,
        kind: str,
        owner_session: str | None,
        ttl_s: int,
        recipient_ids: Sequence[int],
    ) -> SharingSession:
        with self._engine.begin() as conn:
            row = conn.execute(
                text(
                    f"INSERT INTO location_sharing_sessions (client_id, kind, owner_session, "
                    f"expires_at, recipient_ids) VALUES (:cid, :kind, :owner, :expires, :ids) "
                    f"RETURNING {_SHARING_COLUMNS}"
                ),
                {
                    "cid": client_id_value,
                    "kind": kind,
                    "owner": owner_session,
                    "expires": _now() + timedelta(seconds=ttl_s),
                    "ids": json.dumps(list(recipient_ids)),
                },
            ).one()
        return _to_sharing(row)

    def active_sharing(self, client_id_value: str) -> SharingSession | None:
        with self._engine.connect() as conn:
            row = conn.execute(
                text(
                    f"SELECT {_SHARING_COLUMNS} FROM location_sharing_sessions "
                    "WHERE client_id = :cid AND status = 'ACTIVE' ORDER BY started_at DESC LIMIT 1"
                ),
                {"cid": client_id_value},
            ).one_or_none()
        if row is None:
            return None
        session = _to_sharing(row)
        return self._expire_lazily(session)

    def get_sharing(self, client_id_value: str, session_id: str) -> SharingSession | None:
        with self._engine.connect() as conn:
            row = conn.execute(
                text(
                    f"SELECT {_SHARING_COLUMNS} FROM location_sharing_sessions "
                    "WHERE id = :id AND client_id = :cid"
                ),
                {"id": session_id, "cid": client_id_value},
            ).one_or_none()
        if row is None:
            return None
        return self._expire_lazily(_to_sharing(row))

    def update_sharing_location(
        self,
        client_id_value: str,
        session_id: str,
        latitude: float,
        longitude: float,
    ) -> SharingSession | None:
        with self._engine.begin() as conn:
            row = conn.execute(
                text(
                    f"UPDATE location_sharing_sessions SET latitude = :lat, longitude = :lon, "
                    f"last_updated_at = now() WHERE id = :id AND client_id = :cid AND "
                    f"status = 'ACTIVE' AND expires_at > now() RETURNING {_SHARING_COLUMNS}"
                ),
                {"id": session_id, "cid": client_id_value, "lat": latitude, "lon": longitude},
            ).one_or_none()
        return _to_sharing(row) if row is not None else None

    def stop_sharing(self, client_id_value: str, session_id: str) -> SharingSession | None:
        with self._engine.begin() as conn:
            row = conn.execute(
                text(
                    f"UPDATE location_sharing_sessions SET status = 'STOPPED', stopped_at = now() "
                    f"WHERE id = :id AND client_id = :cid AND status = 'ACTIVE' "
                    f"RETURNING {_SHARING_COLUMNS}"
                ),
                {"id": session_id, "cid": client_id_value},
            ).one_or_none()
        return _to_sharing(row) if row is not None else None

    def _mark_expired(self, session_id: str) -> None:
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    "UPDATE location_sharing_sessions SET status = 'EXPIRED' "
                    "WHERE id = :id AND status = 'ACTIVE' AND expires_at <= now()"
                ),
                {"id": session_id},
            )


def _make_engine() -> Engine:
    return make_engine()


@lru_cache(maxsize=4)
def get_sessions_store() -> EmergencyStore:
    try:
        engine = _make_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1 FROM emergency_sessions LIMIT 1"))
        return PostgresEmergencyStore(engine)
    except Exception as exc:
        logger.warning("PostGIS unavailable for sessions; using memory store: %s", exc)
        return MemoryEmergencyStore()
