from __future__ import annotations

from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import (
    JSON,
    UUID,
    BigInteger,
    Boolean,
    DateTime,
    Float,
    Integer,
    LargeBinary,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class RoadSegment(Base):
    __tablename__ = "road_segments"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    osm_way_id: Mapped[int] = mapped_column(BigInteger, index=True)
    geometry: Mapped[object] = mapped_column(
        Geometry(geometry_type="LINESTRING", srid=4326), nullable=False
    )
    road_type: Mapped[str | None] = mapped_column(Text)
    lit: Mapped[str | None] = mapped_column(Text)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    data_source: Mapped[str] = mapped_column(Text, default="osm", nullable=False)
    dataset_version: Mapped[str] = mapped_column(Text, nullable=False)


class Facility(Base):
    __tablename__ = "facilities"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    osm_id: Mapped[int] = mapped_column(BigInteger, index=True)
    type: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str | None] = mapped_column(Text)
    geometry: Mapped[object] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326), nullable=False
    )
    operational_status: Mapped[str | None] = mapped_column(Text)
    distance_m: Mapped[float | None] = mapped_column(Float)
    updated_at = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    dataset_version: Mapped[str] = mapped_column(Text, nullable=False)


class DataSource(Base):
    __tablename__ = "data_sources"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    source_type: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    reliability: Mapped[float] = mapped_column(Float, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)


class SafetyObservation(Base):
    __tablename__ = "safety_observations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    segment_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    source_type: Mapped[str] = mapped_column(Text, nullable=False)
    observation_type: Mapped[str] = mapped_column(Text, nullable=False)
    value_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict, nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ingested_at = mapped_column(DateTime(timezone=True), server_default=func.now())
    source_reliability: Mapped[float] = mapped_column(Float, default=0.6, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    verification_state: Mapped[str] = mapped_column(Text, default="REPORTED", nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    evidence_hash: Mapped[str] = mapped_column(Text, unique=True, nullable=False)


class SafetyObservationHistory(Base):
    __tablename__ = "safety_observation_history"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    observation_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    segment_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    verification_state: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    changed_at = mapped_column(DateTime(timezone=True), server_default=func.now())
    evidence_hash: Mapped[str] = mapped_column(Text, nullable=False)


class SafetyReport(Base):
    __tablename__ = "safety_reports"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    segment_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    category: Mapped[str] = mapped_column(Text, nullable=False)
    description_redacted: Mapped[str | None] = mapped_column(Text)
    reported_at = mapped_column(DateTime(timezone=True), server_default=func.now())
    verification_state: Mapped[str] = mapped_column(Text, default="REPORTED", nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    client_hash: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_image_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())


class JourneyCheckin(Base):
    __tablename__ = "journey_checkins"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    client_id: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="ACTIVE",
    )
    started_at = mapped_column(DateTime(timezone=True), server_default=func.now())
    ended_at = mapped_column(DateTime(timezone=True))
    end_reason: Mapped[str | None] = mapped_column(Text)
    destination_name = mapped_column(Text)
    destination_lat = mapped_column(Float)
    destination_lon = mapped_column(Float)
    expected_arrival_at = mapped_column(DateTime(timezone=True))
    checkin_interval_s = mapped_column(Integer, nullable=False, default=900)
    checkin_grace_s = mapped_column(Integer, nullable=False, default=300)
    last_checkin_at = mapped_column(DateTime(timezone=True))
    next_checkin_at = mapped_column(DateTime(timezone=True))
    contact_ids = mapped_column(JSON, nullable=False, default=list)
    escalation_stage = mapped_column(Integer, nullable=False, default=0)
    notified_stage = mapped_column(Integer, nullable=False, default=0)
    latitude = mapped_column(Float, nullable=True)
    longitude = mapped_column(Float, nullable=True)
    last_known_at = mapped_column(DateTime(timezone=True))


class SafetyAlert(Base):
    __tablename__ = "safety_alerts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    category: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    severity: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="moderate",
    )
    lat = mapped_column(Float, nullable=False)
    lon = mapped_column(Float, nullable=False)
    location_name = mapped_column(Text)
    description = mapped_column(Text)
    source = mapped_column(Text, nullable=False)
    evidence_status = mapped_column(
        Text,
        nullable=False,
        default="verified",
    )
    confidence = mapped_column(Float, nullable=False, default=0.5)
    observed_at = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at = mapped_column(DateTime(timezone=True))
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())


class SafetyPreferences(Base):
    __tablename__ = "safety_preferences"

    client_id: Mapped[str] = mapped_column(Text, primary_key=True)
    prefer_better_lit = mapped_column(Boolean, nullable=False, default=True)
    prefer_main_roads = mapped_column(Boolean, nullable=False, default=True)
    prefer_near_emergency = mapped_column(Boolean, nullable=False, default=True)
    avoid_known_hazards = mapped_column(Boolean, nullable=False, default=True)
    avoid_isolated_roads = mapped_column(Boolean, nullable=False, default=False)
    minimize_walking_time = mapped_column(Boolean, nullable=False, default=False)
    default_profile = mapped_column(
        Text,
        nullable=False,
        default="balanced",
    )
    discreet_mode_enabled = mapped_column(Boolean, nullable=False, default=False)
    voice_guidance_enabled = mapped_column(Boolean, nullable=False, default=True)
    voice_language = mapped_column(Text, nullable=False, default="en")
    updated_at = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class DiscreetModeSettings(Base):
    __tablename__ = "discreet_mode_settings"

    client_id: Mapped[str] = mapped_column(Text, primary_key=True)
    enabled = mapped_column(Boolean, nullable=False, default=False)
    quick_sos_gesture = mapped_column(Text, nullable=False, default="triple_tap")
    exit_to_neutral_app = mapped_column(Boolean, nullable=False, default=True)
    neutral_app_label = mapped_column(Text, nullable=False, default="Weather")
    neutral_app_icon = mapped_column(Text, nullable=False, default="cloud-sun")
    updated_at = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class FakeCallSession(Base):
    __tablename__ = "fake_call_sessions"

    id: Mapped[int] = mapped_column(UUID, primary_key=True)
    client_id: Mapped[str] = mapped_column(Text, nullable=False)
    caller_name = mapped_column(Text, nullable=False, default="Unknown")
    caller_number = mapped_column(Text)
    scheduled_at = mapped_column(DateTime(timezone=True), nullable=False)
    triggered_at = mapped_column(DateTime(timezone=True))
    status = mapped_column(
        Text,
        nullable=False,
        default="SCHEDULED",
    )
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())


class VoiceGuidanceSession(Base):
    __tablename__ = "voice_guidance_sessions"

    id: Mapped[int] = mapped_column(UUID, primary_key=True)
    client_id: Mapped[str] = mapped_column(Text, nullable=False)
    route_session_id = mapped_column(UUID)
    language = mapped_column(Text, nullable=False, default="en")
    active = mapped_column(Boolean, nullable=False, default=True)
    started_at = mapped_column(DateTime(timezone=True), server_default=func.now())
    ended_at = mapped_column(DateTime(timezone=True))


class DeviceSession(Base):
    __tablename__ = "device_sessions"

    token_hash: Mapped[str] = mapped_column(Text, primary_key=True)
    client_id: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    expires_at = mapped_column(DateTime(timezone=True), nullable=False)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())
