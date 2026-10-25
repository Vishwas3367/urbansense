#include <WiFi.h>
#include <HTTPClient.h>
#include <Wire.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <DHT.h>
#include <TinyGPSPlus.h>
#include <ArduinoJson.h>
#include <Preferences.h>
#include <time.h>
#include <math.h>
#include <mbedtls/md.h>

const char* WIFI_SSID = "YOUR_WIFI_NAME";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
const char* BACKEND_URL = "http://YOUR_MAC_LAN_IP:8000";
const char* DEVICE_ID = "US-ESP32-001";
const char* DEVICE_SECRET = "PASTE_DEVICE_SECRET_LOCALLY";
const char* API_PATH = "/api/readings";

#define DHT_PIN       4
#define DHT_TYPE      DHT22
#define GPS_RX_PIN    16
#define GPS_TX_PIN    17
#define LED_PIN       19
#define BUZZER_PIN    5
#define BUTTON_PIN    18
constexpr unsigned long SEND_INTERVAL_MS = 5000;
constexpr unsigned long DHT_INTERVAL_MS = 2500;
constexpr uint32_t MPU_SAMPLE_RATE_HZ = 100;
constexpr unsigned long MPU_SAMPLE_INTERVAL_MS = 1000 / MPU_SAMPLE_RATE_HZ;
constexpr size_t MOTION_WINDOW_SAMPLES = 100;
constexpr unsigned long IMPACT_WINDOW_MS = 1000;
constexpr unsigned long MIN_EVENT_SEPARATION_MS = 500;
constexpr float GRAVITY_M_S2 = 9.80665f;
constexpr float INITIAL_IMPACT_THRESHOLD_G = 0.5f;
constexpr float HIGH_IMPACT_THRESHOLD_G = 1.0f;
constexpr float MIN_DETECTION_SPEED_KMH = 10.0f;

// Preliminary offsets assume stationary samples and a level, Z-up mounting.
constexpr float ACCEL_BIAS_X_G = -0.00277f;
constexpr float ACCEL_BIAS_Y_G = 0.01884f;
constexpr float ACCEL_BIAS_Z_G = 0.09398f;
constexpr float GYRO_BIAS_X_DPS = -0.98226f;
constexpr float GYRO_BIAS_Y_DPS = 0.22260f;
constexpr float GYRO_BIAS_Z_DPS = -0.63648f;
constexpr float GRAVITY_FILTER_TAU_SECONDS = 0.5f;
constexpr float MOTION_FILTER_TAU_SECONDS = 0.015f;
constexpr float VERTICAL_ACTIVITY_THRESHOLD_G = 0.15f;

Adafruit_MPU6050 mpu;
DHT dht(DHT_PIN, DHT_TYPE);
TinyGPSPlus gps;
HardwareSerial gpsSerial(2);
Preferences preferences;

struct MotionSample {
  float axG;
  float ayG;
  float azG;
  float gxDps;
  float gyDps;
  float gzDps;
};

struct MotionFeatures {
  float verticalPeakG;
  float verticalRmsG;
  float dynamicRmsG;
  float accelerationPeakG;
  float jerkPeakGS;
  float gyroPeakDps;
  float yawPeakDps;
  uint32_t impactDurationMs;
  uint16_t verticalPeakCount;
  bool biphasic;
  float longitudinalPeakG;
  float lateralPeakG;
};

MotionSample motionSamples[MOTION_WINDOW_SAMPLES];
MotionSample pendingImpactSample;
MotionFeatures pendingImpactFeatures;
size_t motionWriteIndex = 0;
size_t motionSampleCount = 0;
portMUX_TYPE motionMux = portMUX_INITIALIZER_UNLOCKED;

