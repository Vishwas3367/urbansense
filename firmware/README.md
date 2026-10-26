# UrbanSense ESP32 firmware

The example sketch is `esp32/urbansense_esp32.ino`. It sends MPU6050
acceleration (in g), GPS coordinates, speed, estimated GPS accuracy, and
available DHT22 temperature/humidity to the authenticated FastAPI endpoint.
The sketch waits for a valid, recent GPS fix and HDOP before sending, so it
does not substitute a made-up accuracy value when GPS accuracy is unavailable.

## Startup motion calibration

The sketch uses the Adafruit MPU6050 library to collect 150 accelerometer and
gyroscope samples at 50 Hz (about three seconds) during startup. Keep the
sensor stationary, level, and with its Z axis pointing up throughout this
calibration. The sketch calculates each accelerometer offset from the collected
mean (subtracting 1 g from the Z-axis mean for gravity) and each gyroscope
offset from the measured mean angular rate. These measured offsets are applied
to the top-level acceleration values and every motion sample used by the
motion-feature pipeline; no preset calibration offsets are used.

Calibration fails if measured acceleration magnitude or angular rate indicates
movement, or if per-axis sample variation exceeds the stationarity limits.
On failure, the firmware leaves `calibrated` false, does not start motion
sampling or submit readings, and reports the cause in Serial Monitor. Hold the
sensor still and send `r` in Serial Monitor to retry; use 115200 baud. A
successful calibration prints all six calculated offsets and starts sampling.
`calibrated` becomes true only after all calibration checks pass.

The sketch then samples motion at 100 Hz and analyzes
the latest 1-second motion window. A vertical dynamic peak at `0.5 g` while
moving at least 10 km/h is a candidate trigger; events are separated by at
least 500 ms. A peak of at least `1.0 g` is reported as high impact in Serial
Monitor. Bias-corrected acceleration including gravity is sent in the
top-level API fields for compatibility; the backend-compatible motion summary
uses EMA gravity removal and filtering.

These thresholds are a prototype profile, not proof of calibration or
confirmation of a pothole. The feature
pipeline assumes a level, Z-up sensor and does not estimate changing sensor
orientation. Validate the mounting orientation and collect labeled
normal-road, pothole, and speed-bump data before relying on these thresholds.
The GPS parser runs independently from HTTP sending so it can keep updating
the fix while a request is in progress.

## Before uploading

1. Install the Arduino libraries used by the sketch: Adafruit MPU6050,
   Adafruit Unified Sensor, DHT sensor library, TinyGPSPlus, ArduinoJson 7,
   and the ESP32 Arduino core.
   MPU6050 I2C is on GPIO 21 (SDA) and GPIO 22 (SCL). The button uses
   `INPUT_PULLUP`, so wire it between GPIO 18 and GND.
2. Set `WIFI_SSID` and `WIFI_PASSWORD` locally.
3. Set `BACKEND_URL` to the Mac's current LAN IPv4 address, for example
   `http://192.168.1.10:8000`. Start FastAPI with `--host 0.0.0.0`; the ESP32
   and Mac must be able to communicate over the same network.
4. Set `DEVICE_ID` and `DEVICE_SECRET` to the registered device credentials.
   Keep the secret in local firmware configuration only; never commit it or
   share it in logs or chat.
5. Before powering the board, place the MPU6050 level with its Z axis up on a
   stable surface. Keep it still for the three-second startup calibration.
   Confirm Serial Monitor prints `Calibration SUCCESSFUL` and the six measured
   offsets before testing motion. If calibration fails, stabilize the sensor
   and send `r` in Serial Monitor to retry. Configure
   `HIGH_TEMPERATURE_THRESHOLD_C` and
   `HIGH_TEMPERATURE_CONSECUTIVE_READINGS` in the backend environment as
   needed. Defaults are 40°C and two consecutive valid readings. This is a
   prototype environmental alert threshold, not an official safety limit.
6. Upload and open Serial Monitor at 115200 baud. Check the HTTP status and
   backend `decision` for each reading.

