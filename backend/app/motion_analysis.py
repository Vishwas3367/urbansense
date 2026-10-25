from math import exp, sqrt

GRAVITY_TIME_CONSTANT_SECONDS = 0.5
MOTION_FILTER_TIME_CONSTANT_SECONDS = 0.015
VERTICAL_ACTIVITY_THRESHOLD_G = 0.15


def extract_motion_features(
    samples: list[dict[str, float]],
    sample_rate_hz: float = 100.0,
) -> dict[str, float | int | bool]:
    if sample_rate_hz <= 0:
        raise ValueError("sample_rate_hz must be positive.")
    if len(samples) < 3:
        raise ValueError("At least three motion samples are required.")

    dt = 1.0 / sample_rate_hz
    gravity_alpha = 1.0 - exp(-dt / GRAVITY_TIME_CONSTANT_SECONDS)
    motion_alpha = dt / (MOTION_FILTER_TIME_CONSTANT_SECONDS + dt)
    first = samples[0]
    gravity = [first["ax_g"], first["ay_g"], first["az_g"]]
    dynamic_vectors: list[tuple[float, float, float]] = []
    filtered_motion = [0.0, 0.0, 0.0]
    gyro_magnitudes: list[float] = []
    yaw_rates: list[float] = []

    for sample in samples:
        acceleration = (sample["ax_g"], sample["ay_g"], sample["az_g"])
        gravity = [
            component + gravity_alpha * (observed - component)
            for component, observed in zip(gravity, acceleration, strict=True)
        ]
        dynamic = [
            observed - component
            for observed, component in zip(acceleration, gravity, strict=True)
        ]
        filtered_motion = [
            filtered + motion_alpha * (current - filtered)
            for filtered, current in zip(filtered_motion, dynamic, strict=True)
        ]
        dynamic_vectors.append(tuple(filtered_motion))
        gyro_magnitudes.append(
            sqrt(
                sample["gx_dps"] ** 2
                + sample["gy_dps"] ** 2
                + sample["gz_dps"] ** 2
            )
        )
        yaw_rates.append(abs(sample["gz_dps"]))

    vertical = [vector[2] for vector in dynamic_vectors]
    magnitudes = [sqrt(sum(component**2 for component in vector)) for vector in dynamic_vectors]
    vertical_peak_index = max(range(len(vertical)), key=lambda index: abs(vertical[index]))
    vertical_peak = abs(vertical[vertical_peak_index])
    vertical_rms = sqrt(sum(value**2 for value in vertical) / len(vertical))
    dynamic_rms = sqrt(sum(value**2 for value in magnitudes) / len(magnitudes))

    peak_jerk = 0.0
    for previous, current in zip(dynamic_vectors, dynamic_vectors[1:]):
        jerk = sqrt(
            sum((after - before) ** 2 for before, after in zip(previous, current, strict=True))
        ) / dt
        peak_jerk = max(peak_jerk, jerk)

    activity = [abs(value) >= VERTICAL_ACTIVITY_THRESHOLD_G for value in vertical]
    peak_count = sum(is_active and not was_active for was_active, is_active in zip(
        [False, *activity[:-1]], activity, strict=True
    ))
    duration_ms = round(sum(activity) * dt * 1000)

    neighborhood_samples = max(1, round(0.25 * sample_rate_hz))
    before_start = max(0, vertical_peak_index - neighborhood_samples)
    after_end = min(len(vertical), vertical_peak_index + neighborhood_samples + 1)
    peak_value = vertical[vertical_peak_index]
    if peak_value >= 0:
        opposing_before = any(
            value <= -VERTICAL_ACTIVITY_THRESHOLD_G
            for value in vertical[before_start:vertical_peak_index]
        )
        opposing_after = any(
            value <= -VERTICAL_ACTIVITY_THRESHOLD_G
            for value in vertical[vertical_peak_index + 1:after_end]
        )
    else:
        opposing_before = any(
            value >= VERTICAL_ACTIVITY_THRESHOLD_G
            for value in vertical[before_start:vertical_peak_index]
        )
        opposing_after = any(
            value >= VERTICAL_ACTIVITY_THRESHOLD_G
            for value in vertical[vertical_peak_index + 1:after_end]
        )

    longitudinal_peak = max(abs(vector[0]) for vector in dynamic_vectors)
    lateral_peak = max(abs(vector[1]) for vector in dynamic_vectors)
    return {
        "vertical_peak_g": round(vertical_peak, 4),
        "vertical_rms_g": round(vertical_rms, 4),
        "dynamic_rms_g": round(dynamic_rms, 4),
        "acceleration_peak_g": round(max(magnitudes), 4),
        "jerk_peak_g_s": round(peak_jerk, 3),
        "gyro_peak_dps": round(max(gyro_magnitudes), 3),
        "yaw_peak_dps": round(max(yaw_rates), 3),
        "impact_duration_ms": duration_ms,
        "vertical_peak_count": peak_count,
        "biphasic": opposing_before or opposing_after,
        "longitudinal_peak_g": round(longitudinal_peak, 4),
        "lateral_peak_g": round(lateral_peak, 4),
    }


