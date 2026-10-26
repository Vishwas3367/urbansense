# UrbanSense technical disclosure for patent-report preparation

This file is a separate technical reference for preparing a detailed,
evidence-based invention disclosure or patent-oriented report about UrbanSense.
It supplements the project [README](./README.md); it does not replace it.

## Important limits

UrbanSense is a working engineering prototype. This document is not a patent
application, legal opinion, novelty search, or claim of patentability. Do not
describe a feature as novel, inventive, commercially proven, or legally
protectable without independent evidence and review by a qualified patent
professional. Do not invent experimental results, inventors, dates of
conception, public disclosures, test performance, or implementation details
that are not supported by the repository or project records.

The implementation details below describe the current checked-in code, not
necessarily the earliest conception or every deployed build. Confirm inventors,
ownership, contribution dates, public disclosure dates, and the exact firmware
and software revisions with the project team before preparing a filing.

## Working title

Trust-aware mobile sensing and infrastructure-reporting system for
location-tagged road-condition observations.

This is a descriptive title, not a claim that the system or any element is new.

## Technical field

The project combines mobile IoT sensing, inertial-sensor signal processing,
geolocation, authenticated telemetry, backend evidence evaluation, and
infrastructure-report visualization. The current demonstration targets
potential road-surface anomalies sensed from vehicle-mounted equipment.

## Problem addressed by the prototype

The prototype is designed to explore how a fleet of mobile sensing nodes can
submit location-associated sensor readings while the server distinguishes
candidate observations from reports that satisfy configured evidence and
trust checks. It also explores recording human-triggered reports without
treating a button press as proof that an infrastructure defect exists.

These are project goals, not validated claims that the implementation solves
the problem more effectively than existing systems.

## System overview

The repository contains three connected components:

1. **Vehicle sensor node** — an ESP32 sketch reads an MPU6050 inertial sensor,
   GPS receiver, DHT22 temperature/humidity sensor, and a manual report button.
2. **Backend** — a FastAPI service validates and authenticates incoming
   readings, evaluates signal and context evidence, stores events in PostgreSQL
   with PostGIS location data, and fuses accepted nearby road issues.
3. **Dashboard** — a React/Vite application requests authenticated backend
   data and displays devices, readings, candidate reports, accepted issues,
   map locations, and analytics.

The principal source locations are:

- Firmware: [`firmware/esp32/urbansense_esp32.ino`](./firmware/esp32/urbansense_esp32.ino)
- Backend ingestion and API: [`backend/app/main.py`](./backend/app/main.py)
- Input schemas: [`backend/app/schemas.py`](./backend/app/schemas.py)
- Trust and decision logic: [`backend/app/trust_engine.py`](./backend/app/trust_engine.py)
- Motion classifier: [`backend/app/motion_analysis.py`](./backend/app/motion_analysis.py)
- Frontend monitoring: [`frontend/src/app/pages/Monitoring.jsx`](./frontend/src/app/pages/Monitoring.jsx)
- Frontend report/issue page: [`frontend/src/app/pages/Issues.jsx`](./frontend/src/app/pages/Issues.jsx)
- Map rendering: [`frontend/src/app/components/MapView.jsx`](./frontend/src/app/components/MapView.jsx)

## Current end-to-end operation

### 1. Sensor startup and calibration

The firmware initializes the MPU6050 through Adafruit's MPU6050 library and
collects 150 samples at approximately 50 Hz, taking roughly three seconds.
The calibration expects a stationary, level sensor with its Z axis pointing
up. It estimates three accelerometer offsets from the sample means, subtracting
one g from the Z mean to account for gravity, and three gyro offsets from the
measured angular rates.

The calibration is rejected when acceleration magnitude deviates from one g by
more than 0.15 g, gyro magnitude exceeds 5 degrees/second, per-axis
accelerometer sample standard deviation exceeds 0.04 g, per-axis gyro standard
deviation exceeds 1.5 degrees/second, or a sample is non-finite. The firmware
prints progress, failure cause, calculated offsets on success, and the final
status. A failed attempt leaves `calibrated` false and prevents the MPU sampling
task and sensor-reading submission from starting. Sending `r` or `R` over the
serial monitor retries calibration.