The button adds `manual_trigger: true` to the next successfully submitted
reading and uses the most recent valid GPS fix captured at button press. Wire
the button between GPIO 18 and GND. The backend stores and displays this manual
signal but does not bypass automated trust scoring or create an issue solely
because the button was pressed. If pressed before a valid GPS fix is available,
the firmware keeps the manual report queued and waits for a fresh GPS fix before
submitting it.

Automatic threshold crossings are sent as `impact_detected` with
`impact_peak_g` and the latest recent GPS fix captured at the impact. They are
shown as potential impacts; they do not force an accepted road issue or
bypass the backend trust decision.

The sketch sends the backend's full `motion_features` summary from the most
recent one-second, 100 Hz window: gravity-corrected vertical, lateral, and
longitudinal peaks; RMS and combined acceleration; jerk; gyroscope and yaw
rates; active-impact duration/count; and an opposing impact/rebound flag. A
detected impact preserves its own feature window and GPS fix until the backend
processes it. The backend classifies that summary and returns its
classification and confidence alongside the separate trust decision. Run the
synthetic pipeline examples in [the backend README](../backend/README.md)
before testing on the vehicle.

After successful stationary calibration, the firmware reports
`calibrated: true` with each reading. Calibration does not bypass backend
trust validation: readings can still return `REQUEST_DATA` when additional
validation is needed.

## Hardware pin map

| Part | ESP32 connection |
| --- | --- |
| DHT22 data | GPIO 4 |
| GPS module TX to ESP32 RX | GPIO 16 |
| GPS module RX from ESP32 TX | GPIO 17 |
| LED signal | GPIO 19 |
| Buzzer signal | GPIO 5 |
| Push button | GPIO 18 to GND (`INPUT_PULLUP`) |
| MPU6050 SDA | GPIO 21 |
| MPU6050 SCL | GPIO 22 |

Use the appropriate power, ground, and level requirements for each breakout
board. GPIO signal assignments do not define the sensor module's supply
voltage. The code expects a GPS UART baud rate of 9600.

## Data sent to the backend

The sketch sends event ID, persistent sequence number, UTC timestamp, recent
GPS latitude/longitude, HDOP-derived GPS accuracy estimate, speed, acceleration
in g, DHT22 temperature/humidity, sensor status, `calibrated`, and
`manual_trigger`. It also sends `impact_detected`, `impact_peak_g`, `jerk`, and
the validated `motion_features` fields required by the current backend:

- vertical peak and RMS acceleration, total dynamic RMS, and acceleration
  peak, all in g;
- peak jerk in g/s;
- peak combined gyro and yaw rates in degrees/second;
- active impact duration in milliseconds and vertical peak count;
- `biphasic`, indicating an opposing acceleration lobe near the largest peak;
- longitudinal and lateral dynamic acceleration peaks in g.

Each request is HMAC-SHA256 signed over the exact serialized JSON bytes sent
over HTTP. The sketch parses and prints the backend's decision,
motion-classification label, classifier confidence, reasons, and issue ID when
present. HTTP `201` means the API processed the request; it does not imply the
decision is `ACCEPT`.

The sketch stores the next sequence number in ESP32 Preferences before sending
to avoid replaying a sequence after a restart. If the board is replaced or its
Preferences are erased, synchronize/reset its sequence with care; the backend
rejects sequence numbers that are not newer than the last recorded reading.

## Known prototype limitations

- Startup calibration estimates stationary sensor bias only; it is not a
  multi-orientation calibration. The feature extraction assumes a level,
  Z-up mounting and does not estimate changing sensor orientation.
- The backend accepts an issue only after its trust rules pass. A successful
  firmware calibration is necessary but does not by itself guarantee issue
  acceptance; readings may still return `REQUEST_DATA`.
- `gps_accuracy_m` is an HDOP-based estimate, not a measured receiver accuracy.
- The simulated classification pipeline and configured thresholds have not
  been validated against labeled bus or LMV recordings.
- Compile with the ESP32 Arduino core and required libraries, then test on a
  stationary bench before road use. Confirm every pin, sensor orientation,
  output level, and backend response for the exact board and wiring.
