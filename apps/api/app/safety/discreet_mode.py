"""Discreet mode settings store (Feature Group S).

Handles per-client discreet mode configuration for safety function access."""
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
class DiscreetModeSettings:
    client_id: str
    enabled: bool
    quick_sos_gesture: str
    exit_to_neutral_app: bool
    neutral_app_label: str
    neutral_app_icon: str


def _to_discreet_settings(row: Row[Any]) -> DiscreetModeSettings:
    return DiscreetModeSettings(
        client_id=str(row[0]),
        enabled=bool(row[1]),
        quick_sos_gesture=str(row[2]),
        exit_to_neutral_app=bool(row[3]),
        neutral_app_label=str(row[4]),
        neutral_app_icon=str(row[5]),
    )


class DiscreetModeSettingsStore:
    def get_settings(self, client_id_value: str) -> DiscreetModeSettings | None:
        raise NotImplementedError

    def update_settings(
        self,
        client_id_value: str,
        *,
        enabled: bool,
        quick_sos_gesture: str,
        exit_to_neutral_app: bool,
        neutral_app_label: str,
        neutral_app_icon: str,
    ) -> DiscreetModeSettings:
        raise NotImplementedError


class MemoryDiscreetModeSettingsStore(DiscreetModeSettingsStore):
    def __init__(self) -> None:
        self._settings: dict[str, DiscreetModeSettings] = {}

    def get_settings(self, client_id_value: str) -> DiscreetModeSettings | None:
        return self._settings.get(client_id_value)

    def update_settings(
        self,
        client_id_value: str,
        *,
        enabled: bool,
        quick_sos_gesture: str,
        exit_to_neutral_app: bool,
        neutral_app_label: str,
        neutral_app_icon: str,
    ) -> DiscreetModeSettings:
        settings = DiscreetModeSettings(
            client_id=client_id_value,
            enabled=enabled,
            quick_sos_gesture=quick_sos_gesture,
            exit_to_neutral_app=exit_to_neutral_app,
            neutral_app_label=neutral_app_label,
            neutral_app_icon=neutral_app_icon,
        )
        self._settings[client_id_value] = settings
        return settings


def _make_engine() -> Engine:
    return make_engine()


@lru_cache(maxsize=4)
def get_discreet_mode_settings_store() -> DiscreetModeSettingsStore:
    try:
        engine = _make_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1 FROM discreet_mode_settings LIMIT 1"))
        return PostgresDiscreetModeSettingsStore(engine)
    except Exception as exc:
        logger.warning("PostGIS unavailable for discreet mode; using memory store: %s", exc)
        return MemoryDiscreetModeSettingsStore()


class PostgresDiscreetModeSettingsStore(DiscreetModeSettingsStore):
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def get_settings(self, client_id_value: str) -> DiscreetModeSettings | None:
        with self._engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT client_id, enabled, quick_sos_gesture, "
                    "exit_to_neutral_app, neutral_app_label, neutral_app_icon "
                    "FROM discreet_mode_settings WHERE client_id = :cid"
                ),
                {"cid": client_id_value},
            ).one_or_none()
        if row is None:
            return None
        return _to_discreet_settings(row)

    def update_settings(
        self,
        client_id_value: str,
        *,
        enabled: bool,
        quick_sos_gesture: str,
        exit_to_neutral_app: bool,
        neutral_app_label: str,
        neutral_app_icon: str,
    ) -> DiscreetModeSettings:
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO discreet_mode_settings (client_id, enabled, quick_sos_gesture, "
                    "exit_to_neutral_app, neutral_app_label, neutral_app_icon, updated_at) "
                    "VALUES (:cid, :enabled, :quick_sos, :exit_to_neu, :neu_label, "
                    ":neu_icon, now()) "
                    "ON CONFLICT (client_id) DO UPDATE SET "
                    "enabled = :enabled, quick_sos_gesture = :quick_sos, "
                    "exit_to_neutral_app = :exit_to_neu, "
                    "neutral_app_label = :neu_label, neutral_app_icon = :neu_icon, "
                    "updated_at = now()"
                ),
                {
                    "cid": client_id_value,
                    "enabled": enabled,
                    "quick_sos": quick_sos_gesture,
                    "exit_to_neu": exit_to_neutral_app,
                    "neu_label": neutral_app_label,
                    "neu_icon": neutral_app_icon,
                },
            )
            row = conn.execute(
                text(
                    "SELECT client_id, enabled, quick_sos_gesture, "
                    "exit_to_neutral_app, neutral_app_label, neutral_app_icon "
                    "FROM discreet_mode_settings WHERE client_id = :cid"
                ),
                {"cid": client_id_value},
            ).one()
        return _to_discreet_settings(row)