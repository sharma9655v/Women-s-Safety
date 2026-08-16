"""Fake call sessions store (Feature Group T).

Handles user-controlled scheduled fake calls for distraction purposes."""
from __future__ import annotations

import json
import logging
import uuid
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
class FakeCallSession:
    id: str
    client_id: str
    caller_name: str
    caller_number: str | None
    scheduled_at: datetime
    triggered_at: datetime | None
    status: str  # SCHEDULED, TRIGGERED, DISMISSED, EXPIRED


def _to_fake_call(row: Row[Any]) -> FakeCallSession:
    return FakeCallSession(
        id=str(row[0]),
        client_id=str(row[1]),
        caller_name=str(row[2]),
        caller_number=str(row[3]) if row[3] is not None else None,
        scheduled_at=row[4],
        triggered_at=row[5],
        status=str(row[6]),
    )


class FakeCallStore:
    def create_fake_call(
        self,
        client_id_value: str,
        *,
        caller_name: str,
        caller_number: str | None,
        scheduled_at: datetime,
    ) -> FakeCallSession:
        raise NotImplementedError

    def get_fake_call(self, client_id_value: str, call_id: str) -> FakeCallSession | None:
        raise NotImplementedError


class MemoryFakeCallStore(FakeCallStore):
    def __init__(self) -> None:
        self._calls: dict[str, FakeCallSession] = {}

    def create_fake_call(
        self,
        client_id_value: str,
        *,
        caller_name: str,
        caller_number: str | None,
        scheduled_at: datetime,
    ) -> FakeCallSession:
        call_id = str(uuid.uuid4())
        call = FakeCallSession(
            id=call_id,
            client_id=client_id_value,
            caller_name=caller_name,
            caller_number=caller_number,
            scheduled_at=scheduled_at,
            triggered_at=None,
            status="SCHEDULED",
        )
        self._calls[call_id] = call
        return call

    def get_fake_call(self, client_id_value: str, call_id: str) -> FakeCallSession | None:
        call = self._calls.get(call_id)
        if call is None or call.client_id != client_id_value:
            return None
        return call


def _make_engine() -> Engine:
    return make_engine()


@lru_cache(maxsize=4)
def get_fake_call_store() -> FakeCallStore:
    try:
        engine = _make_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1 FROM fake_call_sessions LIMIT 1"))
        return PostgresFakeCallStore(engine)
    except Exception as exc:
        logger.warning("PostGIS unavailable for fake calls; using memory store: %s", exc)
        return MemoryFakeCallStore()


class PostgresFakeCallStore(FakeCallStore):
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def create_fake_call(
        self,
        client_id_value: str,
        *,
        caller_name: str,
        caller_number: str | None,
        scheduled_at: datetime,
    ) -> FakeCallSession:
        with self._engine.begin() as conn:
            row = conn.execute(
                text(
                    f"INSERT INTO fake_call_sessions (client_id, caller_name, caller_number, "
                    f"scheduled_at) VALUES (:cid, :caller_name, :caller_number, :scheduled) "
                    f"RETURNING *"
                ),
                {
                    "cid": client_id_value,
                    "caller_name": caller_name,
                    "caller_number": caller_number,
                    "scheduled": scheduled_at,
                },
            ).one()
        return _to_fake_call(row)

    def get_fake_call(self, client_id_value: str, call_id: str) -> FakeCallSession | None:
        with self._engine.connect() as conn:
            row = conn.execute(
                text(
                    f"SELECT id, client_id, caller_name, caller_number, scheduled_at, "
                    f"triggered_at, status FROM fake_call_sessions WHERE id = :id AND "
                    f"client_id = :cid"
                ),
                {"id": call_id, "cid": client_id_value},
            ).one_or_none()
        if row is None:
            return None
        return _to_fake_call(row)