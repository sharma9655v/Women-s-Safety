"""Voice guidance sessions store (Feature Group U).

Handles voice guidance settings and session tracking for navigation voice prompts."""
from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any

from sqlalchemy import Engine, Row, text

from app.db import make_engine

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class VoiceGuidanceSession:
    id: str
    client_id: str
    route_session_id: str | None
    language: str
    active: bool
    started_at: datetime
    ended_at: datetime | None


def _to_voice_guidance(row: Row[Any]) -> VoiceGuidanceSession:
    return VoiceGuidanceSession(
        id=str(row[0]),
        client_id=str(row[1]),
        route_session_id=str(row[2]) if row[2] is not None else None,
        language=str(row[3]),
        active=bool(row[4]),
        started_at=row[5],
        ended_at=row[6],
    )


class VoiceGuidanceStore:
    def start_voice_guidance(
        self,
        client_id_value: str,
        *,
        route_session_id: str | None,
        language: str,
    ) -> VoiceGuidanceSession:
        raise NotImplementedError

    def stop_voice_guidance(self, client_id_value: str) -> VoiceGuidanceSession | None:
        raise NotImplementedError

    def get_voice_status(self, client_id_value: str) -> VoiceGuidanceSession | None:
        raise NotImplementedError


class MemoryVoiceGuidanceStore(VoiceGuidanceStore):
    def __init__(self) -> None:
        self._sessions: dict[str, VoiceGuidanceSession] = {}

    def start_voice_guidance(
        self,
        client_id_value: str,
        *,
        route_session_id: str | None,
        language: str,
    ) -> VoiceGuidanceSession:
        session_id = str(uuid.uuid4())
        now = datetime.now(UTC)
        session = VoiceGuidanceSession(
            id=session_id,
            client_id=client_id_value,
            route_session_id=route_session_id,
            language=language,
            active=True,
            started_at=now,
            ended_at=None,
        )
        self._sessions[session_id] = session
        return session

    def stop_voice_guidance(self, client_id_value: str) -> VoiceGuidanceSession | None:
        for session_id, session in self._sessions.items():
            if session.client_id == client_id_value and session.active:
                updated = VoiceGuidanceSession(
                    id=session.id,
                    client_id=session.client_id,
                    route_session_id=session.route_session_id,
                    language=session.language,
                    active=False,
                    started_at=session.started_at,
                    ended_at=datetime.now(UTC),
                )
                self._sessions[session_id] = updated
                return updated
        return None

    def get_voice_status(self, client_id_value: str) -> VoiceGuidanceSession | None:
        for session in self._sessions.values():
            if session.client_id == client_id_value:
                return session
        return None


def _make_engine() -> Engine:
    return make_engine()


@lru_cache(maxsize=4)
def get_voice_guidance_store() -> VoiceGuidanceStore:
    try:
        engine = _make_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1 FROM voice_guidance_sessions LIMIT 1"))
        return PostgresVoiceGuidanceStore(engine)
    except Exception as exc:
        logger.warning("PostGIS unavailable for voice guidance; using memory store: %s", exc)
        return MemoryVoiceGuidanceStore()


class PostgresVoiceGuidanceStore(VoiceGuidanceStore):
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def start_voice_guidance(
        self,
        client_id_value: str,
        *,
        route_session_id: str | None,
        language: str,
    ) -> VoiceGuidanceSession:
        with self._engine.begin() as conn:
            row = conn.execute(
                text(
                    f"INSERT INTO voice_guidance_sessions (client_id, route_session_id, "
                    f"language, active, started_at) VALUES (:cid, :route_sid, :lang, "
                    f":active, now()) RETURNING *"
                ),
                {
                    "cid": client_id_value,
                    "route_sid": route_session_id,
                    "lang": language,
                    "active": True,
                },
            ).one()
        return _to_voice_guidance(row)

    def stop_voice_guidance(self, client_id_value: str) -> VoiceGuidanceSession | None:
        with self._engine.begin() as conn:
            row = conn.execute(
                text(
                    f"UPDATE voice_guidance_sessions SET active = FALSE, ended_at = now() "
                    f"WHERE client_id = :cid AND active = TRUE RETURNING *"
                ),
                {"cid": client_id_value},
            ).one_or_none()
        if row is None:
            return None
        return _to_voice_guidance(row)

    def get_voice_status(self, client_id_value: str) -> VoiceGuidanceSession | None:
        with self._engine.connect() as conn:
            row = conn.execute(
                text(
                    f"SELECT id, client_id, route_session_id, language, active, "
                    f"started_at, ended_at FROM voice_guidance_sessions WHERE client_id = :cid "
                    f"ORDER BY started_at DESC LIMIT 1"
                ),
                {"cid": client_id_value},
            ).one_or_none()
        if row is None:
            return None
        return _to_voice_guidance(row)