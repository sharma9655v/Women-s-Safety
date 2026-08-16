"""Real Telegram delivery for notification events.

Honest by design: delivery is attempted only when BOTH TELEGRAM_BOT_TOKEN and
TELEGRAM_CHAT_ID are configured (and notify_channel=telegram). Otherwise the
store records status 'no_channel' and the UI says so — never fake delivery.
The send is fire-and-forget with a short timeout: the app never blocks an
emergency flow on a third-party network call."""

from __future__ import annotations

import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_API = "https://api.telegram.org/bot{token}/sendMessage"
_TIMEOUT_S = 5.0


def telegram_configured() -> bool:
    return bool(settings.telegram_bot_token and settings.telegram_chat_id)


def send_telegram(text: str) -> bool:
    """Send one message to the configured chat. Returns True on HTTP 200."""
    if not telegram_configured():
        return False
    try:
        resp = httpx.post(
            _API.format(token=settings.telegram_bot_token),
            json={
                "chat_id": settings.telegram_chat_id,
                "text": text,
                "disable_web_page_preview": True,
            },
            timeout=_TIMEOUT_S,
        )
        if resp.status_code == 200:
            return True
        logger.warning("Telegram send failed: HTTP %s (%s)", resp.status_code, resp.text[:200])
        return False
    except httpx.HTTPError as exc:
        logger.warning("Telegram send error: %s", exc)
        return False