uint32_t nextSequence = 1;
unsigned long lastSendTime = 0;
unsigned long lastDhtReadTime = 0;
float temperatureC = NAN;
float humidityPercent = NAN;
bool mpuAvailable = false;
bool dhtAvailable = false;
bool calibrated = false;
bool manualTriggerPending = false;
volatile float vehicleSpeedKmh = 0.0f;
volatile float latestLatitude = 0.0f;
volatile float latestLongitude = 0.0f;
volatile float latestGpsAccuracyM = NAN;
volatile unsigned long latestGpsFixAt = 0;
float manualTriggerLatitude = 0.0f;
float manualTriggerLongitude = 0.0f;
float manualTriggerSpeedKmh = 0.0f;
float manualTriggerAccuracyM = NAN;
bool manualLocationCaptured = false;
volatile bool impactPending = false;
volatile float impactPeakG = 0.0f;
volatile float impactLatitude = 0.0f;
volatile float impactLongitude = 0.0f;
volatile float impactSpeedKmh = 0.0f;
volatile float impactGpsAccuracyM = NAN;
volatile uint32_t impactGeneration = 0;
portMUX_TYPE impactMux = portMUX_INITIALIZER_UNLOCKED;

void mpuSamplingTask(void* parameter);
void gpsParsingTask(void* parameter);
bool captureMotionFeatures(MotionFeatures& features, MotionSample& latestSample);
void addMotionFeatures(JsonDocument& document, const MotionFeatures& features);

void initializeSequence() {
  preferences.begin("urbansense", false);
  nextSequence = preferences.getUInt("sequence", 1);
  if (nextSequence == 0) {
    nextSequence = 1;
  }
}

uint32_t reserveSequence() {
  if (nextSequence == 0 || nextSequence > 2147483647UL) {
    Serial.println("Sequence reached the backend limit; re-enrollment is required.");
    return 0;
  }
  const uint32_t reserved = nextSequence;
  nextSequence = reserved + 1;
  preferences.putUInt("sequence", nextSequence);
  return reserved;
}

void connectWiFi() {
  if (WiFi.status() == WL_CONNECTED) {
    return;
  }

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.printf("Connecting to Wi-Fi: %s\n", WIFI_SSID);

  const unsigned long startedAt = millis();
  while (WiFi.status() != WL_CONNECTED &&
         millis() - startedAt < 30000) {
    delay(500);
    Serial.print('.');
  }
  Serial.println();

  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("Wi-Fi connected; ESP32 IP: %s\n",
                  WiFi.localIP().toString().c_str());
  } else {
    Serial.println("Wi-Fi connection failed.");
  }
}

void synchronizeTime() {
  configTime(0, 0, "pool.ntp.org", "time.google.com");
  const unsigned long startedAt = millis();
  while (time(nullptr) < 1700000000 &&
         millis() - startedAt < 15000) {
    delay(500);
  }
  Serial.println(time(nullptr) >= 1700000000
                     ? "UTC time synchronized."
                     : "NTP synchronization failed.");
}

String timestampUtc() {
  const time_t now = time(nullptr);
  if (now < 1700000000) {
    return "";
  }

  struct tm timeInfo;
  gmtime_r(&now, &timeInfo);
  char buffer[30];
  strftime(buffer, sizeof(buffer), "%Y-%m-%dT%H:%M:%SZ", &timeInfo);
  return String(buffer);
}

void initializeMpu() {
  if (!mpu.begin()) {
    Serial.println("MPU6050 not detected.");
    return;
  }

  mpuAvailable = true;
  mpu.setAccelerometerRange(MPU6050_RANGE_4_G);
  mpu.setGyroRange(MPU6050_RANGE_500_DEG);
  mpu.setFilterBandwidth(MPU6050_BAND_21_HZ);
  Serial.println("MPU6050 initialized.");
  xTaskCreate(mpuSamplingTask, "mpuSampling", 4096, nullptr, 2, nullptr);
}

