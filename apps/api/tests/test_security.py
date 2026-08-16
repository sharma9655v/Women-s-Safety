"""Security hardening tests (Groups C and Q).

Covers the CORS allowlist, the spoofable X-Forwarded-For rate-limit key,
the dev admin key opt-in and the report encryption key fallback.
"""

from __future__ import annotations

import hashlib

import pytest
from fastapi import Request
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.reports.limiter import client_key
from app.reports.redact import decrypt_blob, encrypt_blob

client = TestClient(app)


def test_cors_blocks_disallowed_origin() -> None:
    resp = client.get("/health", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in resp.headers


def test_cors_allows_configured_origin() -> None:
    origin = settings.cors_origins.split(",")[0].strip()
    resp = client.get("/health", headers={"Origin": origin})
    assert resp.headers.get("access-control-allow-origin") == origin
    assert resp.headers.get("access-control-allow-credentials") == "true"


def test_cors_preflight_method_is_tight() -> None:
    resp = client.options(
        "/api/routes",
        headers={
            "Origin": settings.cors_origins.split(",")[0].strip(),
            "Access-Control-Request-Method": "PATCH",
        },
    )
    allow = resp.headers.get("access-control-allow-methods", "")
    assert "PATCH" not in allow
    assert "POST" in allow


def test_client_key_ignores_spoofed_forwarded_for_by_default() -> None:
    scope = {
        "type": "http",
        "headers": [(b"x-forwarded-for", b"203.0.113.9")],
        "client": ("10.0.0.5", 12345),
    }
    key = client_key(Request(scope))
    assert key == hashlib.sha256(b"10.0.0.5").hexdigest()[:16]


def test_client_key_uses_forwarded_for_when_trust_proxy_enabled(monkeypatch) -> None:
    monkeypatch.setattr(settings, "trust_proxy", True)
    scope = {
        "type": "http",
        "headers": [(b"x-forwarded-for", b"203.0.113.9, 10.0.0.1")],
        "client": ("10.0.0.5", 12345),
    }
    key = client_key(Request(scope))
    assert key == hashlib.sha256(b"203.0.113.9").hexdigest()[:16]


def test_dev_admin_key_inert_without_opt_in(monkeypatch) -> None:
    monkeypatch.setattr(settings, "admin_dev_key_enabled", False)
    resp = client.get("/api/admin/reports", headers={"X-Admin-Key": "dev-admin-key"})
    assert resp.status_code in (403, 503)


def test_dev_admin_key_works_when_opt_in_enabled() -> None:
    resp = client.get("/api/admin/reports", headers={"X-Admin-Key": "dev-admin-key"})
    assert resp.status_code == 200


def test_encryption_key_fallback_is_random_per_install(tmp_path, monkeypatch) -> None:
    key_file = tmp_path / "key.bin"
    monkeypatch.setattr(settings, "report_encryption_key_file", str(key_file))
    monkeypatch.setattr(settings, "report_encryption_key", "")

    from app.reports import redact

    redact._fernet.cache_clear()
    first = redact._fernet()
    first_key = first._encryption_key
    redact._fernet.cache_clear()
    second = redact._fernet()
    assert first_key == second._encryption_key
    assert key_file.exists()
    assert key_file.read_bytes() != b"map-for-women-dev-encryption-key"


def test_encryption_round_trip_with_fallback_key() -> None:
    plaintext = b"+919876543210"
    assert decrypt_blob(encrypt_blob(plaintext)) == plaintext