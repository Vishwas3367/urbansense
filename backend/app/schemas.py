from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class DeviceRegistration(BaseModel):
    device_id: str = Field(min_length=3, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")
    vehicle_id: str = Field(min_length=1, max_length=80)


class DeviceRegistrationResult(BaseModel):
    device_id: str
    vehicle_id: str
    device_secret: str
    message: str


class DashboardLogin(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=256)


class MotionFeatures(BaseModel):
    vertical_peak_g: float = Field(ge=0, le=32)
    vertical_rms_g: float = Field(ge=0, le=32)
    dynamic_rms_g: float = Field(ge=0, le=56)
    acceleration_peak_g: float = Field(ge=0, le=56)
    jerk_peak_g_s: float = Field(ge=0, le=10_000)
    gyro_peak_dps: float = Field(ge=0, le=2000)
    yaw_peak_dps: float = Field(ge=0, le=2000)
    impact_duration_ms: int = Field(ge=0, le=10_000)
    vertical_peak_count: int = Field(ge=0, le=1000)
    biphasic: bool
    longitudinal_peak_g: float = Field(ge=0, le=32)
    lateral_peak_g: float = Field(ge=0, le=32)


class SensorReading(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(min_length=8, max_length=100, pattern=r"^[A-Za-z0-9_-]+$")
    sequence_number: int = Field(gt=0, le=2_147_483_647)
    timestamp: datetime
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    ax: float = Field(ge=-32, le=32, description="Longitudinal acceleration in g.")
    ay: float = Field(ge=-32, le=32, description="Lateral acceleration in g.")
    az: float = Field(ge=-32, le=32, description="Vertical acceleration in g.")
    speed_kmh: float = Field(ge=0, le=250, description="Vehicle speed in km/h.")
    gps_accuracy_m: float = Field(ge=0, le=1000, description="Reported horizontal GPS accuracy in meters.")
    temperature_c: float | None = Field(default=None, ge=-50, le=100)
    humidity_percent: float | None = Field(default=None, ge=0, le=100)
    rainfall_mm: float | None = Field(default=None, ge=0, le=500)
    jerk: float | None = Field(default=None, ge=0, le=100)
    manual_trigger: bool = False
    impact_detected: bool = False
    impact_peak_g: float | None = Field(
        default=None,
        ge=0,
        le=32,
        description="Peak absolute vertical dynamic acceleration for a potential impact, in g.",
    )
    motion_features: MotionFeatures | None = None
    sensor_status: Literal["NORMAL", "DEGRADED", "FAULT"] = "NORMAL"
    calibrated: bool = True


class IssueResult(BaseModel):
    id: str
    title: str
    type: str
    severity: str
    confidence: int
    riskScore: int
    detections: int
    vehicles: list[str]
    location: str
    lat: float
    lng: float
    status: str
    time: str
    vibration: float
    priorityScore: int
    recommendedAction: str


class IngestionResult(BaseModel):
    event_id: str
    decision: str
    confidence: int
    risk_score: int
    severity: str
    conflict_detected: bool
    reasons: list[str]
    event_classification: str | None = None
    pothole_confidence: int | None = None
    issue: IssueResult | None = None
