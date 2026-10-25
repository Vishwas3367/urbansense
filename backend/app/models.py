from datetime import datetime, timezone
from uuid import uuid4

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    secret_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    vehicle_id: Mapped[str] = mapped_column(String(80), nullable=False)
    registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    last_sequence: Mapped[int] = mapped_column(Integer, default=0)
    trust_score: Mapped[float] = mapped_column(Float, default=0.8)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class SensorEvent(Base):
    __tablename__ = "sensor_events"
    __table_args__ = (
        UniqueConstraint("device_id", "event_id", name="uq_sensor_event_device_event"),
    )

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: str(uuid4()))
    event_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    device_id: Mapped[str] = mapped_column(ForeignKey("devices.id"), nullable=False, index=True)
    vehicle_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    location: Mapped[object] = mapped_column(Geometry("POINT", srid=4326), nullable=False)
    acceleration_magnitude: Mapped[float] = mapped_column(Float, nullable=False)
    speed_kmh: Mapped[float] = mapped_column(Float, nullable=False)
    gps_accuracy_m: Mapped[float] = mapped_column(Float, nullable=False)
    temperature_c: Mapped[float | None] = mapped_column(Float)
    humidity_percent: Mapped[float | None] = mapped_column(Float)
    rainfall_mm: Mapped[float | None] = mapped_column(Float)
    jerk: Mapped[float | None] = mapped_column(Float)
    sensor_status: Mapped[str] = mapped_column(String(24), nullable=False)
    calibrated: Mapped[bool] = mapped_column(Boolean, nullable=False)
    sensor_quality: Mapped[float] = mapped_column(Float, nullable=False)
    anomaly_evidence: Mapped[float] = mapped_column(Float, nullable=False)
    contextual_evidence: Mapped[float] = mapped_column(Float, nullable=False)
    corroboration: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    risk_score: Mapped[int] = mapped_column(Integer, nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    decision: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    conflict_detected: Mapped[bool] = mapped_column(Boolean, default=False)
    manual_trigger: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    impact_detected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    impact_peak_g: Mapped[float | None] = mapped_column(Float)
    motion_features: Mapped[dict | None] = mapped_column(JSON)
    event_classification: Mapped[str | None] = mapped_column(String(40))
    pothole_confidence: Mapped[float | None] = mapped_column(Float)
    temperature_alert: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    decision_reasons: Mapped[list[str]] = mapped_column(JSON, nullable=False)


class RoadIssue(Base):
    __tablename__ = "road_issues"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: str(uuid4()))
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    issue_type: Mapped[str] = mapped_column(String(40), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="Unresolved")
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    location: Mapped[object] = mapped_column(Geometry("POINT", srid=4326), nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    risk_score: Mapped[int] = mapped_column(Integer, nullable=False)
    detection_count: Mapped[int] = mapped_column(Integer, default=1)
    vehicle_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    vibration: Mapped[float] = mapped_column(Float, nullable=False)


class AuditRecord(Base):
    __tablename__ = "audit_records"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: str(uuid4()))
    actor: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(100), nullable=False)
    details: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
