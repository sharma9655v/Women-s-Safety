from __future__ import annotations

import base64
import io
import re
import secrets
from functools import lru_cache
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from PIL import Image

from app.config import settings

REDACTED = "[redacted]"

EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
URL_PATTERN = re.compile(r"https?://\S+|www\.\S+")
IP_PATTERN = re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")
PHONE_PATTERN = re.compile(r"(?<!\d)(?:\+?\d[\d\s()\-]{6,}\d)(?!\d)")


def redact_description(text: str) -> str:
    """Strip personal identifiers from a free-text report before storage."""
    scrubbed = URL_PATTERN.sub(REDACTED, text)
    scrubbed = EMAIL_PATTERN.sub(REDACTED, scrubbed)
    scrubbed = PHONE_PATTERN.sub(REDACTED, scrubbed)
    scrubbed = IP_PATTERN.sub(REDACTED, scrubbed)
    normalized = " ".join(scrubbed.split())
    return normalized[: settings.report_max_description_chars]


def strip_image_metadata(data: bytes, max_dimension: int = 1280) -> bytes:
    """Re-encode an image, dropping EXIF and other embedded metadata.

    Re-encoding never copies metadata: only the pixel data is written out.
    Raises ValueError for anything Pillow cannot decode.
    """
    try:
        with Image.open(io.BytesIO(data)) as img:
            img.load()
            source_format = img.format
            working = img.convert("RGB") if img.mode not in ("RGB", "L") else img
            if max(working.size) > max_dimension:
                working.thumbnail((max_dimension, max_dimension))
            out = io.BytesIO()
            working.save(out, format="PNG" if source_format == "PNG" else "JPEG")
            return out.getvalue()
    except Exception as exc:
        raise ValueError("Invalid or unsupported image") from exc


def _dev_key() -> bytes:
    """Random per-install key, persisted so restarts keep decryptability.

    Production must set REPORT_ENCRYPTION_KEY; this fallback exists only so
    local development works without configuration. The old deterministic
    derivation is gone: a publicly known key is no security at all.
    """
    path = Path(settings.report_encryption_key_file or ".report_encryption_key")
    try:
        if path.exists():
            stored = path.read_bytes()
            if stored:
                return base64.urlsafe_b64encode(stored)
        key = secrets.token_bytes(32)
        path.write_bytes(key)
        return base64.urlsafe_b64encode(key)
    except OSError:
        return base64.urlsafe_b64encode(secrets.token_bytes(32))


@lru_cache(maxsize=1)
def _fernet() -> Fernet:
    raw = settings.report_encryption_key
    key = raw.encode() if raw else _dev_key()
    return Fernet(key)


def encrypt_blob(data: bytes) -> bytes:
    return _fernet().encrypt(data)


def decrypt_blob(data: bytes) -> bytes:
    try:
        return _fernet().decrypt(data)
    except InvalidToken as exc:
        raise ValueError("Unable to decrypt report data") from exc
