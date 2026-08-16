"""Pseudonymous client identity (Phase 9).

All personal safety data is keyed by a device-generated client_id sent in the
X-Client-Id header. The client_id is a random hex string created on-device and
stored in localStorage — it is NOT a real identity, is never tied to an
account, and is never logged in raw form anywhere. A future auth layer can
bind the same tables to a real user without schema changes.

The audit trail stores only a sha256 hash of the id (same pattern as the
admin key), so the raw id cannot be recovered from logs.
"""

from __future__ import annotations

import hashlib
import re

from fastapi import HTTPException, Request, status

_CLIENT_ID_RE = re.compile(r"^[0-9a-fA-F]{32,64}$")

MAX_CLIENT_ID_LEN = 64


def client_id_from_header(x_client_id: str | None = None) -> str:
    """Validate the pseudonymous X-Client-Id header value."""
    if not x_client_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "X-Client-Id header required")
    value = x_client_id.strip().lower()
    if len(value) > MAX_CLIENT_ID_LEN or not _CLIENT_ID_RE.fullmatch(value):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "X-Client-Id must be 32-64 hex characters",
        )
    return value


def client_id(request: Request) -> str:
    return client_id_from_header(request.headers.get("x-client-id"))


def client_hash(client_id_value: str) -> str:
    """Audit-safe hash of a client id (never log the raw id)."""
    return hashlib.sha256(client_id_value.encode()).hexdigest()


__all__ = ["client_id", "client_id_from_header", "client_hash"]