void readDht() {
  if (millis() - lastDhtReadTime < DHT_INTERVAL_MS) {
    return;
  }
  lastDhtReadTime = millis();

  const float nextTemperature = dht.readTemperature();
  const float nextHumidity = dht.readHumidity();
  dhtAvailable = !isnan(nextTemperature) && !isnan(nextHumidity);
  if (dhtAvailable) {
    temperatureC = nextTemperature;
    humidityPercent = nextHumidity;
  } else {
    Serial.println("DHT22 reading failed.");
  }
}

bool gpsReady() {
  unsigned long fixAt;
  portENTER_CRITICAL(&impactMux);
  fixAt = latestGpsFixAt;
  portEXIT_CRITICAL(&impactMux);
  return fixAt != 0 && millis() - fixAt < 5000;
}

float gpsAccuracyEstimateM() {
  float accuracy;
  portENTER_CRITICAL(&impactMux);
  accuracy = latestGpsAccuracyM;
  portEXIT_CRITICAL(&impactMux);
  return accuracy;
}

void gpsParsingTask(void* parameter) {
  while (true) {
    while (gpsSerial.available()) {
      gps.encode(gpsSerial.read());
    }

    if (gps.location.isValid() && gps.location.age() < 5000) {
      const float accuracy = gps.hdop.isValid() &&
                                     gps.hdop.hdop() > 0 &&
                                     gps.hdop.hdop() <= 100
                                 ? constrain(gps.hdop.hdop() * 5.0f, 1.0f, 100.0f)
                                 : NAN;
      const float latitude = gps.location.lat();
      const float longitude = gps.location.lng();
      const unsigned long fixAt = millis() - gps.location.age();
      const float speedKmh = gps.speed.isValid() ? gps.speed.kmph() : 0.0f;
      portENTER_CRITICAL(&impactMux);
      latestLatitude = latitude;
      latestLongitude = longitude;
      latestGpsAccuracyM = accuracy;
      latestGpsFixAt = fixAt;
      vehicleSpeedKmh = speedKmh;
      portEXIT_CRITICAL(&impactMux);
    }

    vTaskDelay(pdMS_TO_TICKS(1));
  }
}

String calculateHmac(const String& payload) {
  const mbedtls_md_info_t* info =
      mbedtls_md_info_from_type(MBEDTLS_MD_SHA256);
  if (info == nullptr || DEVICE_SECRET[0] == '\0') {
    Serial.println("HMAC unavailable: check the local device secret.");
    return "";
  }

  unsigned char result[32];
  const int status = mbedtls_md_hmac(
      info,
      reinterpret_cast<const unsigned char*>(DEVICE_SECRET),
      strlen(DEVICE_SECRET),
      reinterpret_cast<const unsigned char*>(payload.c_str()),
      payload.length(),
      result);
  if (status != 0) {
    Serial.printf("HMAC calculation failed: %d\n", status);
    return "";
  }

  char hex[65];
  for (size_t i = 0; i < sizeof(result); ++i) {
    snprintf(hex + i * 2, 3, "%02x", result[i]);
  }
  hex[64] = '\0';
  return String(hex);
}

String sensorStatus() {
  return mpuAvailable ? "NORMAL" : "FAULT";
}

