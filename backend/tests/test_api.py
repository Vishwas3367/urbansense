import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from app.config import get_settings
from app.database import get_db
from app.main import DEVICE_ACTIVE_WINDOW_SECONDS, app
from app.models import Device, RoadIssue, SensorEvent
from app.motion_analysis import extract_motion_features
from app.motion_simulation import SAMPLE_RATE_HZ, generate_scenario_samples
from app.security import require_dashboard_user, sign_event


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
    def __init__(self, values=None):
        self.values = values or []

    def all(self):
        return self.values


class FakeVehicleDatabase:
    def __init__(self, devices, events):
        self.devices = devices
        self.events = events

    def scalars(self, statement):
        entity = statement.column_descriptions[0]["entity"]
        if entity is Device:
            return FakeResults(self.devices)
        if entity is SensorEvent and "manual_trigger IS true" in str(statement.whereclause):
            return FakeResults(self.events)
        return FakeResults([])

    def scalar(self, statement):
        entity = statement.column_descriptions[0]["entity"]
        if entity is not SensorEvent:
            return 0

        where_clause = str(statement.whereclause)
        events = self.events
        if "temperature_c IS NOT NULL" in where_clause:
            events = [event for event in events if event.temperature_c is not None]
        elif "humidity_percent IS NOT NULL" in where_clause:
            events = [event for event in events if event.humidity_percent is not None]
        return max(
            events,
            key=lambda event: (event.observed_at, event.sequence_number),
            default=None,
        )

    def close(self):
        pass


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
    monkeypatch.setenv("HIGH_TEMPERATURE_CONSECUTIVE_READINGS", "1")
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
            "calibrated": True,
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
        assert response.json()["temperature_c"] == 31
        assert response.json()["humidity_percent"] == 60
        assert response.json()["decision"] == "ACCEPT"
        assert response.json()["event_classification"] == "POTENTIAL_POTHOLE"
        assert response.json()["pothole_confidence"] >= 65
        assert response.json()["issue"] is not None
        stored_event = next(
            item for item in database.added if isinstance(item, SensorEvent)
        )
        assert stored_event.manual_trigger is True
        assert stored_event.impact_detected is True
        assert stored_event.impact_peak_g == 0.72
        assert stored_event.event_classification == "POTENTIAL_POTHOLE"
        assert stored_event.pothole_confidence >= 0.65
        assert stored_event.motion_features == payload["motion_features"]
        assert any(isinstance(item, RoadIssue) for item in database.added)

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

        missing_environment_payload = {
            **payload,
            "event_id": "EVT-00000003",
            "sequence_number": 3,
        }
        missing_environment_payload.pop("temperature_c")
        missing_environment_payload.pop("humidity_percent")
        missing_environment_body = json.dumps(
            missing_environment_payload,
            separators=(",", ":"),
        ).encode()
        missing_environment = TestClient(app).post(
            "/api/readings",
            content=missing_environment_body,
            headers={
                "Content-Type": "application/json",
                "X-Device-ID": device.id,
                "X-Device-Signature": sign_event(missing_environment_body, secret),
            },
        )
        assert missing_environment.status_code == 201
        assert missing_environment.json()["temperature_c"] is None
        assert missing_environment.json()["humidity_percent"] is None

        stale_hot_payload = {
            **payload,
            "event_id": "EVT-00000004",
            "sequence_number": 4,
            "timestamp": (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat(),
            "temperature_c": 45,
        }
        stale_hot_body = json.dumps(stale_hot_payload, separators=(",", ":")).encode()
        stale_hot = TestClient(app).post(
            "/api/readings",
            content=stale_hot_body,
            headers={
                "Content-Type": "application/json",
                "X-Device-ID": device.id,
                "X-Device-Signature": sign_event(stale_hot_body, secret),
            },
        )
        assert stale_hot.status_code == 201
        assert stale_hot.json()["decision"] == "DEFER"
        stale_hot_event = next(
            item
            for item in database.added
            if isinstance(item, SensorEvent) and item.event_id == "EVT-00000004"
        )
        assert stale_hot_event.temperature_alert is False

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


def test_vehicle_uses_latest_fresh_valid_temperature_and_humidity():
    now = datetime.now(timezone.utc)
    device = SimpleNamespace(
        id="US-ESP32-001",
        vehicle_id="BUS-001",
        is_active=True,
        trust_score=0.8,
    )
    events = [
        SimpleNamespace(
            device_id=device.id,
            observed_at=now - timedelta(minutes=10),
            sequence_number=1,
            temperature_c=35.0,
            humidity_percent=55.0,
        ),
        SimpleNamespace(
            device_id=device.id,
            observed_at=now - timedelta(seconds=30),
            sequence_number=2,
            temperature_c=28.4,
            humidity_percent=None,
        ),
        SimpleNamespace(
            device_id=device.id,
            observed_at=now - timedelta(seconds=10),
            sequence_number=3,
            temperature_c=None,
            humidity_percent=67.1,
            latitude=12.9,
            longitude=79.1,
            speed_kmh=22,
            gps_accuracy_m=5,
        ),
    ]
    database = FakeVehicleDatabase([device], events)

    def fake_db():
        yield database

    app.dependency_overrides[get_db] = fake_db
    app.dependency_overrides[require_dashboard_user] = lambda: "admin"
    try:
        response = TestClient(app).get("/api/vehicles")
        assert response.status_code == 200
        vehicle = response.json()[0]
        assert vehicle["temperature_c"] == 28.4
        assert vehicle["humidity_percent"] == 67.1
    finally:
        app.dependency_overrides.clear()


def test_vehicle_hides_stale_measurements():
    now = datetime.now(timezone.utc)
    device = SimpleNamespace(
        id="US-ESP32-001",
        vehicle_id="BUS-001",
        is_active=True,
        trust_score=0.8,
    )
    old_event = SimpleNamespace(
        device_id=device.id,
        observed_at=now - timedelta(seconds=DEVICE_ACTIVE_WINDOW_SECONDS + 1),
        sequence_number=1,
        temperature_c=29.8,
        humidity_percent=67.6,
        latitude=12.9,
        longitude=79.1,
        speed_kmh=22,
        gps_accuracy_m=5,
    )
    database = FakeVehicleDatabase([device], [old_event])

    def fake_db():
        yield database

    app.dependency_overrides[get_db] = fake_db
    app.dependency_overrides[require_dashboard_user] = lambda: "admin"
    try:
        response = TestClient(app).get("/api/vehicles")
        assert response.status_code == 200
        vehicle = response.json()[0]
        assert vehicle["temperature_c"] is None
        assert vehicle["humidity_percent"] is None
    finally:
        app.dependency_overrides.clear()


def test_manual_trigger_is_stored_and_returned_as_pending_candidate(monkeypatch):
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
    app.dependency_overrides[require_dashboard_user] = lambda: "admin"
    try:
        payload = {
            "event_id": "EVT-MANUAL-0001",
            "sequence_number": 1,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "latitude": 12.9716,
            "longitude": 79.1594,
            "ax": 0.01,
            "ay": 0.01,
            "az": 1.0,
            "speed_kmh": 30,
            "gps_accuracy_m": 4,
            "manual_trigger": True,
            "calibrated": True,
        }
        body = json.dumps(payload, separators=(",", ":")).encode()
        response = TestClient(app).post(
            "/api/readings",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Device-ID": device.id,
                "X-Device-Signature": sign_event(body, secret),
            },
        )

        assert response.status_code == 201, response.text
        assert response.json()["decision"] == "REQUEST_DATA"
        assert response.json()["issue"] is None
        stored_event = next(
            event
            for event in database.added
            if isinstance(event, SensorEvent)
        )
        assert stored_event.manual_trigger is True

        reports_database = FakeVehicleDatabase(
            [],
            [
                SimpleNamespace(
                    event_id=stored_event.event_id,
                    vehicle_id=stored_event.vehicle_id,
                    latitude=stored_event.latitude,
                    longitude=stored_event.longitude,
                    observed_at=stored_event.observed_at,
                    received_at=datetime.now(timezone.utc),
                    decision=stored_event.decision,
                    confidence=stored_event.confidence,
                    decision_reasons=stored_event.decision_reasons,
                    event_classification=stored_event.event_classification,
                ),
                SimpleNamespace(
                    event_id="EVT-MANUAL-CONFIRMED",
                    vehicle_id="BUS-001",
                    latitude=12.9717,
                    longitude=79.1595,
                    observed_at=stored_event.observed_at,
                    received_at=datetime.now(timezone.utc),
                    decision="ACCEPT",
                    confidence=0.91,
                    decision_reasons=["Motion candidate passed the configured validation checks."],
                    event_classification="POTENTIAL_POTHOLE",
                ),
                SimpleNamespace(
                    event_id="EVT-MANUAL-DEFERRED",
                    vehicle_id="BUS-002",
                    latitude=12.9718,
                    longitude=79.1596,
                    observed_at=stored_event.observed_at,
                    received_at=datetime.now(timezone.utc),
                    decision="DEFER",
                    confidence=0.48,
                    decision_reasons=["Conflicting observations require review."],
                    event_classification="NORMAL_OR_UNCLASSIFIED",
                ),
                SimpleNamespace(
                    event_id="EVT-MANUAL-REJECTED",
                    vehicle_id="BUS-003",
                    latitude=12.9719,
                    longitude=79.1597,
                    observed_at=stored_event.observed_at,
                    received_at=datetime.now(timezone.utc),
                    decision="REJECT",
                    confidence=0.12,
                    decision_reasons=["Device health is below the acceptance floor."],
                    event_classification="NORMAL_OR_UNCLASSIFIED",
                ),
            ],
        )

        def reports_db():
            yield reports_database

        app.dependency_overrides[get_db] = reports_db
        report_response = TestClient(app).get("/api/manual-reports")
        assert report_response.status_code == 200
        reports = {report["event_id"]: report for report in report_response.json()}
        report = reports["EVT-MANUAL-0001"]
        assert report["event_id"] == "EVT-MANUAL-0001"
        assert report["vehicle_id"] == "BUS-001"
        assert report["latitude"] == 12.9716
        assert report["longitude"] == 79.1594
        assert report["detection_status"] == "PENDING"
        assert report["decision"] == "REQUEST_DATA"
        assert report["reasons"]
        assert reports["EVT-MANUAL-CONFIRMED"]["detection_status"] == "CONFIRMED"
        assert reports["EVT-MANUAL-DEFERRED"]["detection_status"] == "DEFERRED"
        assert reports["EVT-MANUAL-REJECTED"]["detection_status"] == "REJECTED"
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()


def test_manual_trigger_without_gps_coordinates_is_rejected(monkeypatch):
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
            "event_id": "EVT-MANUAL-NOGPS",
            "sequence_number": 1,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "longitude": 79.1594,
            "ax": 0.01,
            "ay": 0.01,
            "az": 1.0,
            "speed_kmh": 0,
            "gps_accuracy_m": 4,
            "manual_trigger": True,
        }
        body = json.dumps(payload, separators=(",", ":")).encode()
        response = TestClient(app).post(
            "/api/readings",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Device-ID": device.id,
                "X-Device-Signature": sign_event(body, secret),
            },
        )

        assert response.status_code == 422
        assert not database.added
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()
