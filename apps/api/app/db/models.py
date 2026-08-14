from __future__ import annotations

from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import JSON, BigInteger, DateTime, Float, LargeBinary, Text, func
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
    updated_at = mapped_column(DateTime(timezone=True), server_default=func.now())
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