void mpuSamplingTask(void* parameter) {
  TickType_t lastWake = xTaskGetTickCount();
  const TickType_t samplePeriod = pdMS_TO_TICKS(MPU_SAMPLE_INTERVAL_MS);
  unsigned long windowStartedAt = millis();
  float windowPeakG = 0.0f;
  unsigned long lastImpactAt = 0;

  while (true) {
    sensors_event_t acceleration;
    sensors_event_t gyro;
    sensors_event_t mpuTemperature;
    mpu.getEvent(&acceleration, &gyro, &mpuTemperature);

    const float axRawG = acceleration.acceleration.x / GRAVITY_M_S2;
    const float ayRawG = acceleration.acceleration.y / GRAVITY_M_S2;
    const float azRawG = acceleration.acceleration.z / GRAVITY_M_S2;
    const float ax = axRawG - ACCEL_BIAS_X_G;
    const float ay = ayRawG - ACCEL_BIAS_Y_G;
    const float azCorrected = azRawG - ACCEL_BIAS_Z_G;
    const float azDynamic = azCorrected - 1.0f;
    const float peakG = fabsf(azDynamic);
    const MotionSample sample = {
        ax,
        ay,
        azCorrected,
        gyro.gyro.x * 180.0f / PI - GYRO_BIAS_X_DPS,
        gyro.gyro.y * 180.0f / PI - GYRO_BIAS_Y_DPS,
        gyro.gyro.z * 180.0f / PI - GYRO_BIAS_Z_DPS,
    };

    portENTER_CRITICAL(&motionMux);
    motionSamples[motionWriteIndex] = sample;
    motionWriteIndex = (motionWriteIndex + 1) % MOTION_WINDOW_SAMPLES;
    if (motionSampleCount < MOTION_WINDOW_SAMPLES) {
      motionSampleCount++;
    }
    portEXIT_CRITICAL(&motionMux);

    const unsigned long now = millis();
    if (now - windowStartedAt >= IMPACT_WINDOW_MS) {
      windowStartedAt = now;
      windowPeakG = 0.0f;
    }
    if (peakG > windowPeakG) {
      windowPeakG = peakG;
    }

    float speedKmh;
    float latitude;
    float longitude;
    float accuracyM;
    unsigned long fixAt;
    portENTER_CRITICAL(&impactMux);
    speedKmh = vehicleSpeedKmh;
    latitude = latestLatitude;
    longitude = latestLongitude;
    accuracyM = latestGpsAccuracyM;
    fixAt = latestGpsFixAt;
    portEXIT_CRITICAL(&impactMux);
    const bool gpsRecent = fixAt != 0 && now - fixAt < 5000;
    if (windowPeakG >= INITIAL_IMPACT_THRESHOLD_G &&
        speedKmh >= MIN_DETECTION_SPEED_KMH &&
        gpsRecent &&
        (lastImpactAt == 0 || now - lastImpactAt >= MIN_EVENT_SEPARATION_MS)) {
      MotionFeatures eventFeatures;
      MotionSample eventSample;
      if (captureMotionFeatures(eventFeatures, eventSample)) {
        portENTER_CRITICAL(&impactMux);
        if (!impactPending) {
          impactPending = true;
          impactPeakG = eventFeatures.verticalPeakG;
          impactLatitude = latitude;
          impactLongitude = longitude;
          impactSpeedKmh = speedKmh;
          impactGpsAccuracyM = accuracyM;
          pendingImpactFeatures = eventFeatures;
          pendingImpactSample = eventSample;
          impactGeneration++;
        }
        portEXIT_CRITICAL(&impactMux);
      }
      lastImpactAt = now;
      Serial.printf(
          "Potential road impact: %.2f g%s\n",
          windowPeakG,
          windowPeakG >= HIGH_IMPACT_THRESHOLD_G ? " (high impact)" : "");
      windowPeakG = 0.0f;
      windowStartedAt = now;
    }

    vTaskDelayUntil(&lastWake, samplePeriod);
  }
}

