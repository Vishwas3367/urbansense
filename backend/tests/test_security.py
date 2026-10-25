from app.security import sign_event, verify_device_signature


def test_hmac_signature_verifies_and_detects_payload_changes():
    raw_body = (
        b'{"event_id":"EVT-00000001","sequence_number":1,'
        b'"timestamp":"2026-10-25T10:30:00Z","latitude":12.9716,'
        b'"longitude":79.1594,"ax":0.1,"ay":0.1,"az":2.0,'
        b'"speed_kmh":30,"gps_accuracy_m":4}'
    )
    signature = sign_event(raw_body, "device-secret")
    assert verify_device_signature(raw_body, "device-secret", signature)
    assert not verify_device_signature(raw_body, "wrong-secret", signature)
    assert not verify_device_signature(raw_body + b" ", "device-secret", signature)
