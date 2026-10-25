# UrbanSense

UrbanSense is an experimental urban-infrastructure sensing prototype. An ESP32
with an MPU6050, GPS receiver, and DHT22 sends authenticated readings to a
FastAPI/PostGIS backend. A React dashboard displays device status, telemetry,
motion classifications, potential alerts, road issues, and analytics.

The project is an engineering prototype. Its sensor offsets, classifier
thresholds, trust scores, and temperature alert threshold have not been
validated against a representative labeled road dataset and are not safety or
maintenance standards.

## Project components

- [`backend/`](./backend/README.md): FastAPI API, device authentication,
  ingestion, PostGIS persistence, prototype trust scoring, motion analysis,
  temperature alerts, and synthetic test scenarios.
- [`frontend/`](./frontend/README.md): authenticated React dashboard using live
  backend data for monitoring, issues, notifications, and analytics.
- [`firmware/`](./firmware/README.md): ESP32 sketch, wiring, local
  configuration, sensor processing, and upload instructions.

## Local development

1. Set up PostgreSQL with PostGIS, configure `backend/.env`, initialize the
   schema, and start FastAPI using the [backend guide](./backend/README.md).
2. Start the frontend in another terminal:

   ```bash
   cd frontend
   npm install
   npm run dev
   ```
3. Open the Vite URL and sign in with the dashboard email and password from
   `backend/.env`.

During local development Vite proxies `/api` requests to
`http://127.0.0.1:8000`. Set `VITE_API_PROXY_TARGET` in `frontend/.env` if
FastAPI listens elsewhere. For deployments, set `VITE_API_BASE_URL` when the
API is not served from the same origin.

## Current sensor workflow

- ESP32 readings are authenticated with HMAC-SHA256 over the exact transmitted
  JSON bytes. Device sequences are persisted across reboots.
- MPU6050 samples are processed in a one-second window. The firmware reports
  gravity-corrected motion features; the backend classifies potential pothole,
  speed-breaker-like, rough-road-like, braking-like, turning, and other
  patterns.
- The trust engine separately decides `ACCEPT`, `REQUEST_DATA`, `DEFER`, or
  `REJECT`. Manual button signals and impact detections do not bypass that
  decision.
- DHT22 readings are shown on the dashboard. The backend emits a high
  temperature alert by default at 40°C for two consecutive valid readings.
- Analytics are derived from backend events and issues. Coverage route visuals
  remain explicitly simulated demonstration data.

See the component READMEs for API details, wiring, local secrets, test
commands, prototype limitations, and safe setup. Do not commit or share Wi-Fi
passwords, device secrets, dashboard credentials, or `.env` files. Rotate any
credential exposed in chat, terminal output, or an editor selection.
