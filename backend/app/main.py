import hmac
import secrets
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from geoalchemy2 import Geography, WKTElement
from sqlalchemy import Numeric, cast, func, or_, select
from sqlalchemy.orm import Session

from .config import get_settings
from .database import get_db
from .models import AuditRecord, Device, RoadIssue, SensorEvent, utc_now
from .schemas import (
    DeviceRegistration,
    DeviceRegistrationResult,
    DashboardLogin,
    IngestionResult,
    IssueResult,
    SensorReading,
)
from .security import (
    decrypt_device_secret,
    encrypt_device_secret,
    get_raw_request_body,
    issue_dashboard_token,
    require_dashboard_user,
    verify_device_signature,
)
from .trust_engine import maintenance_priority, score_event, temperature_alert_triggered

app = FastAPI(
    title="UrbanSense Trust-Aware Sensor API",
    description="Prototype authenticated ingestion, sensor trust, event fusion, and maintenance prioritization.",
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type", "X-Device-ID", "X-Device-Signature", "X-Admin-Token"],
)


def make_point(latitude: float, longitude: float) -> WKTElement:
    return WKTElement(f"POINT({longitude} {latitude})", srid=4326)


def to_issue_result(issue: RoadIssue) -> IssueResult:
    priority = maintenance_priority(
        {
            "severity": issue.severity,
            "confidence": round(issue.confidence * 100),
            "detections": issue.detection_count,
        }
    )
    return IssueResult(
        id=issue.id,
        title=issue.title,
        type=issue.issue_type,
        severity=issue.severity,
        confidence=round(issue.confidence * 100),
        riskScore=issue.risk_score,
        detections=issue.detection_count,
        vehicles=issue.vehicle_ids,
        location=f"{issue.latitude:.5f}, {issue.longitude:.5f}",
        lat=issue.latitude,
        lng=issue.longitude,
        status=issue.status,
        time=issue.last_seen_at.astimezone().strftime("%I:%M %p").lstrip("0"),
        vibration=round(issue.vibration, 2),
        priorityScore=priority["priority_score"],
        recommendedAction=priority["recommended_action"],
    )


def add_audit(
    db: Session,
    actor: str,
    action: str,
    entity_id: str,
    details: dict,
) -> None:
    db.add(AuditRecord(actor=actor, action=action, entity_id=entity_id, details=details))


@app.get("/health")
def health():
    return {"status": "ok", "service": "UrbanSense trust-aware API"}


