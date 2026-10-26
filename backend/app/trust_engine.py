from datetime import datetime, timezone
from math import sqrt

from .motion_analysis import classify_road_event


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return min(max(value, low), high)


def temperature_alert_triggered(
    temperature_c: float | None,
    sequence_number: int,
    previous_readings: list[dict],
    threshold_c: float,
    consecutive_readings: int,
) -> bool:
    if temperature_c is None or temperature_c < threshold_c:
        return False

    previous_high_run = 0
    for offset, reading in enumerate(previous_readings, start=1):
        if (
            reading["sequence_number"] != sequence_number - offset
            or reading["temperature_c"] is None
            or reading["temperature_c"] < threshold_c
        ):
            break
        previous_high_run += 1

    return previous_high_run == consecutive_readings - 1


def score_event(
    sample: dict,
    device_trust: float,
    nearby_events: list[dict],
    max_event_age_seconds: int,
    now: datetime | None = None,
) -> dict:
    """Prototype trust/conflict model; weights require calibration against labeled data."""
    now = now or datetime.now(timezone.utc)
    observed_at = sample["timestamp"]
    if observed_at.tzinfo is None:
        observed_at = observed_at.replace(tzinfo=timezone.utc)

    magnitude = sqrt(sample["ax"] ** 2 + sample["ay"] ** 2 + sample["az"] ** 2)
    road_event = None
    if sample.get("motion_features") is not None:
        road_event = classify_road_event(
            sample["motion_features"],
            sample["speed_kmh"],
        )
    anomaly_evidence = clamp(
        0.7 * ((magnitude - 0.65) / 1.2)
        + 0.2 * ((sample.get("jerk") or 0.0) / 2.0)
        + 0.1 * (sample["speed_kmh"] / 80.0)
    )
    gps_quality = 1.0 - clamp(sample["gps_accuracy_m"] / 50.0)
    status_quality = {"NORMAL": 1.0, "DEGRADED": 0.5, "FAULT": 0.0}[sample["sensor_status"]]
    age_seconds = max(0.0, (now - observed_at).total_seconds())
    freshness = 1.0 - clamp(age_seconds / max(max_event_age_seconds, 1))
    sensor_quality = clamp(
        0.45 * gps_quality
        + 0.25 * status_quality
        + 0.2 * float(sample["calibrated"])
        + 0.1 * freshness
    )

    speed_context = 1.0 if 5 <= sample["speed_kmh"] <= 80 else 0.5
    environment_present = any(
        sample.get(key) is not None
        for key in ("temperature_c", "humidity_percent", "rainfall_mm")
    )
    contextual_evidence = clamp(
        0.6 * gps_quality + 0.25 * speed_context + 0.15 * float(environment_present)
    )

    different_vehicle_events = [
        event for event in nearby_events if event["vehicle_id"] != sample["vehicle_id"]
    ]
    corroborating = [
        event
        for event in different_vehicle_events
        if abs(event["anomaly_evidence"] - anomaly_evidence) <= 0.35
    ]
    conflicting = [
        event
        for event in different_vehicle_events
        if abs(event["anomaly_evidence"] - anomaly_evidence) >= 0.55
    ]
    corroboration = clamp(len({event["vehicle_id"] for event in corroborating}) / 2.0)
    conflict_detected = bool(conflicting)

    confidence = clamp(
        0.25 * clamp(device_trust)
        + 0.4 * anomaly_evidence
        + 0.2 * contextual_evidence
        + 0.15 * corroboration
    )

    reasons = []
    if age_seconds > max_event_age_seconds:
        reasons.append("Reading arrived outside the configured freshness window.")
    if not sample["calibrated"]:
        reasons.append("Sensor calibration is not current.")
    if sample["sensor_status"] != "NORMAL":
        reasons.append(f"Sensor reports {sample['sensor_status'].lower()} status.")
    if sample["gps_accuracy_m"] > 15:
        reasons.append("GPS accuracy is too low for a precise road location.")
    if conflict_detected:
        reasons.append("Independent nearby vehicle readings disagree.")
    if corroboration:
        reasons.append("Independent vehicle observations support this event.")

    if sample["sensor_status"] == "FAULT" or device_trust < 0.2:
        decision = "REJECT"
        reasons.append("Device health or trust is below the acceptance floor.")
    elif age_seconds > max_event_age_seconds or conflict_detected:
        decision = "DEFER"
    elif not sample["calibrated"] or sample["sensor_status"] == "DEGRADED" or sample["gps_accuracy_m"] > 15:
        decision = "REQUEST_DATA"
    elif confidence >= 0.7 and anomaly_evidence >= 0.45:
        decision = "ACCEPT"
    elif confidence >= 0.4:
        decision = "REQUEST_DATA"
        reasons.append("More sensor evidence is needed before creating an issue.")
    else:
        decision = "REJECT"
        reasons.append("The reading does not provide sufficient anomaly evidence.")

    if road_event is None:
        if decision == "ACCEPT":
            decision = "REQUEST_DATA"
        reasons.append(
            "Motion features are missing; acceleration-only evidence cannot confirm a pothole candidate."
        )
    else:
        reasons.extend(road_event["evidence"])
        if road_event["classification"] != "POTENTIAL_POTHOLE":
            if road_event["classification"] == "INSUFFICIENT_SPEED":
                if decision == "ACCEPT":
                    decision = "REQUEST_DATA"
                    reasons.append(
                        "A higher-speed sample is required to evaluate a pothole candidate."
                    )
            else:
                if road_event["classification"] in {
                    "BRAKING_LIKE",
                    "SHARP_TURN_LIKE",
                    "ROTATION_DOMINATED",
                    "SPEED_BREAKER_LIKE",
                    "ROUGH_ROAD_LIKE",
                    "NORMAL_OR_UNCLASSIFIED",
                } and decision == "ACCEPT":
                    decision = "REJECT"
                elif decision == "ACCEPT":
                    decision = "REQUEST_DATA"
                reasons.append(
                    "The motion pattern did not meet the prototype pothole-candidate criteria."
                )
        elif road_event["confidence"] < 0.65 and decision == "ACCEPT":
            decision = "REQUEST_DATA"
            reasons.append("Pothole-candidate confidence is below the prototype evidence floor.")

    if sample.get("manual_trigger") and decision == "REJECT" and sample["sensor_status"] != "FAULT" and device_trust >= 0.2:
        decision = "REQUEST_DATA"
        reasons.append(
            "Manual pothole report recorded as a candidate; additional trusted sensor evidence is required."
        )

    risk_score = round(100 * clamp(0.55 * anomaly_evidence + 0.45 * confidence))
    severity = (
        "CRITICAL" if risk_score >= 85 else
        "HIGH" if risk_score >= 70 else
        "MEDIUM" if risk_score >= 50 else
        "LOW"
    )

    return {
        "magnitude": magnitude,
        "sensor_quality": sensor_quality,
        "anomaly_evidence": anomaly_evidence,
        "contextual_evidence": contextual_evidence,
        "corroboration": corroboration,
        "confidence": confidence,
        "risk_score": risk_score,
        "severity": severity,
        "decision": decision,
        "event_classification": (
            road_event["classification"] if road_event is not None else None
        ),
        "pothole_confidence": (
            road_event["confidence"] if road_event is not None else None
        ),
        "conflict_detected": conflict_detected,
        "reasons": reasons or ["Evidence passed the prototype validation thresholds."],
    }


def maintenance_priority(issue: dict) -> dict:
    severity_weight = {"CRITICAL": 100, "HIGH": 75, "MEDIUM": 55, "LOW": 30}
    priority = round(
        min(
            100,
            0.55 * severity_weight[issue["severity"]]
            + 0.3 * issue["confidence"]
            + 0.15 * min(issue["detections"] * 20, 100),
        )
    )
    action = (
        "Immediate inspection and repair" if priority >= 85 else
        "Dispatch maintenance team within 24 hours" if priority >= 70 else
        "Schedule preventive inspection" if priority >= 50 else
        "Continue monitoring"
    )
    return {"priority_score": priority, "recommended_action": action}