bool captureMotionFeatures(MotionFeatures& features, MotionSample& latestSample) {
  MotionSample samples[MOTION_WINDOW_SAMPLES];
  size_t count;
  size_t oldestIndex;

  portENTER_CRITICAL(&motionMux);
  count = motionSampleCount;
  oldestIndex = (motionWriteIndex + MOTION_WINDOW_SAMPLES - count) %
                MOTION_WINDOW_SAMPLES;
  for (size_t index = 0; index < count; ++index) {
    samples[index] = motionSamples[(oldestIndex + index) % MOTION_WINDOW_SAMPLES];
  }
  portEXIT_CRITICAL(&motionMux);

  if (count < 3) {
    return false;
  }

  const float dt = 1.0f / MPU_SAMPLE_RATE_HZ;
  const float gravityAlpha = 1.0f - expf(-dt / GRAVITY_FILTER_TAU_SECONDS);
  const float motionAlpha = dt / (MOTION_FILTER_TAU_SECONDS + dt);
  float gravity[3] = {samples[0].axG, samples[0].ayG, samples[0].azG};
  float filtered[3] = {0.0f, 0.0f, 0.0f};
  float previousDynamic[3] = {0.0f, 0.0f, 0.0f};
  float vertical[MOTION_WINDOW_SAMPLES];
  float longitudinalPeak = 0.0f;
  float lateralPeak = 0.0f;
  float verticalPeak = 0.0f;
  float verticalSquares = 0.0f;
  float dynamicSquares = 0.0f;
  float accelerationPeak = 0.0f;
  float jerkPeak = 0.0f;
  float gyroPeak = 0.0f;
  float yawPeak = 0.0f;
  size_t verticalPeakIndex = 0;
  uint32_t activeSamples = 0;
  uint16_t peakCount = 0;
  bool wasActive = false;

  for (size_t index = 0; index < count; ++index) {
    const float observed[3] = {
        samples[index].axG,
        samples[index].ayG,
        samples[index].azG,
    };
    float dynamic[3];
    float dynamicMagnitudeSquared = 0.0f;
    for (size_t axis = 0; axis < 3; ++axis) {
      gravity[axis] += gravityAlpha * (observed[axis] - gravity[axis]);
      dynamic[axis] = observed[axis] - gravity[axis];
      filtered[axis] += motionAlpha * (dynamic[axis] - filtered[axis]);
      dynamicMagnitudeSquared += filtered[axis] * filtered[axis];
    }

    const float magnitude = sqrtf(dynamicMagnitudeSquared);
    const float verticalValue = filtered[2];
    vertical[index] = verticalValue;
    dynamicSquares += dynamicMagnitudeSquared;
    verticalSquares += verticalValue * verticalValue;
    if (magnitude > accelerationPeak) {
      accelerationPeak = magnitude;
    }
    if (fabsf(filtered[0]) > longitudinalPeak) {
      longitudinalPeak = fabsf(filtered[0]);
    }
    if (fabsf(filtered[1]) > lateralPeak) {
      lateralPeak = fabsf(filtered[1]);
    }
    if (fabsf(verticalValue) > verticalPeak) {
      verticalPeak = fabsf(verticalValue);
      verticalPeakIndex = index;
    }

    if (index > 0) {
      const float dx = filtered[0] - previousDynamic[0];
      const float dy = filtered[1] - previousDynamic[1];
      const float dz = filtered[2] - previousDynamic[2];
      const float jerk = sqrtf(dx * dx + dy * dy + dz * dz) / dt;
      if (jerk > jerkPeak) {
        jerkPeak = jerk;
      }
    }
    for (size_t axis = 0; axis < 3; ++axis) {
      previousDynamic[axis] = filtered[axis];
    }

    const float gyroMagnitude = sqrtf(
        samples[index].gxDps * samples[index].gxDps +
        samples[index].gyDps * samples[index].gyDps +
        samples[index].gzDps * samples[index].gzDps);
    if (gyroMagnitude > gyroPeak) {
      gyroPeak = gyroMagnitude;
    }
    if (fabsf(samples[index].gzDps) > yawPeak) {
      yawPeak = fabsf(samples[index].gzDps);
    }

    const bool active = fabsf(verticalValue) >= VERTICAL_ACTIVITY_THRESHOLD_G;
    activeSamples += active ? 1 : 0;
    if (active && !wasActive) {
      peakCount++;
    }
    wasActive = active;
  }

  const size_t neighborhood = max(
      static_cast<size_t>(1),
      static_cast<size_t>(roundf(0.25f * MPU_SAMPLE_RATE_HZ)));
  const size_t beforeStart =
      verticalPeakIndex > neighborhood ? verticalPeakIndex - neighborhood : 0;
  const size_t afterEnd = min(count, verticalPeakIndex + neighborhood + 1);
  const float peakValue = vertical[verticalPeakIndex];
  bool opposingBefore = false;
  bool opposingAfter = false;
  for (size_t index = beforeStart; index < verticalPeakIndex; ++index) {
    opposingBefore |= peakValue >= 0
                          ? vertical[index] <= -VERTICAL_ACTIVITY_THRESHOLD_G
                          : vertical[index] >= VERTICAL_ACTIVITY_THRESHOLD_G;
  }
  for (size_t index = verticalPeakIndex + 1; index < afterEnd; ++index) {
    opposingAfter |= peakValue >= 0
                         ? vertical[index] <= -VERTICAL_ACTIVITY_THRESHOLD_G
                         : vertical[index] >= VERTICAL_ACTIVITY_THRESHOLD_G;
  }

  features.verticalPeakG = verticalPeak;
  features.verticalRmsG = sqrtf(verticalSquares / count);
  features.dynamicRmsG = sqrtf(dynamicSquares / count);
  features.accelerationPeakG = accelerationPeak;
  features.jerkPeakGS = jerkPeak;
  features.gyroPeakDps = gyroPeak;
  features.yawPeakDps = yawPeak;
  features.impactDurationMs = roundf(activeSamples * dt * 1000.0f);
  features.verticalPeakCount = peakCount;
  features.biphasic = opposingBefore || opposingAfter;
  features.longitudinalPeakG = longitudinalPeak;
  features.lateralPeakG = lateralPeak;
  latestSample = samples[count - 1];
  return true;
}

