"""Personal safety preferences store (Feature Group Q).

Handles per-client safety preference configuration that influences routing
decisions but never bypasses the core safety model."""
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
class SafetyPreferences:
    client_id: str
    prefer_better_lit: bool
    prefer_main_roads: bool
    prefer_near_emergency: bool
    avoid_known_hazards: bool
    avoid_isolated_roads: bool
    minimize_walking_time: bool
    default_profile: str
    discreet_mode_enabled: bool
    voice_guidance_enabled: bool
    voice_language: str


def _to_preferences(row: Row[Any]) -> SafetyPreferences:
    return SafetyPreferences(
        client_id=str(row[0]),
        prefer_better_lit=bool(row[1]),
        prefer_main_roads=bool(row[2]),
        prefer_near_emergency=bool(row[3]),
        avoid_known_hazards=bool(row[4]),
        avoid_isolated_roads=bool(row[5]),
        minimize_walking_time=bool(row[6]),
        default_profile=str(row[7]),
        discreet_mode_enabled=bool(row[8]),
        voice_guidance_enabled=bool(row[9]),
        voice_language=str(row[10]),
    )


class SafetyPreferencesStore:
    def get_preferences(self, client_id_value: str) -> SafetyPreferences | None:
        raise NotImplementedError

    def update_preferences(
        self,
        client_id_value: str,
        *,
        prefer_better_lit: bool,
        prefer_main_roads: bool,
        prefer_near_emergency: bool,
        avoid_known_hazards: bool,
        avoid_isolated_roads: bool,
        minimize_walking_time: bool,
        default_profile: str,
        discreet_mode_enabled: bool,
        voice_guidance_enabled: bool,
        voice_language: str,
    ) -> SafetyPreferences:
        raise NotImplementedError


class MemorySafetyPreferencesStore(SafetyPreferencesStore):
    def __init__(self) -> None:
        self._preferences: dict[str, SafetyPreferences] = {}

    def get_preferences(self, client_id_value: str) -> SafetyPreferences | None:
        return self._preferences.get(client_id_value)

    def update_preferences(
        self,
        client_id_value: str,
        *,
        prefer_better_lit: bool,
        prefer_main_roads: bool,
        prefer_near_emergency: bool,
        avoid_known_hazards: bool,
        avoid_isolated_roads: bool,
        minimize_walking_time: bool,
        default_profile: str,
        discreet_mode_enabled: bool,
        voice_guidance_enabled: bool,
        voice_language: str,
    ) -> SafetyPreferences:
        prefs = SafetyPreferences(
            client_id=client_id_value,
            prefer_better_lit=prefer_better_lit,
            prefer_main_roads=prefer_main_roads,
            prefer_near_emergency=prefer_near_emergency,
            avoid_known_hazards=avoid_known_hazards,
            avoid_isolated_roads=avoid_isolated_roads,
            minimize_walking_time=minimize_walking_time,
            default_profile=default_profile,
            discreet_mode_enabled=discreet_mode_enabled,
            voice_guidance_enabled=voice_guidance_enabled,
            voice_language=voice_language,
        )
        self._preferences[client_id_value] = prefs
        return prefs


def _make_engine() -> Engine:
    return make_engine()


@lru_cache(maxsize=4)
def get_safety_preferences_store() -> SafetyPreferencesStore:
    try:
        engine = _make_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1 FROM safety_preferences LIMIT 1"))
        return PostgresSafetyPreferencesStore(engine)
    except Exception as exc:
        logger.warning("PostGIS unavailable for preferences; using memory store: %s", exc)
        return MemorySafetyPreferencesStore()


class PostgresSafetyPreferencesStore(SafetyPreferencesStore):
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def get_preferences(self, client_id_value: str) -> SafetyPreferences | None:
        with self._engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT client_id, prefer_better_lit, prefer_main_roads, "
                    "prefer_near_emergency, avoid_known_hazards, avoid_isolated_roads, "
                    "minimize_walking_time, default_profile, discreet_mode_enabled, "
                    "voice_guidance_enabled, voice_language FROM safety_preferences "
                    "WHERE client_id = :cid"
                ),
                {"cid": client_id_value},
            ).one_or_none()
        if row is None:
            return None
        return _to_preferences(row)

    def update_preferences(
        self,
        client_id_value: str,
        *,
        prefer_better_lit: bool,
        prefer_main_roads: bool,
        prefer_near_emergency: bool,
        avoid_known_hazards: bool,
        avoid_isolated_roads: bool,
        minimize_walking_time: bool,
        default_profile: str,
        discreet_mode_enabled: bool,
        voice_guidance_enabled: bool,
        voice_language: str,
    ) -> SafetyPreferences:
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO safety_preferences (client_id, prefer_better_lit, prefer_main_roads, "
                    "prefer_near_emergency, avoid_known_hazards, avoid_isolated_roads, "
                    "minimize_walking_time, default_profile, discreet_mode_enabled, "
                    "voice_guidance_enabled, voice_language, updated_at) "
                    "VALUES (:cid, :pref_lit, :pref_main, :pref_near, :avoid_haz, "
                    ":avoid_iso, :min_walk, :default_prof, :discreet, :voice_guid, "
                    ":voice_lang, now()) "
                    "ON CONFLICT (client_id) DO UPDATE SET "
                    "prefer_better_lit = :pref_lit, prefer_main_roads = :pref_main, "
                    "prefer_near_emergency = :pref_near, avoid_known_hazards = :avoid_haz, "
                    "avoid_isolated_roads = :avoid_iso, minimize_walking_time = :min_walk, "
                    "default_profile = :default_prof, discreet_mode_enabled = :discreet, "
                    "voice_guidance_enabled = :voice_guid, voice_language = :voice_lang, "
                    "updated_at = now()"
                ),
                {
                    "cid": client_id_value,
                    "pref_lit": prefer_better_lit,
                    "pref_main": prefer_main_roads,
                    "pref_near": prefer_near_emergency,
                    "avoid_haz": avoid_known_hazards,
                    "avoid_iso": avoid_isolated_roads,
                    "min_walk": minimize_walking_time,
                    "default_prof": default_profile,
                    "discreet": discreet_mode_enabled,
                    "voice_guid": voice_guidance_enabled,
                    "voice_lang": voice_language,
                },
            )
            row = conn.execute(
                text(
                    "SELECT client_id, prefer_better_lit, prefer_main_roads, "
                    "prefer_near_emergency, avoid_known_hazards, avoid_isolated_roads, "
                    "minimize_walking_time, default_profile, discreet_mode_enabled, "
                    "voice_guidance_enabled, voice_language FROM safety_preferences "
                    "WHERE client_id = :cid"
                ),
                {"cid": client_id_value},
            ).one()
        return _to_preferences(row)