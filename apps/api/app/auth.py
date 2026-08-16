"""Device session tokens (Group D auth layer).

Personal-safety endpoints require a revocable bearer token issued by
POST /api/auth/device, bound to the device's pseudonymous client_id. Only the
sha256 hash of a token is stored, tokens expire, and a device can revoke its
token at any time.

This is a session layer over the pseudonymous model, not real identity
authentication: the token proves the device presented a client_id, and
revocation gives a device a way to end access. Production deployments must
keep ALLOW_LEGACY_CLIENT_ID off so the raw X-Client-Id header alone is never
accepted for private endpoints.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from functools import lru_cache

from fastapi import HTTPException, Request, status
from sqlalchemy import Engine, text

from app.config import settings
from app.db import make_engine
from app.identity import client_id_from_header


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class MemoryDeviceSessionStore:
    """In-memory session store (dev/test fallback)."""

    def __init__(self) -> None:
        self._sessions: dict[str, tuple[str, datetime]] = {}

    def create(self, client_id_value: str, ttl: timedelta) -> str:
        token = secrets.token_urlsafe(32)
        self._sessions[_hash_token(token)] = (
            client_id_value,
            datetime.now(UTC) + ttl,
        )
        return token

    def resolve(self, token: str) -> str | None:
        entry = self._sessions.get(_hash_token(token))
        if entry is None:
            return None
        client_id_value, expires_at = entry
        if datetime.now(UTC) > expires_at:
            self._sessions.pop(_hash_token(token), None)
            return None
        return client_id_value

    def revoke(self, token: str) -> None:
        self._sessions.pop(_hash_token(token), None)


class PostgresDeviceSessionStore:
    """device_sessions table store (production)."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def create(self, client_id_value: str, ttl: timedelta) -> str:
        token = secrets.token_urlsafe(32)
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO device_sessions (token_hash, client_id, expires_at) "
                    "VALUES (:token_hash, :client_id, :expires_at)"
                ),
                {
                    "token_hash": _hash_token(token),
                    "client_id": client_id_value,
                    "expires_at": datetime.now(UTC) + ttl,
                },
            )
        return token

    def resolve(self, token: str) -> str | None:
        with self._engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT client_id, expires_at FROM device_sessions "
                    "WHERE token_hash = :token_hash"
                ),
                {"token_hash": _hash_token(token)},
            ).first()
        if row is None:
            return None
        client_id_value, expires_at = row
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if datetime.now(UTC) > expires_at:
            return None
        return str(client_id_value)

    def revoke(self, token: str) -> None:
        with self._engine.begin() as conn:
            conn.execute(
                text("DELETE FROM device_sessions WHERE token_hash = :token_hash"),
                {"token_hash": _hash_token(token)},
            )


@lru_cache(maxsize=1)
def get_device_session_store() -> MemoryDeviceSessionStore | PostgresDeviceSessionStore:
    """PostGIS when reachable, else the in-memory fallback (tests/dev)."""
    if settings.database_url:
        try:
            engine = make_engine()
            with engine.connect():
                pass
            return PostgresDeviceSessionStore(engine)
        except Exception:
            pass
    return MemoryDeviceSessionStore()


def require_client_id(request: Request) -> str:
    """Client identity for private endpoints.

    Accepts a bearer device-session token. When ALLOW_LEGACY_CLIENT_ID is
    enabled (explicit dev/test compatibility), the raw X-Client-Id header is
    accepted as a fallback. Production keeps it off.
    """
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        token = auth[7:].strip()
        if not token:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")
        store = get_device_session_store()
        client_id_value = store.resolve(token)
        if client_id_value is None:
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED,
                "Session token is invalid or expired",
            )
        return client_id_value
    if settings.allow_legacy_client_id:
        return client_id_from_header(request.headers.get("x-client-id"))
    raise HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        "Authentication required — send a device session token",
    )
