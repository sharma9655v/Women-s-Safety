"""Safety alerts store (Feature Group K).

Handles creation, listing, and filtering of safety alerts per client.
All alerts are scoped to the pseudonymous client_id."""
from __future__ import annotations

import json
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
class Alert:
    id: int
    client_id: str
    category: str
    severity: str
    lat: float
    lon: float
    location_name: str | None
    description: str | None
    source: str
    evidence_status: str
    confidence: float
    observed_at: datetime
    expires_at: datetime | None
    created_at: datetime


def _to_alert(row: Row[Any]) -> Alert:
    return Alert(
        id=int(row[0]),
        client_id=str(row[1]),
        category=str(row[2]),
        severity=str(row[3]),
        lat=float(row[4]),
        lon=float(row[5]),
        location_name=row[6],
        description=row[7],
        source=str(row[8]),
        evidence_status=str(row[9]),
        confidence=float(row[10]),
        observed_at=row[11],
        expires_at=row[12],
        created_at=row[13],
    )


class AlertStore:
    def create_alert(
        self,
        client_id_value: str,
        *,
        category: str,
        severity: str,
        lat: float,
        lon: float,
        location_name: str | None,
        description: str | None,
        source: str,
    ) -> Alert:
        raise NotImplementedError

    def list_alerts(self, client_id_value: str, limit: int) -> Sequence[Alert]:
        raise NotImplementedError

    def active_alerts(self, client_id_value: str) -> Sequence[Alert]:
        raise NotImplementedError


class MemoryAlertStore(AlertStore):
    def __init__(self) -> None:
        self._alerts: dict[int, Alert] = {}
        self._next_id = 1

    def create_alert(
        self,
        client_id_value: str,
        *,
        category: str,
        severity: str,
        lat: float,
        lon: float,
        location_name: str | None,
        description: str | None,
        source: str,
    ) -> Alert:
        alert = Alert(
            id=self._next_id,
            client_id=client_id_value,
            category=category,
            severity=severity,
            lat=lat,
            lon=lon,
            location_name=location_name,
            description=description,
            source=source,
            evidence_status="verified",
            confidence=0.7,
            observed_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(days=30),
            created_at=datetime.now(UTC),
        )
        self._next_id += 1
        self._alerts[alert.id] = alert
        return alert

    def list_alerts(self, client_id_value: str, limit: int) -> Sequence[Alert]:
        return [
            a
            for a in self._alerts.values()
            if a.client_id == client_id_value
        ][-limit:][::-1]

    def active_alerts(self, client_id_value: str) -> Sequence[Alert]:
        now = datetime.now(UTC)
        return [
            a
            for a in self._alerts.values()
            if a.client_id == client_id_value and a.expires_at > now
        ]


def _make_engine() -> Engine:
    return make_engine()


@lru_cache(maxsize=4)
def get_alert_store() -> AlertStore:
    try:
        engine = _make_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1 FROM safety_alerts LIMIT 1"))
        return PostgresAlertStore(engine)
    except Exception as exc:
        logger.warning("PostGIS unavailable for alerts; using memory store: %s", exc)
        return MemoryAlertStore()


class PostgresAlertStore(AlertStore):
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def create_alert(
        self,
        client_id_value: str,
        *,
        category: str,
        severity: str,
        lat: float,
        lon: float,
        location_name: str | None,
        description: str | None,
        source: str,
    ) -> Alert:
        with self._engine.begin() as conn:
            row = conn.execute(
                text(
                    f"INSERT INTO safety_alerts (client_id, category, severity, lat, lon, "
                    f"location_name, description, source, evidence_status, confidence, "
                    f"observed_at) VALUES (:cid, :cat, :sev, :lat, :lon, :loc_name, "
                    f":desc, :src, :evid, :conf, :obs) RETURNING *"
                ),
                {
                    "cid": client_id_value,
                    "cat": category,
                    "sev": severity,
                    "lat": lat,
                    "lon": lon,
                    "loc_name": location_name,
                    "desc": description,
                    "src": source,
                    "evid": "verified",
                    "conf": 0.7,
                    "obs": datetime.now(UTC),
                },
            ).one()
        return _to_alert(row)

    def list_alerts(self, client_id_value: str, limit: int) -> Sequence[Alert]:
        with self._engine.connect() as conn:
            rows = conn.execute(
                text(
                    f"SELECT id, client_id, category, severity, lat, lon, location_name, "
                    f"description, source, evidence_status, confidence, observed_at, "
                    f"expires_at, created_at FROM safety_alerts WHERE client_id = :cid "
                    f"ORDER BY created_at DESC LIMIT :limit"
                ),
                {"cid": client_id_value, "limit": limit},
            ).all()
        return [_to_alert(row) for row in rows]

    def active_alerts(self, client_id_value: str) -> Sequence[Alert]:
        now = datetime.now(UTC)
        with self._engine.connect() as conn:
            rows = conn.execute(
                text(
                    f"SELECT id, client_id, category, severity, lat, lon, location_name, "
                    f"description, source, evidence_status, confidence, observed_at, "
                    f"expires_at, created_at FROM safety_alerts WHERE client_id = :cid "
                    f"AND expires_at > now ORDER BY created_at DESC"
                ),
                {"cid": client_id_value},
            ).all()
        return [_to_alert(row) for row in rows]