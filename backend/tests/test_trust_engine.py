from datetime import datetime, timedelta, timezone

from app.trust_engine import (
    maintenance_priority,
    score_event,
    temperature_alert_triggered,
)


def reading(**overrides):
    sample = {
        "timestamp": datetime.now(timezone.utc),
        "vehicle_id": "BUS-001",
        "ax": 0.1,
        "ay": 0.1,
        "az": 2.0,
        "speed_kmh": 30,
        "gps_accuracy_m": 4,
        "temperature_c": 31,
        "humidity_percent": 60,
        "rainfall_mm": 0,
        "jerk": 1.5,
        "sensor_status": "NORMAL",
        "calibrated": True,
    }
    sample.update(overrides)
    return sample


def evaluate(sample=None, trust=0.8, nearby=None, now=None):
    return score_event(
        sample or reading(),
        trust,
        nearby or [],
        max_event_age_seconds=900,
        now=now,
    )


def pothole_motion_features():
    return {
        "vertical_peak_g": 0.9,
        "vertical_rms_g": 0.12,
        "dynamic_rms_g": 0.13,
        "acceleration_peak_g": 0.9,
        "jerk_peak_g_s": 10.0,
        "gyro_peak_dps": 10.0,
        "yaw_peak_dps": 5.0,
        "impact_duration_ms": 60,
        "vertical_peak_count": 1,
        "biphasic": True,
        "longitudinal_peak_g": 0.1,
        "lateral_peak_g": 0.1,
    }


def test_reliable_high_signal_is_accepted():
    result = evaluate(reading(motion_features=pothole_motion_features()))
    assert result["decision"] == "ACCEPT"
    assert result["confidence"] >= 0.7
    assert result["risk_score"] > 0


def test_acceleration_only_high_signal_requests_motion_features():
    result = evaluate()
    assert result["decision"] == "REQUEST_DATA"
    assert "acceleration-only" in " ".join(result["reasons"])


def test_faulty_sensor_is_rejected():
    result = evaluate(reading(sensor_status="FAULT"))
    assert result["decision"] == "REJECT"
    assert "fault" in " ".join(result["reasons"]).lower()


def test_conflicting_independent_reading_is_deferred():
    sample = reading()
    baseline_accepts = (sample["ax"] ** 2 + sample["ay"] ** 2 + sample["az"] ** 2) ** 0.5 >= 1.2
    result = evaluate(sample, nearby=[{"vehicle_id": "BUS-002", "anomaly_evidence": 0.05}])
    assert baseline_accepts is True
    assert result["conflict_detected"] is True
    assert result["decision"] == "DEFER"


def test_repeated_independent_evidence_increases_corroboration():
    lone = evaluate()
    corroborated = evaluate(
        nearby=[
            {"vehicle_id": "BUS-002", "anomaly_evidence": 0.8},
            {"vehicle_id": "BUS-003", "anomaly_evidence": 0.85},
        ]
    )
    assert corroborated["corroboration"] == 1
    assert corroborated["confidence"] > lone["confidence"]


def test_stale_event_is_deferred_for_review():
    now = datetime.now(timezone.utc)
    stale = reading(timestamp=now - timedelta(minutes=30))
    result = evaluate(stale, now=now)
    assert result["decision"] == "DEFER"
    assert "freshness" in " ".join(result["reasons"])


def test_unreliable_gps_requests_more_data():
    result = evaluate(reading(gps_accuracy_m=80))
    assert result["decision"] == "REQUEST_DATA"
    assert result["sensor_quality"] < 0.6


def test_maintenance_priority_orders_critical_issues_higher():
    critical = maintenance_priority(
        {"severity": "CRITICAL", "confidence": 95, "detections": 3}
    )
    medium = maintenance_priority(
        {"severity": "MEDIUM", "confidence": 60, "detections": 1}
    )
    assert critical["priority_score"] > medium["priority_score"]
    assert critical["recommended_action"] == "Immediate inspection and repair"


def test_high_temperature_alert_triggers_once_after_consecutive_samples():
    previous = [{"sequence_number": 4, "temperature_c": 40.0}]

    assert temperature_alert_triggered(40.0, 5, previous, 40.0, 2) is True
    assert temperature_alert_triggered(
        40.0,
        6,
        [
            {"sequence_number": 5, "temperature_c": 40.0},
            {"sequence_number": 4, "temperature_c": 40.0},
        ],
        40.0,
        2,
    ) is False


def test_high_temperature_requires_consecutive_sequences_and_valid_values():
    assert temperature_alert_triggered(
        41.0,
        5,
        [{"sequence_number": 3, "temperature_c": 41.0}],
        40.0,
        2,
    ) is False
    assert temperature_alert_triggered(
        41.0,
        5,
        [{"sequence_number": 4, "temperature_c": None}],
        40.0,
        2,
    ) is False


def test_manual_trigger_does_not_bypass_sensor_decision():
    sample = reading()
    manual_sample = {**sample, "manual_trigger": True}

    assert evaluate(manual_sample)["decision"] == evaluate(sample)["decision"]


def test_motion_classifier_prevents_non_pothole_acceptance():
    result = evaluate(
        reading(
            motion_features={
                "vertical_peak_g": 0.05,
                "vertical_rms_g": 0.02,
                "dynamic_rms_g": 0.03,
                "acceleration_peak_g": 0.6,
                "jerk_peak_g_s": 1.0,
                "gyro_peak_dps": 0.0,
                "yaw_peak_dps": 0.0,
                "impact_duration_ms": 0,
                "vertical_peak_count": 0,
                "biphasic": False,
                "longitudinal_peak_g": 0.6,
                "lateral_peak_g": 0.02,
            }
        )
    )

    assert result["event_classification"] == "BRAKING_LIKE"
    assert result["decision"] == "REJECT"
    assert any("pothole-candidate criteria" in reason for reason in result["reasons"])
