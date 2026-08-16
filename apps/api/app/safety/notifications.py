"""In-app notification events. Every notification has a real source event.

Delivery is honest: channel 'app' is the in-app notification center; sms and
telegram require a configured provider (settings.notify_channel). Without a
provider, events are recorded with status 'no_channel' and the UI must show
"Notification queued — no channel configured", never fake delivery. When a
real Telegram provider is configured, delivery is actually attempted and the
event records 'sent' or 'failed'."""

from __future__ import annotations

import json
import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any

from sqlalchemy import Engine, Row, text

from app.config import settings
from app.db import make_engine
from app.notify import send_telegram, telegram_configured

logger = logging.getLogger(__name__)

NOTIFICATION_TYPES = (
    "sos_started",
    "sos_ended",
    "location_sharing_started",
    "location_sharing_stopped",
    "guardian_started",
    "guardian_ended",
    "journey_completed",
    "checkin_reminder",
    "checkin_missed",
    "checkin_escalated",
    "route_changed",
    "safety_alert",
)


@dataclass(frozen=True)
class NotificationEvent:
    id: int
    client_id: str
    type: str
    channel: str
    status: str
    payload: dict[str, object]
    created_at: datetime


def _to_event(row: Row[Any]) -> NotificationEvent:
    return NotificationEvent(
        id=int(row[0]),
        client_id=str(row[1]),
        type=str(row[2]),
        channel=str(row[3]),
        status=str(row[4]),
        payload=dict(row[5] or {}),
        created_at=row[6],
    )


def _telegram_text(notification_type: str, payload: dict[str, object]) -> str:
    """Human-readable one-liner for external channels. Never claims safety."""
    headline = {
        "sos_started": "SOS started",
        "sos_ended": "SOS ended",
        "location_sharing_started": "Live location sharing started",
        "location_sharing_stopped": "Live location sharing stopped",
        "guardian_started": "Guardian mode started",
        "guardian_ended": "Guardian mode ended",
        "journey_completed": "Journey completed",
        "checkin_reminder": "Check-in reminder",
        "checkin_missed": "Check-in missed",
        "checkin_escalated": "Check-in escalated",
        "route_changed": "Route changed",
        "safety_alert": "Safety alert",
    }.get(notification_type, "Map for Women notification")
    parts = [headline]
    for key in ("journey_id", "route_id", "message"):
        if payload.get(key):
            parts.append(str(payload[key]))
    return " · ".join(parts)


def expected_notify_status() -> str:
    """Status a fresh emergency session should claim: honest about the
    configured provider without over-promising live delivery."""
    if settings.notify_channel == "sms":
        return "queued"
    if settings.notify_channel == "telegram":
        return "queued" if telegram_configured() else "no_channel"
    return "no_channel"


def _delivery(notification_type: str, payload: dict[str, object]) -> tuple[str, str]:
    """Decide channel + status for a fresh event, attempting real delivery.

    Returns (channel, status). Honest statuses: 'no_channel' (nothing
    configured), 'queued' (provider configured but no live attempt, e.g. sms),
    'sent' / 'failed' (real Telegram delivery attempted)."""
    if settings.notify_channel == "sms":
        return "sms", "queued"
    if settings.notify_channel == "telegram":
        if not telegram_configured():
            return "app", "no_channel"
        ok = send_telegram(_telegram_text(notification_type, payload))
        return "telegram", "sent" if ok else "failed"
    return "app", "no_channel"


class NotificationStore:
    def record(
        self,
        client_id_value: str,
        notification_type: str,
        payload: dict[str, object],
    ) -> NotificationEvent:
        raise NotImplementedError

    def recent(self, client_id_value: str, limit: int) -> Sequence[NotificationEvent]:
        raise NotImplementedError


class MemoryNotificationStore(NotificationStore):
    def __init__(self) -> None:
        self._events: list[NotificationEvent] = []
        self._next_id = 1

    def record(
        self,
        client_id_value: str,
        notification_type: str,
        payload: dict[str, object],
    ) -> NotificationEvent:
        channel, status = _delivery(notification_type, payload)
        event = NotificationEvent(
            id=self._next_id,
            client_id=client_id_value,
            type=notification_type,
            channel=channel,
            status=status,
            payload=payload,
            created_at=datetime.now(UTC),
        )
        self._next_id += 1
        self._events.append(event)
        return event

    def recent(self, client_id_value: str, limit: int) -> Sequence[NotificationEvent]:
        return [e for e in self._events if e.client_id == client_id_value][-limit:][::-1]


class PostgresNotificationStore(NotificationStore):
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def record(
        self,
        client_id_value: str,
        notification_type: str,
        payload: dict[str, object],
    ) -> NotificationEvent:
        channel, status = _delivery(notification_type, payload)
        with self._engine.begin() as conn:
            row = conn.execute(
                text(
                    "INSERT INTO notification_events (client_id, type, channel, status, "
                    "payload_json) VALUES (:cid, :type, :channel, :status, :payload) "
                    "RETURNING id, client_id, type, channel, status, payload_json, created_at"
                ),
                {
                    "cid": client_id_value,
                    "type": notification_type,
                    "channel": channel,
                    "status": status,
                    "payload": json.dumps(payload),
                },
            ).one()
        return _to_event(row)

    def recent(self, client_id_value: str, limit: int) -> Sequence[NotificationEvent]:
        with self._engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT id, client_id, type, channel, status, payload_json, created_at "
                    "FROM notification_events WHERE client_id = :cid "
                    "ORDER BY created_at DESC LIMIT :limit"
                ),
                {"cid": client_id_value, "limit": limit},
            ).all()
        return [_to_event(row) for row in rows]


def _make_engine() -> Engine:
    return make_engine()


@lru_cache(maxsize=4)
def get_notification_store() -> NotificationStore:
    try:
        engine = _make_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1 FROM notification_events LIMIT 1"))
        return PostgresNotificationStore(engine)
    except Exception as exc:
        logger.warning("PostGIS unavailable for notifications; using memory store: %s", exc)
        return MemoryNotificationStore()
