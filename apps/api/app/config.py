from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="../../.env", extra="ignore")

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/mapforwomen"
    redis_url: str = "redis://localhost:6379/0"
    osrm_base_url: str = "http://localhost:5000"
    weather_api_key: str = ""
    segments_geojson: str = ""
    evidence_seed_json: str = ""
    app_env: str = "development"
    admin_key: str = ""
    report_rate_limit_per_hour: int = 5
    report_duplicate_window_s: int = 86400
    report_max_description_chars: int = 500
    report_encryption_key: str = ""


settings = Settings()
