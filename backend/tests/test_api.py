import json
from datetime import datetime, timezone

from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from app.config import get_settings
from app.database import get_db
from app.main import app
from app.models import Device, RoadIssue, SensorEvent
from app.motion_analysis import extract_motion_features
from app.motion_simulation import SAMPLE_RATE_HZ, generate_scenario_samples
from app.security import sign_event


class FakeDatabase:
    def __init__(self, device):
        self.device = device
        self.added = []

    def scalar(self, statement):
        entity = statement.column_descriptions[0]["entity"]
        if entity is Device:
            return self.device
        return None

    def scalars(self, _statement):
        return FakeResults()

    def add(self, value):
        self.added.append(value)

    def flush(self):
        for value in self.added:
            if isinstance(value, RoadIssue) and value.status is None:
                value.status = "Unresolved"

    def commit(self):
        pass

    def close(self):
        pass


class FakeResults:
    def all(self):
        return []


def test_health_and_dashboard_authentication(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-jwt-secret-that-is-long-enough-for-tests")
    monkeypatch.setenv("DASHBOARD_EMAIL", "admin@example.test")
    monkeypatch.setenv("DASHBOARD_PASSWORD", "test-password")
    get_settings.cache_clear()
    try:
        client = TestClient(app)
        assert client.get("/health").status_code == 200
        assert client.get("/api/issues").status_code == 401

        bad_login = client.post(
            "/api/auth/login",
            json={"email": "admin@example.test", "password": "wrong"},
        )
        assert bad_login.status_code == 401

        good_login = client.post(
            "/api/auth/login",
            json={"email": "admin@example.test", "password": "test-password"},
        )
        assert good_login.status_code == 200
        assert good_login.json()["token_type"] == "bearer"
    finally:
        get_settings.cache_clear()


def test_ingestion_authenticates_the_exact_request_bytes(monkeypatch):
    key = Fernet.generate_key().decode()
    secret = "registered-device-secret"
    monkeypatch.setenv("DEVICE_ENCRYPTION_KEY", key)
    get_settings.cache_clear()
    device = Device(
        id="US-ESP32-001",
        vehicle_id="BUS-001",
        secret_encrypted=Fernet(key.encode()).encrypt(secret.encode()).decode(),
        trust_score=0.8,
        last_sequence=0,
        is_active=True,
    )
    database = FakeDatabase(device)

    def fake_db():
        yield database

    app.dependency_overrides[get_db] = fake_db
    try:
        payload = {
            "event_id": "EVT-00000001",
            "sequence_number": 1,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "latitude": 12.9716,
            "longitude": 79.1594,
            "ax": 0.1,
            "ay": 0.1,
            "az": 2.0,
            "speed_kmh": 30,
            "gps_accuracy_m": 4,
            "temperature_c": 31,
            "humidity_percent": 60,
            "rainfall_mm": 0,
            "jerk": 1.5,
            "manual_trigger": True,
            "impact_detected": True,
            "impact_peak_g": 0.72,
            "motion_features": extract_motion_features(
                generate_scenario_samples("pothole"),
                SAMPLE_RATE_HZ,
            ),
        }
        body = json.dumps(payload, separators=(",", ":")).encode()
        signature = sign_event(body, secret)
        response = TestClient(app).post(
            "/api/readings",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Device-ID": device.id,
                "X-Device-Signature": signature,
            },
        )
        assert response.status_code == 201, response.text
        assert response.json()["decision"] == "ACCEPT"
        assert response.json()["event_classification"] == "POTENTIAL_POTHOLE"
        assert response.json()["pothole_confidence"] >= 65
        stored_event = next(
            item for item in database.added if isinstance(item, SensorEvent)
        )
        assert stored_event.manual_trigger is True
        assert stored_event.impact_detected is True
        assert stored_event.impact_peak_g == 0.72
        assert stored_event.event_classification == "POTENTIAL_POTHOLE"
        assert stored_event.pothole_confidence >= 0.65
        assert stored_event.motion_features == payload["motion_features"]

        threshold_only_payload = {
            **payload,
            "event_id": "EVT-00000002",
            "sequence_number": 2,
        }
        threshold_only_payload.pop("motion_features")
        threshold_only_body = json.dumps(
            threshold_only_payload,
            separators=(",", ":"),
        ).encode()
        threshold_only = TestClient(app).post(
            "/api/readings",
            content=threshold_only_body,
            headers={
                "Content-Type": "application/json",
                "X-Device-ID": device.id,
                "X-Device-Signature": sign_event(threshold_only_body, secret),
            },
        )
        assert threshold_only.status_code == 201
        assert threshold_only.json()["decision"] == "REQUEST_DATA"
        assert threshold_only.json()["issue"] is None
        assert stored_event.temperature_alert is False

        altered_body = body + b" "
        altered = TestClient(app).post(
            "/api/readings",
            content=altered_body,
            headers={
                "Content-Type": "application/json",
                "X-Device-ID": device.id,
                "X-Device-Signature": signature,
            },
        )
        assert altered.status_code == 401
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()
