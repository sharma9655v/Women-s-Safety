"""Shared pytest configuration.

The dev admin key is an explicit opt-in (ADMIN_DEV_KEY_ENABLED) since the
security hardening pass; tests that exercise admin endpoints enable it here
so their behaviour does not depend on environment variables.
"""

from __future__ import annotations

from app.config import settings

settings.admin_dev_key_enabled = True
settings.allow_legacy_client_id = True