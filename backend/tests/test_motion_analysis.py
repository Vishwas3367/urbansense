from app.motion_analysis import classify_road_event, extract_motion_features
from app.motion_simulation import SAMPLE_RATE_HZ, generate_scenario_samples


def analyze(event: str, speed_kmh: float = 30.0):
    features = extract_motion_features(
        generate_scenario_samples(event),
        SAMPLE_RATE_HZ,
    )
    return features, classify_road_event(features, speed_kmh)


def test_simulated_pothole_uses_multiple_motion_features():
    features, result = analyze("pothole")

    assert result["classification"] == "POTENTIAL_POTHOLE"
    assert result["confidence"] >= 0.65
    assert features["vertical_peak_g"] >= 0.5
    assert features["jerk_peak_g_s"] >= 3
    assert features["biphasic"] is True


def test_simulated_speed_bump_is_not_classified_as_pothole():
    _, result = analyze("speed_bump")
    assert result["classification"] == "SPEED_BREAKER_LIKE"


def test_simulated_repeated_impacts_are_classified_as_rough_road():
    features, result = analyze("rough_road")
    assert features["vertical_peak_count"] >= 3
    assert result["classification"] == "ROUGH_ROAD_LIKE"


def test_simulated_braking_and_turning_use_axis_and_gyro_context():
    braking_features, braking = analyze("braking")
    turn_features, turn = analyze("sharp_turn")

    assert braking_features["longitudinal_peak_g"] >= 0.35
    assert braking["classification"] == "BRAKING_LIKE"
    assert turn_features["yaw_peak_dps"] >= 35
    assert turn["classification"] == "SHARP_TURN_LIKE"


def test_rotation_without_vertical_impact_is_not_a_pothole():
    samples = generate_scenario_samples("normal")
    for sample in samples[30:60]:
        sample["gx_dps"] = 100.0
    features = extract_motion_features(samples, SAMPLE_RATE_HZ)

    assert features["gyro_peak_dps"] >= 80
    assert classify_road_event(features, 30.0)["classification"] == "ROTATION_DOMINATED"


def test_normal_motion_and_low_speed_do_not_create_pothole_candidates():
    features, normal = analyze("normal")
    low_speed = classify_road_event(features, 5.0)

    assert normal["classification"] == "NORMAL_OR_UNCLASSIFIED"
    assert low_speed["classification"] == "INSUFFICIENT_SPEED"