These are prototype thresholds and a single-orientation stationary bias
estimate, not a full multi-axis or orientation-independent calibration. Motion
feature extraction assumes level, Z-up installation.

### 2. Motion sampling and transmission

After successful calibration, the firmware samples the MPU6050 at 100 Hz and
maintains a one-second, 100-sample motion window. It subtracts the estimated
accelerometer and gyro offsets before calculating motion features. The
reported summary includes vertical, longitudinal, and lateral peaks; RMS and
combined acceleration; jerk; gyro/yaw peaks; impact duration and peak count;
and a biphasic impact/rebound indicator.

The firmware can flag an automatic impact candidate after a vertical dynamic
peak of at least 0.5 g while vehicle speed is at least 10 km/h, GPS is recent,
and the event-separation interval has elapsed. The firmware preserves the
associated motion window and GPS position for transmission. These thresholds
are a prototype profile; an impact flag is not an accepted infrastructure
issue.

Each reading includes an event ID, persistent increasing per-device sequence
number, UTC timestamp, GPS coordinates and HDOP-derived accuracy estimate,
speed, acceleration, temperature/humidity where available, calibration and
sensor status, manual-trigger and impact flags, and motion features. The
reading is signed using HMAC-SHA256 over the exact serialized JSON body sent
to the backend.

### 3. Authentication, validation, and persistence

The backend enrolls devices using an administrative token and issues a device
secret once. Device secrets are encrypted at rest by the application. Reading
requests identify the device and carry its HMAC signature. The API validates
the payload schema, verifies the signature, checks device state and sequence
replay conditions, then stores the event and processing result.

Coordinates, sensor values, sequence numbers, calibration state, status, and
optional motion features have schema constraints in `backend/app/schemas.py`.
Temperature and humidity may be null; the API does not fabricate missing
measurements. Latest temperature and humidity values are selected
independently, and values older than the configured five-minute freshness
window are exposed as unavailable in the vehicle response.

### 4. Motion classification and trust-aware decision

The backend motion classifier processes the supplied multi-axis summary and
returns a classification, motion-classifier confidence, and evidence. Example
classes include `POTENTIAL_POTHOLE`, `SPEED_BREAKER_LIKE`,
`ROUGH_ROAD_LIKE`, `BRAKING_LIKE`, `SHARP_TURN_LIKE`,
`ROTATION_DOMINATED`, `NORMAL_OR_UNCLASSIFIED`, and `INSUFFICIENT_SPEED`.
Motion confidence is kept distinct from trust-engine confidence and the final
decision.

The trust engine combines device trust, anomaly evidence, contextual evidence,
GPS quality, sensor status, calibration state, reading freshness, nearby
observations from other vehicles, and motion-classifier output. In the current
implementation, its confidence is computed as:

`0.25 * clamped device trust + 0.40 * anomaly evidence + 0.20 * contextual evidence + 0.15 * corroboration`

Its initial decision thresholds and subsequent safety gates are prototype
logic. The result is one of `ACCEPT`, `REQUEST_DATA`, `DEFER`, or `REJECT`,
with reasons. Stale readings or conflicts can defer; uncalibrated, degraded,
or imprecise-GPS readings can request more data; weak health/trust can reject.
The motion result can prevent acceptance where motion features are missing,
speed is insufficient, or the class is not a potential pothole.

A manual trigger is stored as a candidate signal, not a confirmation. Under
the current trust logic it can change an otherwise rejected, non-fault reading
to `REQUEST_DATA` only when device trust meets the configured floor; it does
not override a fault status, a `DEFER`, or an `ACCEPT` rule. Reasons and status
are derived from the stored backend result.

### 5. Candidate reports and accepted-issue fusion

Manual-trigger readings are available through the authenticated
`GET /api/manual-reports` endpoint. The endpoint maps stored decisions to
display states: `REQUEST_DATA` → `PENDING`, `DEFER` → `DEFERRED`,
`REJECT` → `REJECTED`, and `ACCEPT` → `CONFIRMED`. Each record includes the
actual vehicle identifier, GPS coordinates, observed and received timestamps,
backend decision, trust confidence, reasons, and classification.

