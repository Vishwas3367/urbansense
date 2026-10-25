SAMPLE_RATE_HZ = 100
SCENARIOS = ("pothole", "speed_bump", "rough_road", "braking", "sharp_turn", "normal")


def generate_scenario_samples(event: str) -> list[dict[str, float]]:
    samples = [
        {
            "ax_g": 0.0,
            "ay_g": 0.0,
            "az_g": 1.0,
            "gx_dps": 0.0,
            "gy_dps": 0.0,
            "gz_dps": 0.0,
        }
        for _ in range(SAMPLE_RATE_HZ)
    ]

    if event == "pothole":
        for index in (40, 41):
            samples[index]["az_g"] = 2.3
        for index in (42, 43):
            samples[index]["az_g"] = 0.2
    elif event == "speed_bump":
        for index in range(30, 65):
            samples[index]["az_g"] = 1.55
    elif event == "rough_road":
        for index in (20, 35, 50, 65, 80):
            samples[index]["az_g"] = 1.7
            samples[index + 1]["az_g"] = 0.4
    elif event == "braking":
        for sample in samples[30:]:
            sample["ax_g"] = -0.6
    elif event == "sharp_turn":
        for sample in samples[30:60]:
            sample["ay_g"] = 0.45
            sample["gz_dps"] = 45.0
    elif event != "normal":
        raise ValueError(f"Unknown simulated event: {event}")

    return samples