@app.post("/api/auth/login")
def login(payload: DashboardLogin):
    settings = get_settings()
    if not settings.dashboard_email or not settings.dashboard_password or not settings.jwt_secret:
        raise HTTPException(status_code=503, detail="Dashboard credentials are not configured.")
    if not (
        hmac.compare_digest(payload.email.encode(), settings.dashboard_email.encode())
        and hmac.compare_digest(payload.password.encode(), settings.dashboard_password.encode())
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")
    return {"access_token": issue_dashboard_token(payload.email), "token_type": "bearer"}


@app.post("/api/devices", response_model=DeviceRegistrationResult, status_code=201)
def register_device(
    payload: DeviceRegistration,
    db: Session = Depends(get_db),
    admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
):
    settings = get_settings()
    if not settings.us_admin_token:
        raise HTTPException(status_code=503, detail="Device registration is not configured.")
    if not admin_token or not hmac.compare_digest(admin_token, settings.us_admin_token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin token is required.")
    if db.get(Device, payload.device_id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Device ID is already registered.")

    device_secret = secrets.token_urlsafe(32)
    device = Device(
        id=payload.device_id,
        vehicle_id=payload.vehicle_id,
        secret_encrypted=encrypt_device_secret(device_secret),
    )
    db.add(device)
    add_audit(
        db,
        actor="admin",
        action="device.registered",
        entity_id=payload.device_id,
        details={"vehicle_id": payload.vehicle_id},
    )
    db.commit()
    return DeviceRegistrationResult(
        device_id=device.id,
        vehicle_id=device.vehicle_id,
        device_secret=device_secret,
        message="Store this secret securely; it is shown only once.",
    )


@app.post("/api/readings", response_model=IngestionResult, status_code=201)
def ingest_reading(
    reading: SensorReading,
    db: Session = Depends(get_db),
    device_id: str | None = Header(default=None, alias="X-Device-ID"),
    signature: str | None = Header(default=None, alias="X-Device-Signature"),
    raw_body: bytes = Depends(get_raw_request_body),
):
    if not device_id or not signature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-Device-ID and X-Device-Signature are required.",
        )
    device = db.scalar(select(Device).where(Device.id == device_id).with_for_update())
    if not device or not device.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Device is not registered or active.")

    secret = decrypt_device_secret(device.secret_encrypted)
    if not verify_device_signature(raw_body, secret, signature):
        add_audit(
            db,
            actor=device_id,
            action="reading.authentication_failed",
            entity_id=reading.event_id,
            details={},
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid device signature.")

    if db.scalar(
        select(SensorEvent).where(
            SensorEvent.device_id == device_id,
            SensorEvent.event_id == reading.event_id,
        )
    ):
        add_audit(
            db,
            actor=device_id,
            action="reading.duplicate_rejected",
            entity_id=reading.event_id,
            details={"sequence_number": reading.sequence_number},
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Event ID has already been received.")
    if reading.sequence_number <= device.last_sequence:
        add_audit(
            db,
            actor=device_id,
            action="reading.replay_rejected",
            entity_id=reading.event_id,
            details={"sequence_number": reading.sequence_number, "last_sequence": device.last_sequence},
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Sequence number is not newer than the last reading.")

    now = utc_now()
    observed_at = reading.timestamp
    if observed_at.tzinfo is None:
        observed_at = observed_at.replace(tzinfo=timezone.utc)
    future_limit = now + timedelta(seconds=get_settings().future_clock_skew_seconds)
    if observed_at > future_limit:
        raise HTTPException(status_code=422, detail="Reading timestamp is too far in the future.")

    nearby_point = func.ST_SetSRID(func.ST_MakePoint(reading.longitude, reading.latitude), 4326)
    nearby_query = (
        select(SensorEvent)
        .where(
            SensorEvent.observed_at >= observed_at - timedelta(seconds=90),
            SensorEvent.observed_at <= observed_at + timedelta(seconds=90),
            SensorEvent.decision == "ACCEPT",
            func.ST_DWithin(
                cast(SensorEvent.location, Geography(srid=4326)),
                cast(nearby_point, Geography(srid=4326)),
                25.0,
            ),
        )
        .order_by(SensorEvent.observed_at.desc())
        .limit(100)
    )
    nearby_events = db.scalars(nearby_query).all()
    sample = reading.model_dump()
    sample["vehicle_id"] = device.vehicle_id
    analysis = score_event(
        sample,
        device.trust_score,
        [
            {
                "vehicle_id": event.vehicle_id,
                "anomaly_evidence": event.anomaly_evidence,
            }
            for event in nearby_events
        ],
        get_settings().max_event_age_seconds,
        now=now,
    )
    settings = get_settings()
    temperature_history = db.scalars(
        select(SensorEvent)
        .where(
            SensorEvent.device_id == device.id,
            SensorEvent.sequence_number < reading.sequence_number,
        )
        .order_by(SensorEvent.sequence_number.desc())
        .limit(settings.high_temperature_consecutive_readings)
    ).all()
    is_temperature_alert = temperature_alert_triggered(
        reading.temperature_c,
        reading.sequence_number,
        [
            {
                "sequence_number": event.sequence_number,
                "temperature_c": event.temperature_c,
            }
            for event in temperature_history
        ],
        settings.high_temperature_threshold_c,
        settings.high_temperature_consecutive_readings,
    )

    event = SensorEvent(
        event_id=reading.event_id,
        device_id=device.id,
        vehicle_id=device.vehicle_id,
        sequence_number=reading.sequence_number,
        observed_at=observed_at,
        latitude=reading.latitude,
        longitude=reading.longitude,
        location=make_point(reading.latitude, reading.longitude),
        acceleration_magnitude=analysis["magnitude"],
        speed_kmh=reading.speed_kmh,
        gps_accuracy_m=reading.gps_accuracy_m,
        temperature_c=reading.temperature_c,
        humidity_percent=reading.humidity_percent,
        rainfall_mm=reading.rainfall_mm,
        jerk=reading.jerk,
        sensor_status=reading.sensor_status,
        calibrated=reading.calibrated,
        sensor_quality=analysis["sensor_quality"],
        anomaly_evidence=analysis["anomaly_evidence"],
        contextual_evidence=analysis["contextual_evidence"],
        corroboration=analysis["corroboration"],
        confidence=analysis["confidence"],
        risk_score=analysis["risk_score"],
        severity=analysis["severity"],
        decision=analysis["decision"],
        conflict_detected=analysis["conflict_detected"],
        manual_trigger=reading.manual_trigger,
        impact_detected=reading.impact_detected,
        impact_peak_g=reading.impact_peak_g,
        motion_features=(
            reading.motion_features.model_dump()
            if reading.motion_features is not None
            else None
        ),
        event_classification=analysis["event_classification"],
        pothole_confidence=analysis["pothole_confidence"],
        temperature_alert=is_temperature_alert,
        decision_reasons=analysis["reasons"],
    )
    db.add(event)
    device.last_sequence = reading.sequence_number
    observed_reliability = analysis["sensor_quality"]
    if analysis["conflict_detected"]:
        observed_reliability *= 0.5
    elif analysis["corroboration"] > 0:
        observed_reliability = min(1.0, observed_reliability + 0.1)
    device.trust_score = round(0.95 * device.trust_score + 0.05 * observed_reliability, 4)

    issue_result = None
    if analysis["decision"] == "ACCEPT":
        issue_point = func.ST_SetSRID(func.ST_MakePoint(reading.longitude, reading.latitude), 4326)
        existing_issue = db.scalar(
            select(RoadIssue)
            .where(
                RoadIssue.status != "Resolved",
                func.ST_DWithin(
                    cast(RoadIssue.location, Geography(srid=4326)),
                    cast(issue_point, Geography(srid=4326)),
                    25.0,
                ),
            )
            .order_by(RoadIssue.last_seen_at.desc())
            .limit(1)
            .with_for_update()
        )
        vehicle_ids = list(dict.fromkeys(
            (existing_issue.vehicle_ids if existing_issue else []) + [device.vehicle_id]
        ))
        if existing_issue:
            existing_issue.latitude = (
                existing_issue.latitude * existing_issue.detection_count + reading.latitude
            ) / (existing_issue.detection_count + 1)
            existing_issue.longitude = (
                existing_issue.longitude * existing_issue.detection_count + reading.longitude
            ) / (existing_issue.detection_count + 1)
            existing_issue.location = make_point(existing_issue.latitude, existing_issue.longitude)
            existing_issue.detection_count += 1
            existing_issue.vehicle_ids = vehicle_ids
            existing_issue.last_seen_at = now
            existing_issue.confidence = max(existing_issue.confidence, analysis["confidence"])
            existing_issue.risk_score = max(existing_issue.risk_score, analysis["risk_score"])
            existing_issue.severity = max(
                (existing_issue.severity, analysis["severity"]),
                key=lambda severity: ["LOW", "MEDIUM", "HIGH", "CRITICAL"].index(severity),
            )
            existing_issue.vibration = max(existing_issue.vibration, analysis["magnitude"])
            issue = existing_issue
        else:
            title = (
                "Pothole / Road Surface Abnormality"
                if analysis["severity"] == "CRITICAL"
                else "Road Surface Anomaly"
                if analysis["severity"] == "HIGH"
                else "Abnormal Vibration"
            )
            issue = RoadIssue(
                id=f"ISS-{uuid4().hex[:10].upper()}",
                title=title,
                issue_type="Road Surface" if analysis["severity"] in {"CRITICAL", "HIGH"} else "Vibration",
                severity=analysis["severity"],
                latitude=reading.latitude,
                longitude=reading.longitude,
                location=make_point(reading.latitude, reading.longitude),
                first_seen_at=now,
                last_seen_at=now,
                confidence=analysis["confidence"],
                risk_score=analysis["risk_score"],
                detection_count=1,
                vehicle_ids=vehicle_ids,
                vibration=analysis["magnitude"],
            )
            db.add(issue)
        db.flush()
        issue_result = to_issue_result(issue)

    add_audit(
        db,
        actor=device_id,
        action="reading.processed",
        entity_id=reading.event_id,
        details={
            "decision": analysis["decision"],
            "confidence": round(analysis["confidence"] * 100),
            "conflict_detected": analysis["conflict_detected"],
            "manual_trigger": reading.manual_trigger,
            "temperature_alert": is_temperature_alert,
            "event_classification": analysis["event_classification"],
            "pothole_confidence": analysis["pothole_confidence"],
            "issue_id": issue_result.id if issue_result else None,
        },
    )
    db.commit()
    return IngestionResult(
        event_id=reading.event_id,
        decision=analysis["decision"],
        confidence=round(analysis["confidence"] * 100),
        risk_score=analysis["risk_score"],
        severity=analysis["severity"],
        conflict_detected=analysis["conflict_detected"],
        reasons=analysis["reasons"],
        event_classification=analysis["event_classification"],
        pothole_confidence=(
            round(100 * analysis["pothole_confidence"])
            if analysis["pothole_confidence"] is not None
            else None
        ),
        issue=issue_result,
    )


@app.get("/api/issues", response_model=list[IssueResult])
def list_issues(
    _: str = Depends(require_dashboard_user),
    db: Session = Depends(get_db),
):
    issues = db.scalars(select(RoadIssue).order_by(RoadIssue.last_seen_at.desc())).all()
    return [to_issue_result(issue) for issue in issues]


@app.get("/api/maintenance", response_model=list[IssueResult])
def list_maintenance(
    _: str = Depends(require_dashboard_user),
    db: Session = Depends(get_db),
):
    issues = db.scalars(select(RoadIssue).where(RoadIssue.status != "Resolved")).all()
    results = [to_issue_result(issue) for issue in issues]
    return sorted(results, key=lambda issue: issue.priorityScore, reverse=True)


@app.get("/api/alerts")
def list_alerts(
    _: str = Depends(require_dashboard_user),
    db: Session = Depends(get_db),
):
    events = db.scalars(
        select(SensorEvent)
        .where(
            or_(
                SensorEvent.decision == "ACCEPT",
                SensorEvent.manual_trigger.is_(True),
                SensorEvent.impact_detected.is_(True),
                SensorEvent.temperature_alert.is_(True),
                SensorEvent.event_classification == "POTENTIAL_POTHOLE",
            )
        )
        .order_by(SensorEvent.received_at.desc())
        .limit(10)
    ).all()
    alerts = []
    for event in events:
        location = f"{event.latitude:.5f}, {event.longitude:.5f}"
        time = event.received_at.astimezone().strftime("%I:%M %p").lstrip("0")
        common = {
            "location": location,
            "time": time,
            "decision": event.decision,
            "severity": event.severity,
            "confidence": round(event.confidence * 100),
            "temperature_c": event.temperature_c,
            "humidity_percent": event.humidity_percent,
            "vehicle_id": event.vehicle_id,
            "event_classification": event.event_classification,
            "pothole_confidence": (
                round(100 * event.pothole_confidence)
                if event.pothole_confidence is not None
                else None
            ),
        }
        if event.temperature_alert:
            alerts.append(
                {
                    **common,
                    "id": f"{event.event_id}-temperature",
                    "alert_type": "HIGH_TEMPERATURE",
                    "title": "High ambient temperature",
                }
            )
        if event.manual_trigger:
            alerts.append(
                {
                    **common,
                    "id": f"{event.event_id}-manual",
                    "alert_type": "MANUAL_SIGNAL",
                    "title": "Manual pothole signal",
                }
            )
        if event.impact_detected:
            alerts.append(
                {
                    **common,
                    "id": f"{event.event_id}-impact",
                    "alert_type": "POTENTIAL_IMPACT",
                    "title": "Potential road impact",
                    "impact_peak_g": event.impact_peak_g,
                }
            )
        if event.event_classification == "POTENTIAL_POTHOLE":
            alerts.append(
                {
                    **common,
                    "id": f"{event.event_id}-pothole",
                    "alert_type": "POTENTIAL_POTHOLE",
                    "title": "Potential pothole pattern",
                }
            )
        if event.decision == "ACCEPT":
            alerts.append(
                {
                    **common,
                    "id": event.event_id,
                    "alert_type": "SENSOR_DECISION",
                    "title": f"{event.severity.title()} road anomaly",
                }
            )
    return alerts


@app.get("/api/events")
def list_events(
    _: str = Depends(require_dashboard_user),
    db: Session = Depends(get_db),
):
    events = db.scalars(
        select(SensorEvent).order_by(SensorEvent.received_at.desc()).limit(50)
    ).all()
    return [
        {
            "event_id": event.event_id,
            "vehicle_id": event.vehicle_id,
            "decision": event.decision,
            "severity": event.severity,
            "confidence": round(event.confidence * 100),
            "location": f"{event.latitude:.5f}, {event.longitude:.5f}",
            "received_at": event.received_at.isoformat(),
            "reasons": event.decision_reasons,
            "temperature_c": event.temperature_c,
            "humidity_percent": event.humidity_percent,
            "manual_trigger": event.manual_trigger,
            "impact_detected": event.impact_detected,
            "impact_peak_g": event.impact_peak_g,
            "motion_features": event.motion_features,
            "event_classification": event.event_classification,
            "pothole_confidence": (
                round(100 * event.pothole_confidence)
                if event.pothole_confidence is not None
                else None
            ),
            "temperature_alert": event.temperature_alert,
        }
        for event in events
    ]


@app.get("/api/vehicles")
def list_vehicles(
    _: str = Depends(require_dashboard_user),
    db: Session = Depends(get_db),
):
    devices = db.scalars(select(Device).where(Device.is_active.is_(True))).all()
    results = []
    now = utc_now()
    for device in devices:
        latest = db.scalar(
            select(SensorEvent)
            .where(SensorEvent.device_id == device.id)
            .order_by(SensorEvent.observed_at.desc())
            .limit(1)
        )
        if not latest:
            results.append(
                {
                    "id": device.vehicle_id,
                    "type": "Mobile IoT Unit",
                    "status": "Offline",
                    "zone": "Unassigned",
                    "speed": 0,
                    "sensors": 1,
                    "lat": 0,
                    "lng": 0,
                    "distance": 0,
                    "segments": 0,
                    "observations": 0,
                    "anomalies": 0,
                    "trust": round(device.trust_score * 100),
                    "temperature_c": None,
                    "humidity_percent": None,
                }
            )
            continue
        last_observed = latest.observed_at
        if last_observed.tzinfo is None:
            last_observed = last_observed.replace(tzinfo=timezone.utc)
        count = db.scalar(
            select(func.count())
            .select_from(SensorEvent)
            .where(SensorEvent.device_id == device.id)
        )
        anomaly_count = db.scalar(
            select(func.count())
            .select_from(SensorEvent)
            .where(SensorEvent.device_id == device.id, SensorEvent.decision == "ACCEPT")
        )
        results.append(
            {
                "id": device.vehicle_id,
                "type": "Mobile IoT Unit",
                "status": "Active" if (now - last_observed).total_seconds() < 300 else "Offline",
                "zone": f"{latest.latitude:.3f}, {latest.longitude:.3f}",
                "speed": round(latest.speed_kmh),
                "sensors": 1,
                "lat": latest.latitude,
                "lng": latest.longitude,
                "distance": 0,
                "segments": 0,
                "observations": count or 0,
                "anomalies": anomaly_count or 0,
                "trust": round(device.trust_score * 100),
                "temperature_c": latest.temperature_c,
                "humidity_percent": latest.humidity_percent,
            }
        )
    return results


@app.get("/api/summary")
def get_summary(
    _: str = Depends(require_dashboard_user),
    db: Session = Depends(get_db),
):
    devices = db.scalars(select(Device).where(Device.is_active.is_(True))).all()
    issues = db.scalars(select(RoadIssue).where(RoadIssue.status != "Resolved")).all()
    active_cutoff = utc_now() - timedelta(minutes=5)
    active_device_ids = set(
        db.scalars(
            select(SensorEvent.device_id)
            .where(SensorEvent.observed_at >= active_cutoff)
            .distinct()
        ).all()
    )
    segment_bins = (
        select(
            func.round(cast(SensorEvent.latitude, Numeric), 3),
            func.round(cast(SensorEvent.longitude, Numeric), 3),
        )
        .where(SensorEvent.observed_at >= utc_now() - timedelta(hours=24))
        .distinct()
        .subquery()
    )
    segment_count = db.scalar(select(func.count()).select_from(segment_bins)) or 0
    event_count = db.scalar(select(func.count()).select_from(SensorEvent)) or 0
    average_quality = db.scalar(select(func.avg(SensorEvent.sensor_quality))) or 0
    accepted_readings = (
        db.scalar(
            select(func.count())
            .select_from(SensorEvent)
            .where(SensorEvent.decision == "ACCEPT")
        )
        or 0
    )
    return {
        "active_units": len(active_device_ids),
        "registered_units": len(devices),
        "segments_covered": segment_count,
        "issues": len(issues),
        "critical_issues": sum(issue.severity == "CRITICAL" for issue in issues),
        "new_issues": sum(issue.first_seen_at >= active_cutoff for issue in issues),
        "average_sensor_trust": round(
            sum(device.trust_score for device in devices) / len(devices) * 100
        ) if devices else 0,
        "average_reading_quality": round(average_quality * 100),
        "accepted_readings_pct": round(accepted_readings / event_count * 100) if event_count else 0,
    }


@app.get("/api/audit")
def list_audit_records(
    _: str = Depends(require_dashboard_user),
    db: Session = Depends(get_db),
):
    records = db.scalars(
        select(AuditRecord).order_by(AuditRecord.created_at.desc()).limit(200)
    ).all()
    return [
        {
            "id": record.id,
            "actor": record.actor,
            "action": record.action,
            "entity_id": record.entity_id,
            "details": record.details,
            "created_at": record.created_at.isoformat(),
        }
        for record in records
    ]