def classify_road_event(
    features: dict[str, float | int | bool],
    speed_kmh: float,
) -> dict[str, str | float | list[str]]:
    vertical_peak = float(features["vertical_peak_g"])
    vertical_rms = float(features["vertical_rms_g"])
    dynamic_rms = float(features["dynamic_rms_g"])
    acceleration_peak = float(features["acceleration_peak_g"])
    duration_ms = int(features["impact_duration_ms"])
    peak_count = int(features["vertical_peak_count"])
    longitudinal_peak = float(features["longitudinal_peak_g"])
    lateral_peak = float(features["lateral_peak_g"])
    gyro_peak = float(features["gyro_peak_dps"])
    yaw_peak = float(features["yaw_peak_dps"])
    jerk_peak = float(features["jerk_peak_g_s"])
    biphasic = bool(features["biphasic"])

    if speed_kmh < 10:
        return {
            "classification": "INSUFFICIENT_SPEED",
            "confidence": 0.9,
            "evidence": ["Vehicle speed is below the prototype detection minimum."],
        }

    if longitudinal_peak >= 0.35 and longitudinal_peak >= vertical_peak:
        return {
            "classification": "BRAKING_LIKE",
            "confidence": min(0.95, 0.65 + longitudinal_peak * 0.3),
            "evidence": ["Longitudinal acceleration dominates the vertical impact."],
        }

    if (lateral_peak >= 0.35 or yaw_peak >= 35) and vertical_peak < 0.5:
        return {
            "classification": "SHARP_TURN_LIKE",
            "confidence": min(0.95, 0.65 + max(lateral_peak, yaw_peak / 100) * 0.3),
            "evidence": ["Lateral acceleration or yaw rate dominates without a strong vertical impact."],
        }

    if gyro_peak >= 80 and vertical_peak < 0.5:
        return {
            "classification": "ROTATION_DOMINATED",
            "confidence": min(0.95, 0.65 + gyro_peak / 400),
            "evidence": ["Angular velocity is high without a strong vertical impact."],
        }

    if vertical_peak >= 0.35 and duration_ms >= 250:
        return {
            "classification": "SPEED_BREAKER_LIKE",
            "confidence": min(0.9, 0.65 + duration_ms / 2000),
            "evidence": ["Vertical disturbance is broad compared with a short, isolated impact."],
        }

    if peak_count >= 3 or (
        peak_count >= 2 and max(dynamic_rms, vertical_rms) >= 0.18
    ):
        return {
            "classification": "ROUGH_ROAD_LIKE",
            "confidence": min(0.95, 0.65 + 0.08 * peak_count),
            "evidence": ["Repeated vertical vibration peaks occur in the analysis window."],
        }

    if vertical_peak >= 0.5:
        evidence = []
        confidence = 0.25
        if vertical_peak >= 0.5:
            confidence += 0.2
            evidence.append("Vertical acceleration exceeds the prototype impact threshold.")
        if jerk_peak >= 3:
            confidence += 0.2
            evidence.append("Acceleration changes rapidly around the event.")
        if biphasic:
            confidence += 0.2
            evidence.append("The vertical signal has opposing impact and rebound lobes.")
        if 20 <= duration_ms <= 250:
            confidence += 0.15
            evidence.append("The vertical disturbance is short in duration.")
        if (
            vertical_peak > max(longitudinal_peak, lateral_peak)
            and vertical_peak >= 0.6 * acceleration_peak
        ):
            confidence += 0.1
            evidence.append("Vertical motion dominates longitudinal and lateral motion.")
        if gyro_peak >= 80:
            confidence -= 0.1
            evidence.append("Large angular motion reduces pothole-specific confidence.")
        classification = "POTENTIAL_POTHOLE" if confidence >= 0.65 else "AMBIGUOUS_IMPACT"
        return {
            "classification": classification,
            "confidence": min(confidence, 0.95),
            "evidence": evidence or ["Impact features are not sufficiently distinctive."],
        }

    return {
        "classification": "NORMAL_OR_UNCLASSIFIED",
        "confidence": 0.6,
        "evidence": ["The analysis window does not match a strong prototype event pattern."],
    }