void addMotionFeatures(JsonDocument& document, const MotionFeatures& features) {
  JsonObject motion = document["motion_features"].to<JsonObject>();
  motion["vertical_peak_g"] = features.verticalPeakG;
  motion["vertical_rms_g"] = features.verticalRmsG;
  motion["dynamic_rms_g"] = features.dynamicRmsG;
  motion["acceleration_peak_g"] = features.accelerationPeakG;
  motion["jerk_peak_g_s"] = features.jerkPeakGS;
  motion["gyro_peak_dps"] = features.gyroPeakDps;
  motion["yaw_peak_dps"] = features.yawPeakDps;
  motion["impact_duration_ms"] = features.impactDurationMs;
  motion["vertical_peak_count"] = features.verticalPeakCount;
  motion["biphasic"] = features.biphasic;
  motion["longitudinal_peak_g"] = features.longitudinalPeakG;
  motion["lateral_peak_g"] = features.lateralPeakG;
}

String createPayload(uint32_t sequence, uint32_t& includedImpactGeneration) {
  bool impactDetected;
  float peakImpactG;
  float eventLatitude;
  float eventLongitude;
  float currentLatitude;
  float currentLongitude;
  float speedKmh;
  float accuracyM;
  float submittedImpactSpeedKmh;
  float submittedImpactAccuracyM;
  MotionFeatures submittedImpactFeatures;
  MotionSample submittedImpactSample;
  portENTER_CRITICAL(&impactMux);
  impactDetected = impactPending;
  includedImpactGeneration = impactGeneration;
  peakImpactG = impactPeakG;
  eventLatitude = impactLatitude;
  eventLongitude = impactLongitude;
  currentLatitude = latestLatitude;
  currentLongitude = latestLongitude;
  speedKmh = vehicleSpeedKmh;
  accuracyM = latestGpsAccuracyM;
  submittedImpactSpeedKmh = impactSpeedKmh;
  submittedImpactAccuracyM = impactGpsAccuracyM;
  submittedImpactFeatures = pendingImpactFeatures;
  submittedImpactSample = pendingImpactSample;
  portEXIT_CRITICAL(&impactMux);

  const String timestamp = timestampUtc();
  if (timestamp.isEmpty()) {
    Serial.println("No valid UTC timestamp.");
    return "";
  }

  MotionFeatures features;
  MotionSample latestSample;
  if (!captureMotionFeatures(features, latestSample)) {
    Serial.println("Waiting for enough MPU6050 samples to analyze motion.");
    return "";
  }
  if (impactDetected) {
    features = submittedImpactFeatures;
    latestSample = submittedImpactSample;
    speedKmh = submittedImpactSpeedKmh;
    accuracyM = submittedImpactAccuracyM;
  }
  const bool manualLocationAvailable =
      manualTriggerPending && manualLocationCaptured;
  if (manualLocationAvailable) {
    speedKmh = manualTriggerSpeedKmh;
    if (isfinite(manualTriggerAccuracyM)) {
      accuracyM = manualTriggerAccuracyM;
    }
  }

  JsonDocument document;
  document["event_id"] = String(DEVICE_ID) + "-" + String(sequence);
  document["sequence_number"] = sequence;
  document["timestamp"] = timestamp;
  document["latitude"] = manualLocationAvailable
                             ? manualTriggerLatitude
                             : impactDetected ? eventLatitude : currentLatitude;
  document["longitude"] = manualLocationAvailable
                              ? manualTriggerLongitude
                              : impactDetected ? eventLongitude : currentLongitude;
  document["ax"] = latestSample.axG;
  document["ay"] = latestSample.ayG;
  document["az"] = latestSample.azG;
  document["speed_kmh"] = speedKmh;
  document["gps_accuracy_m"] = accuracyM;
  document["temperature_c"] = dhtAvailable ? temperatureC : NAN;
  document["humidity_percent"] = dhtAvailable ? humidityPercent : NAN;
  document["sensor_status"] = sensorStatus();
  document["calibrated"] = calibrated;
  document["manual_trigger"] = manualTriggerPending;
  document["impact_detected"] =
      impactDetected || features.verticalPeakG >= INITIAL_IMPACT_THRESHOLD_G;
  document["impact_peak_g"] = impactDetected
                                  ? peakImpactG
                                  : features.verticalPeakG >= INITIAL_IMPACT_THRESHOLD_G
                                        ? features.verticalPeakG
                                        : NAN;
  document["jerk"] = min(features.jerkPeakGS, 100.0f);
  addMotionFeatures(document, features);

  String payload;
  serializeJson(document, payload);
  return payload;
}

