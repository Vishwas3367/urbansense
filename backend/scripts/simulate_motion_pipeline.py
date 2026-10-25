import json
from datetime import datetime, timezone

from app.motion_analysis import classify_road_event, extract_motion_features
from app.motion_simulation import SAMPLE_RATE_HZ, SCENARIOS, generate_scenario_samples
from app.trust_engine import score_event


def main() -> None:
    for scenario in SCENARIOS:
        features = extract_motion_features(
            generate_scenario_samples(scenario),
            SAMPLE_RATE_HZ,
        )
        classification = classify_road_event(features, speed_kmh=30.0)
        analysis = score_event(
            {
                "timestamp": datetime.now(timezone.utc),
                "vehicle_id": "SIMULATED-VEHICLE",
                "ax": features["longitudinal_peak_g"],
                "ay": features["lateral_peak_g"],
                "az": 1.0 + features["vertical_peak_g"],
                "speed_kmh": 30,
                "gps_accuracy_m": 4,
                "temperature_c": None,
                "humidity_percent": None,
                "rainfall_mm": None,
                "jerk": min(features["jerk_peak_g_s"], 100.0),
                "sensor_status": "NORMAL",
                "calibrated": True,
                "motion_features": features,
            },
            device_trust=0.8,
            nearby_events=[],
            max_event_age_seconds=900,
        )
        print(
            json.dumps(
                {
                    "scenario": scenario,
                    "features": features,
                    "classification": classification,
                    "trust_confidence_percent": round(100 * analysis["confidence"]),
                    "risk_score": analysis["risk_score"],
                    "backend_decision": analysis["decision"],
                    "decision_reasons": analysis["reasons"],
                },
                sort_keys=True,
            )
        )


if __name__ == "__main__":
    main()
