from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.schemas import SensorReading


def base_reading(**overrides):
    values = {
        "event_id": "EVT-00000001",
        "sequence_number": 1,
        "timestamp": datetime.now(timezone.utc),
        "latitude": 12.9,
        "longitude": 79.1,
        "ax": 0.0,
        "ay": 0.0,
        "az": 1.0,
        "speed_kmh": 0,
        "gps_accuracy_m": 5,
    }
    values.update(overrides)
    return values


def test_temperature_and_humidity_can_be_missing_without_fake_defaults():
    reading = SensorReading(**base_reading())

    assert reading.temperature_c is None
    assert reading.humidity_percent is None
    assert reading.calibrated is False


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("temperature_c", float("nan")),
        ("temperature_c", float("inf")),
        ("temperature_c", 81),
        ("humidity_percent", float("nan")),
        ("humidity_percent", -1),
        ("ax", float("nan")),
        ("gps_accuracy_m", float("inf")),
    ],
)
def test_invalid_sensor_values_are_rejected(field, value):
    with pytest.raises(ValidationError):
        SensorReading(**base_reading(**{field: value}))


def test_valid_temperature_and_humidity_are_preserved():
    reading = SensorReading(
        **base_reading(temperature_c=29.8, humidity_percent=67.6)
    )

    assert reading.temperature_c == 29.8
    assert reading.humidity_percent == 67.6