void printDecision(const String& response) {
  JsonDocument document;
  const DeserializationError error = deserializeJson(document, response);
  if (error) {
    Serial.printf("Could not parse backend decision: %s\n", error.c_str());
    return;
  }

  const char* decision = document["decision"] | "UNKNOWN";
  Serial.printf("Backend decision: %s\n", decision);
  const char* classification =
      document["event_classification"] | "UNCLASSIFIED";
  Serial.printf("Motion classification: %s\n", classification);
  if (!document["pothole_confidence"].isNull()) {
    Serial.printf(
        "Motion confidence: %d%%\n",
        document["pothole_confidence"].as<int>());
  }
  JsonArray reasons = document["reasons"].as<JsonArray>();
  for (JsonVariant reason : reasons) {
    Serial.printf("Reason: %s\n", reason.as<const char*>());
  }
  if (document["issue"].is<JsonObject>()) {
    const char* issueId = document["issue"]["id"] | "unknown";
    Serial.printf("Created/updated issue: %s\n", issueId);
  }
}

void sendReading() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("Wi-Fi disconnected; reading not sent.");
    return;
  }
  if (!mpuAvailable) {
    Serial.println("MPU6050 unavailable; reading not sent.");
    return;
  }
  if (!gpsReady()) {
    Serial.println("Waiting for a valid, recent GPS fix.");
    return;
  }
  if (isnan(gpsAccuracyEstimateM())) {
    Serial.println("Waiting for a valid GPS HDOP accuracy estimate.");
    return;
  }

  const uint32_t sequence = reserveSequence();
  if (sequence == 0) {
    return;
  }
  uint32_t submittedImpactGeneration;
  const String payload = createPayload(sequence, submittedImpactGeneration);
  if (payload.isEmpty()) {
    return;
  }

  const String signature = calculateHmac(payload);
  if (signature.isEmpty()) {
    return;
  }

  HTTPClient http;
  const String url = String(BACKEND_URL) + API_PATH;
  http.setTimeout(10000);
  if (!http.begin(url)) {
    Serial.println("Could not start HTTP request.");
    return;
  }
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-Device-ID", DEVICE_ID);
  http.addHeader("X-Device-Signature", signature);

  Serial.println("Sending sensor reading...");
  Serial.println(payload);
  const int responseCode = http.POST(payload);
  Serial.printf("HTTP response: %d\n", responseCode);
  const String response = http.getString();
  if (!response.isEmpty()) {
    Serial.println(response);
  }

  if (responseCode == 201) {
    printDecision(response);
    manualTriggerPending = false;
    manualLocationCaptured = false;
    portENTER_CRITICAL(&impactMux);
    if (impactGeneration == submittedImpactGeneration) {
      impactPending = false;
      impactPeakG = 0.0f;
    }
    portEXIT_CRITICAL(&impactMux);
    digitalWrite(LED_PIN, HIGH);
    delay(100);
    digitalWrite(LED_PIN, LOW);
  } else {
    Serial.println("Reading was not processed; check response and backend logs.");
  }
  http.end();
}

