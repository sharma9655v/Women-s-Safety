from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="../../.env", extra="ignore")

    database_url: str = ""
    redis_url: str = ""
    osrm_base_url: str = "http://localhost:5000"
    weather_api_key: str = ""
    segments_geojson: str = ""
    evidence_seed_json: str = ""
    app_env: str = "development"
    admin_key: str = ""
    # Explicit opt-in for the well-known dev admin key. Production must set
    # ADMIN_KEY instead; leaving this off keeps "dev-admin-key" inert even
    # if APP_ENV is accidentally left as "development".
    admin_dev_key_enabled: bool = False
    # Trust X-Forwarded-For for rate limiting. Enable ONLY when the app sits
    # behind a reverse proxy that overwrites the header; otherwise clients
    # can spoof it to bypass per-client limits.
    trust_proxy: bool = False
    # Accept the raw X-Client-Id header on private endpoints (dev/test
    # compatibility). Production must keep this off: the header is
    # self-asserted and cannot be trusted on its own.
    allow_legacy_client_id: bool = False
    device_session_ttl_days: int = 30
    cors_origins: str = "http://localhost:3000"
    cors_methods: str = "GET,POST,PUT,DELETE,OPTIONS"
    cors_headers: str = "Content-Type,X-Client-Id,X-Admin-Key,Authorization"
    report_rate_limit_per_hour: int = 5
    route_rate_limit_per_minute: int = 30
    report_duplicate_window_s: int = 86400
    report_max_description_chars: int = 500
    report_encryption_key: str = ""
    # Path where a random per-install encryption key is persisted when
    # REPORT_ENCRYPTION_KEY is not set (development fallback). The file must
    # never be committed or shipped.
    report_encryption_key_file: str = ".report_encryption_key"
    emergency_countdown_default_s: int = 5
    emergency_rate_limit_per_hour: int = 10
    location_sharing_max_ttl_s: int = 3600
    guardian_max_duration_s: int = 86400
    checkin_grace_default_s: int = 300
    guardian_escalation_delay_s: int = 900
    guardian_deviation_threshold_m: float = 200.0
    guardian_auto_sos: bool = False
    notify_channel: str = "none"
    # Real Telegram delivery (see app/notify/telegram.py). Both must be set
    # AND notify_channel=telegram before any message is attempted; otherwise
    # events keep the honest status "no_channel".
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    # Computer-vision inference backend. "mock" serves a clearly-labelled
    # development implementation that never pretends to be real ML inference;
    # "disabled" turns the CV API off entirely (503). A real model backend
    # replaces the mock behind the same interface once the ML pipeline
    # produces a validated checkpoint.
    cv_backend: str = "mock"
    # Directory holding CV checkpoints (models/ by default). Used for startup
    # validation and metadata reporting.
    cv_model_dir: str = "models"
    # Upper bound for a single CV inference call (seconds).
    cv_inference_timeout_s: float = 10.0
    # Optional real backend module path (e.g. "app.cv.keras_impl") that will be
    # imported when CV_BACKEND=real. Empty means "real backend not deployed".
    cv_real_backend_module: str = ""


settings = Settings()