An `ACCEPT` decision creates or updates a `RoadIssue`. The backend searches
for a non-resolved issue within a 25-meter PostGIS geography radius; if found,
it updates the stored location, detection count, vehicles, last-seen time, and
worst confidence/risk/severity metrics. Otherwise it creates a new issue.
Non-accepted manual reports remain in sensor-event history and are not
promoted to accepted issues by the frontend.

### 6. Dashboard presentation

The authenticated dashboard polls live backend endpoints at 10-second
intervals. Infrastructure Intelligence renders manual reports separately
from accepted issues. Live Monitoring renders report markers at returned GPS
coordinates, using different visual styles for pending, deferred, rejected,
and confirmed reports. The UI displays backend-returned statuses and reasons;
it does not determine acceptance. The Mobile Units details modal displays
temperature in °C when the backend has a fresh value.

Coverage-route visuals are still demonstration/simulated content and are not
actual fleet coverage. The map's manual-report markers are backed by actual
manual report coordinates.

## Data and decision sequence

```text
MPU6050 + GPS + DHT22 + button
             |
             v
Stationary calibration -> 100 Hz motion window -> JSON reading
                                                  |
                                      HMAC + device sequence
                                                  |
                                                  v
FastAPI validation -> signature/replay checks -> event persistence
                                                  |
                         motion classification + trust/conflict evaluation
                                      |                       |
                       REQUEST_DATA / DEFER / REJECT         ACCEPT
                                      |                       |
                          manual candidate API       25 m issue fusion
                                      |                       |
                                      +----------+------------+
                                                 v
                              authenticated dashboard polling
```

## Evidence currently in the repository

The repository includes backend tests for schema validation, signed
ingestion/authentication, decisions, sensor values, manual-report status, and
issue behavior, plus deterministic synthetic motion-analysis scenarios. At
the time of this document update, the backend test suite completed with 37
passing tests. The frontend production build completed successfully, with a
bundler warning about a JavaScript chunk exceeding 500 kB. These are software
checks, not field validation, statistical performance evidence, or patent
evidence. The firmware has not been compiled with an ESP32 Arduino toolchain
or hardware-tested in the current environment.

## Known limitations and information not established here

- No prior-art search or legal claim analysis has been performed.
- The repository does not establish who qualifies as an inventor, ownership,
  conception dates, filing dates, or whether/when public disclosure occurred.
- Trust weights, motion thresholds, stationarity limits, severity and
  maintenance scoring are prototype values, not trained/validated values.
- Synthetic scenarios do not demonstrate accuracy on real roads or across
  vehicles, sensor mounting variations, weather, speed, or hardware batches.
- Calibration is stationary and orientation-specific; the system does not
  estimate changing device orientation.
- GPS accuracy is an HDOP-derived estimate. The system depends on a valid,
  recent GPS fix for location-based reporting.
- Nearby-event fusion and the 25-meter radius are current implementation
  choices; no claim is made that these are optimal.
- There is no demonstrated fleet-scale, adversarial, safety-certification, or
  field-reliability result in this repository.
- A dashboard `201` response confirms that ingestion was processed, not that
  a pothole was accepted.

## Instructions for preparing a patent-oriented report from this file

Use this document together with the current source code and the project
README. Separate statements into:

1. **Verified implementation facts** — directly supported by code or tests.
2. **Design intent** — goals expressed by the project team but not proven.
3. **Potential inventive concepts for review** — hypotheses requiring prior-art
   search and patent-counsel analysis, never conclusions of novelty.
4. **Open questions** — missing inventor, dates, deployment, measurement, and
   disclosure facts to obtain from the project team.

If asked to produce the report, prepare a technical invention-disclosure style
document with a plain-language abstract, system architecture, detailed
embodiments, step-by-step data and decision flows, alternatives, figure
descriptions, implementation evidence, limitations, and a prior-art research
plan. Do not draft definitive legal claims or state that the system is novel
or patentable. Label speculative alternatives as proposals rather than
existing features and recommend review by a qualified patent professional.