void handleButton() {
  static bool previousState = HIGH;
  static unsigned long lastPressAt = 0;
  const bool currentState = digitalRead(BUTTON_PIN);

  if (previousState == HIGH && currentState == LOW &&
      millis() - lastPressAt > 250) {
    lastPressAt = millis();
    manualTriggerPending = true;
    unsigned long fixAt;
    portENTER_CRITICAL(&impactMux);
    manualTriggerLatitude = latestLatitude;
    manualTriggerLongitude = latestLongitude;
    manualTriggerSpeedKmh = vehicleSpeedKmh;
    manualTriggerAccuracyM = latestGpsAccuracyM;
    fixAt = latestGpsFixAt;
    portEXIT_CRITICAL(&impactMux);
    manualLocationCaptured = fixAt != 0 && millis() - fixAt < 5000;
    Serial.println(
        manualLocationCaptured
            ? "Manual pothole signal queued with the current GPS fix."
            : "Manual signal queued; waiting for a valid GPS fix.");
    digitalWrite(LED_PIN, HIGH);
    digitalWrite(BUZZER_PIN, HIGH);
    delay(150);
    digitalWrite(LED_PIN, LOW);
    digitalWrite(BUZZER_PIN, LOW);
  }
  previousState = currentState;
}

void setup() {
  Serial.begin(115200);
  pinMode(LED_PIN, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(BUTTON_PIN, INPUT_PULLUP);
  digitalWrite(LED_PIN, LOW);
  digitalWrite(BUZZER_PIN, LOW);

  Wire.begin(21, 22);
  gpsSerial.begin(9600, SERIAL_8N1, GPS_RX_PIN, GPS_TX_PIN);
  xTaskCreate(gpsParsingTask, "gpsParsing", 4096, nullptr, 2, nullptr);
  initializeSequence();
  initializeMpu();
  dht.begin();
  connectWiFi();
  if (WiFi.status() == WL_CONNECTED) {
    synchronizeTime();
  }
  Serial.printf("UrbanSense ESP32 ready; device ID: %s\n", DEVICE_ID);
}

void loop() {
  readDht();
  handleButton();

  if (WiFi.status() != WL_CONNECTED) {
    connectWiFi();
  }

  if (millis() - lastSendTime >= SEND_INTERVAL_MS) {
    lastSendTime = millis();
    sendReading();
  }
  delay(10);
}
