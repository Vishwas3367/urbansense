# UrbanSense backend

FastAPI backend for authenticated sensor ingestion, trust-aware event decisions,
PostGIS event storage, road-issue fusion, audit records, and maintenance priority.
The scoring values are a prototype and require validation against labeled sensor
data; they are not operational thresholds or evidence of patentability.

## Local setup

1. In the backend folder, create and activate the virtual environment, then
   install the dependencies:

   ```bash
   cd backend
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. Copy `.env.example` to `.env` and replace every placeholder:

   ```bash
   cp .env.example .env
   ```

   Generate
   independent `JWT_SECRET`, `US_ADMIN_TOKEN`, and URL-safe database passwords
   using a cryptographically secure random generator. Generate
   `DEVICE_ENCRYPTION_KEY` with the configured Python interpreter:

   ```bash
   .venv/bin/python -c "import secrets; print(secrets.token_urlsafe(48))"
   .venv/bin/python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```

   Keep `.env` private; changing the encryption key makes stored device
   credentials unreadable.
3. Set `POSTGRES_PASSWORD` to the same database password in `.env` as the one
   embedded in `DATABASE_URL`.
4. Start PostgreSQL with PostGIS (Docker Compose is provided):

   ```bash
   docker compose up -d database
   ```

   Load the local variables in the shell before using the enrollment example:

   ```bash
   set -a
   source .env
   set +a
   ```
5. Initialize the PostGIS schema and start FastAPI:

   ```bash
   python -m app.init_db
   uvicorn app.main:app --reload
   ```

   The API is available at `http://localhost:8000`; interactive API docs are at
   `/docs`. Run the algorithm tests with `pytest`.

## Device enrollment and signed readings

Enroll each sensor with the admin bootstrap token. The returned device secret is
shown once; store it securely on that device and do not check it into source
control.

```bash
curl -X POST http://localhost:8000/api/devices \
  -H "Content-Type: application/json" \
  -H "X-Admin-Token: $US_ADMIN_TOKEN" \
  -d '{"device_id":"US-ESP32-001","vehicle_id":"BUS-001"}'
```

Send readings to `POST /api/readings` with `X-Device-ID` and
`X-Device-Signature`. The signature is an HMAC-SHA256 hex digest over the exact
UTF-8 JSON request-body bytes sent to the server; sign the same byte buffer that
is transmitted. Include a unique event ID and increasing per-device sequence
number. The ingest response records
`ACCEPT`, `REQUEST_DATA`, `DEFER`, or `REJECT`, the component scores, reasons,
and a fused issue when accepted.

The acceleration axes must be expressed in g (not m/s²). The trust-engine tests
include a synthetic conflict case where a single-threshold baseline accepts a
reading but the trust-aware engine defers it because another vehicle disagrees.
These tests demonstrate behavior on constructed examples only; they are not a
statistical accuracy comparison.

The ESP32 may include `manual_trigger: true` on its next reading after a button
press. This is recorded and shown as a manual signal, but does not bypass the
automatic trust decision or create an issue by itself. Configure
`HIGH_TEMPERATURE_THRESHOLD_C` (default `40`) and
`HIGH_TEMPERATURE_CONSECUTIVE_READINGS` (default `2`) to emit a high-temperature
alert after consecutive valid readings from the same device. This is a
prototype monitoring threshold, not an official health or safety limit.

The current ESP32 sketch sends `impact_detected`, `impact_peak_g`, and the
backend `motion_features` summary. The backend classifies the motion pattern
and stores its `event_classification` and `pothole_confidence` separately from
the trust-engine confidence and decision. Impact flags, manual button signals,
and high motion-classifier confidence do not by themselves bypass trust
requirements or create an accepted issue.

## Motion-analysis pipeline and simulation

Run deterministic synthetic scenarios for the motion-analysis pipeline:

```bash
cd backend
PYTHONPATH=. .venv/bin/python scripts/simulate_motion_pipeline.py
```

The simulation creates 100 Hz accelerometer and gyroscope samples for a
pothole-like impact, speed bump, repeated rough-road vibration, braking, sharp
turn, and normal travel. `motion_analysis.py` removes an EMA gravity estimate,
applies a one-pole motion filter, extracts peak/RMS acceleration, jerk, angular
velocity, impact duration/count, and a short biphasic impact/rebound feature.
The classifier returns a candidate label, confidence, and evidence; the
existing trust engine still decides whether a report is accepted.

The `motion_features` object is optional for compatibility with older clients.
When present, non-pothole motion classes cannot create an accepted road issue.
Reports without it are stored, but cannot be accepted as pothole evidence until
the multi-axis feature summary is provided. The ESP32 sketch now generates
this summary from its one-second MPU6050 window. The synthetic profiles are
illustrative software fixtures—not measured vehicle data, validation, or
production thresholds. Record labeled real-world samples and tune/test this
model before using it operationally.

The firmware currently sets `calibrated: false`. Under the current trust
engine this results in `REQUEST_DATA`, even when the motion classifier labels
the pattern `POTENTIAL_POTHOLE`. Do not change the flag until a real calibration
procedure has been completed and the firmware accurately represents it.

## API endpoints

- `POST /api/auth/login`: dashboard login; returns a bearer token.
- `POST /api/devices`: enroll a device with the admin bootstrap token; returns
  its device secret once.
- `POST /api/readings`: ingest HMAC-signed, sequenced sensor readings.
- `GET /api/summary`, `/api/vehicles`, `/api/events`, `/api/alerts`,
  `/api/issues`, `/api/maintenance`: dashboard data; require a bearer token.
- `GET /api/audit`: audit records; requires dashboard authorization.
- `GET /health`: process health check only; it does not guarantee database
  connectivity.

Interactive OpenAPI documentation is available at `/docs` while the API is
running.

Device secrets are encrypted at rest. Authenticated failures, replay attempts,
and processing decisions are written to the audit table.

## Prototype limitations

- HTTPS termination and certificate management belong at a trusted deployment
  reverse proxy; do not expose this development server directly to the internet.
- Device secrets are encrypted by the application. Encrypt the PostgreSQL
  storage volume at the infrastructure layer to protect stored telemetry at rest.
- Dashboard credentials are environment-configured prototype credentials, not
  a multi-user identity system.
- Trust and severity weights are explainable starting values, not scientifically
  calibrated. Test against labeled normal, anomalous, faulty, conflicting,
  stale, and duplicated readings before making reliability claims.
- A real patent filing needs prior-art research and advice from a registered
  patent professional; this implementation does not establish novelty or
  patentability.
