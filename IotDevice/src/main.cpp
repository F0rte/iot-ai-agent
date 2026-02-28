/*
  ============================================================================
  ESP32-S3 Super Mini
  BLE Wi-Fi Provisioning + Conditional Web OTA + BLE Debug Monitor

  Document: CreatePlan.md v0.1 / SpecifcationDoc.md v0.2
  ============================================================================
*/

#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <Update.h>
#include <Preferences.h>
#include <Wire.h>
#include <time.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>
#include <esp32-hal-rgb-led.h>

// =============================================================================
// Constants & Configuration
// =============================================================================

#ifndef LOG_SERIAL_ENABLED
#define LOG_SERIAL_ENABLED 1
#endif
#define SERIAL_BAUD 115200

// Wi-Fi
#define WIFI_SSID_MAX 32
#define WIFI_PASS_MAX 64

// I2C / MPU6050
#define MPU6050_SDA_PIN 12
#define MPU6050_SCL_PIN 11
#define SENSOR_SEND_INTERVAL_MS 10000
#define SENSOR_ERROR_NOTIFY_INTERVAL_MS 1000
#define ACCEL_BUFFER_SIZE 10

// Status LED (ESP32-S3 Super Mini compatibility)
#define STATUS_LED_GPIO_PIN 47
#define STATUS_LED_RGB_PIN 48

// NVS Namespace
const char *NVS_WIFI_NS = "wifi";
const char *NVS_SYSCFG_NS = "syscfg";

// BLE Debug Service UUID (128-bit from spec)
#define DEBUG_SERVICE_UUID "7f3f0001-6b7c-4f2e-9b8a-1a2b3c4d5e6f"
#define DEBUG_LOG_TX_UUID "7f3f0002-6b7c-4f2e-9b8a-1a2b3c4d5e6f"
#define DEBUG_CMD_RX_UUID "7f3f0003-6b7c-4f2e-9b8a-1a2b3c4d5e6f"
#define DEBUG_STAT_UUID "7f3f0005-6b7c-4f2e-9b8a-1a2b3c4d5e6f"

// BLE Provisioning Service UUID
#define PROV_SERVICE_UUID "8f4f0001-7c8d-5f3e-ac9b-2b3c4d5e6f70"
#define PROV_WIFI_CONFIG_UUID "8f4f0002-7c8d-5f3e-ac9b-2b3c4d5e6f70"

// BLE OTA Service UUID
#define OTA_SERVICE_UUID "9f5f0001-8d9e-6f4e-bd0c-3c4d5e6f7180"
#define OTA_CONTROL_UUID "9f5f0002-8d9e-6f4e-bd0c-3c4d5e6f7180"
#define OTA_DATA_UUID "9f5f0003-8d9e-6f4e-bd0c-3c4d5e6f7180"
#define OTA_STATUS_UUID "9f5f0004-8d9e-6f4e-bd0c-3c4d5e6f7180"

// AWS IoT Core
#define AWS_IOT_ENDPOINT "a12vyeza8y4zmz-ats.iot.ap-northeast-1.amazonaws.com"
#define AWS_IOT_PORT 8883
#define AWS_IOT_TOPIC "hackathon/run/test"
#define AWS_PUBLISH_INTERVAL_MS 5000
#define SENSOR_SAMPLE_INTERVAL_MS 500

const char AWS_ROOT_CA[] PROGMEM = R"EOF(
-----BEGIN CERTIFICATE-----
MIIDQTCCAimgAwIBAgITBmyfz5m/jAo54vB4ikPmljZbyjANBgkqhkiG9w0BAQsF
ADA5MQswCQYDVQQGEwJVUzEPMA0GA1UEChMGQW1hem9uMRkwFwYDVQQDExBBbWF6
b24gUm9vdCBDQSAxMB4XDTE1MDUyNjAwMDAwMFoXDTM4MDExNzAwMDAwMFowOTEL
MAkGA1UEBhMCVVMxDzANBgNVBAoTBkFtYXpvbjEZMBcGA1UEAxMQQW1hem9uIFJv
b3QgQ0EgMTCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBALJ4gHHKeNXj
ca9HgFB0fW7Y14h29Jlo91ghYPl0hAEvrAIthtOgQ3pOsqTQNroBvo3bSMgHFzZM
9O6II8c+6zf1tRn4SWiw3te5djgdYZ6k/oI2peVKVuRF4fn9tBb6dNqcmzU5L/qw
IFAGbHrQgLKm+a/sRxmPUDgH3KKHOVj4utWp+UhnMJbulHheb4mjUcAwhmahRWa6
VOujw5H5SNz/0egwLX0tdHA114gk957EWW67c4cX8jJGKLhD+rcdqsq08p8kDi1L
93FcXmn/6pUCyziKrlA4b9v7LWIbxcceVOF34GfID5yHI9Y/QCB/IIDEgEw+OyQm
jgSubJrIqg0CAwEAAaNCMEAwDwYDVR0TAQH/BAUwAwEB/zAOBgNVHQ8BAf8EBAMC
AYYwHQYDVR0OBBYEFIQYzIU07LwMlJQuCFmcx7IQTgoIMA0GCSqGSIb3DQEBCwUA
A4IBAQCY8jdaQZChGsV2USggNiMOruYou6r4lK5IpDB/G/wkjUu0yKGX9rbxenDI
U5PMCCjjmCXPI6T53iHTfIUJrU6adTrCC2qJeHZERxhlbI1Bjjt/msv0tadQ1wUs
N+gDS63pYaACbvXy8MWy7Vu33PqUXHeeE6V/Uq2V8viTO96LXFvKWlJbYK8U90vv
o/ufQJVtMVT8QtPHRh8jrdkPSHCa2XV4cdFyQzR1bldZwgJcJmApzyMZFo6IQ6XU
5MsI+yMRQ+hDKXJioaldXgjUkK642M4UwtBV8ob2xJNDd2ZhwLnoQdeXeGADbkpy
rqXRfboQnoZsG4q5WTP468SQvvG5
-----END CERTIFICATE-----
)EOF";

const char AWS_DEVICE_CERT[] PROGMEM = R"EOF(
-----BEGIN CERTIFICATE-----
MIIDWTCCAkGgAwIBAgIUUq+5AoVUnk9pVCziw3MDdAqICWgwDQYJKoZIhvcNAQEL
BQAwTTFLMEkGA1UECwxCQW1hem9uIFdlYiBTZXJ2aWNlcyBPPUFtYXpvbi5jb20g
SW5jLiBMPVNlYXR0bGUgU1Q9V2FzaGluZ3RvbiBDPVVTMB4XDTI2MDIyODE1MDEz
NVoXDTQ5MTIzMTIzNTk1OVowHjEcMBoGA1UEAwwTQVdTIElvVCBDZXJ0aWZpY2F0
ZTCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBALApQdZLceUK3yf51SYh
CcXSbTRvQh4peYlxnlwB3aGL6wP+WP0Okh+jR3wSTmHGtFVn3eKzTtAH7bIkt0sW
zQkOV+ptkWq6FbCxmQjCvD9i4RNSn/vc5ltRnwl4XUJOytEo3nJBB5unZ58G5b6U
FMNN87WqveaQOTW3Mlx2sO+13qRN/RApI4t1CR/45SxQul7kNQdUckYgemoyideG
0RwV6MzOwdI3z+dwi2vu1NFmm7H2gprP5xHqrsOvyshyESrQ51se05hRxGKwhz+y
BlcXwG4V7j6tf9UKR04GIzuvHgK5UBlrqjtcczUGEwuxWJWsEtCyElb8Soo8xMK0
GS0CAwEAAaNgMF4wHwYDVR0jBBgwFoAULzmlO16iAH79tGOK7XrWfZ2KUCEwHQYD
VR0OBBYEFASDgWs3SKct8nvD49DkIikinGo3MAwGA1UdEwEB/wQCMAAwDgYDVR0P
AQH/BAQDAgeAMA0GCSqGSIb3DQEBCwUAA4IBAQA/g0te0o2cFUAE5PdHXPiiqAsp
UVot8QYW90xDwEqCwo8XE86heItvjtrJHm2rNbuf32qI6ereYq1+7hxG8ksVKUCq
vbHdegcqER6A4gvQW96ydUTY/JCc7dbEENj61oVFGyMUUT+J4JBfMUzcvL/Ohnh+
UinEaHAfrlwMH+2I+1b4bQ6kzbutLfFxGIGSral5XsSljQYlkHRe2Q2GK+wXdC07
+uRKxU4+bPhmSxH01CCoLSfRkrnqHoUQDA73kUGfoQxQQYYk/qxyI+vXyY6QEIGv
69lTJp6CD/CJxz806F/nxNR82c1nJHnQ6Z1z4GsjYDNZtqmbH+6DUJHg+wcg
-----END CERTIFICATE-----
)EOF";

const char AWS_PRIVATE_KEY[] PROGMEM = R"EOF(
-----BEGIN RSA PRIVATE KEY-----
MIIEpQIBAAKCAQEAsClB1ktx5QrfJ/nVJiEJxdJtNG9CHil5iXGeXAHdoYvrA/5Y
/Q6SH6NHfBJOYca0VWfd4rNO0AftsiS3SxbNCQ5X6m2RaroVsLGZCMK8P2LhE1Kf
+9zmW1GfCXhdQk7K0SjeckEHm6dnnwblvpQUw03ztaq95pA5NbcyXHaw77XepE39
ECkji3UJH/jlLFC6XuQ1B1RyRiB6ajKJ14bRHBXozM7B0jfP53CLa+7U0WabsfaC
ms/nEequw6/KyHIRKtDnWx7TmFHEYrCHP7IGVxfAbhXuPq1/1QpHTgYjO68eArlQ
GWuqO1xzNQYTC7FYlawS0LISVvxKijzEwrQZLQIDAQABAoIBAQCa93BHR48l4e51
iD2NkTq7n2UZ31XWmr2jvyOD5NBHMILJvJIj6xF4a3aTGreBI/+3setrZjlKn+7l
646iq6gq80c7nq9xp8k06sapAkX/rMg661B5i9XJN4AkIJJJpm6cmMs2zyYWM6ng
J30rrbCmLojZox3zGaR6MHJJDNCRzYFN7gFAvbhdCfrx+2ddQZc0khYnRMMIgL+U
u/JoRd4XYjGDwLuYWz1XfC4uiwNs9uTtRv7y58tA/uclZJAZSN9jcGxX2DMXmbXE
eSDRRWbrtND6X1nZ8uyhdtnkhqOZ19Ip4eW/3KbmoPA8g1CfUZ6zSN2J40em7Aqd
QLa7XZoxAoGBAOOEwSggsei1u2aiZdooq0Ht7ueyitH7S6108z1fQitrsA1W0n9m
UDedIjIWTaUqG+CJBlHhGbebXsSfc86hUP8Znvb/Y2jE/HprZH55rcMUdgN36I4C
PrfWzRBt5UqFBQC/Mxve45Adax2PvqdUvYYir1ToPh6H90UzwNjfoJ2bAoGBAMY2
qUWfGTG6hYELmsf6fq1BTDdIaZiPciI+SR/wrH1YuYLWwldgIkEfDKicXo2Ybsv6
wg/krtKMQnOQFbzAw5HcjNOi6zN7FtmvMHHOSKUEGAc+reGSQQiFEiCRy/HhOWX0
e/UGSKCF9MkOE0Rp+xhtKdFGG2KveeLkXiurSPTXAoGAdj8P2JgtfsG81RnAD8Ml
Rs2vZdIgXgPaEBuBM7tne4OrazNdkYMOW+kZ1ahL0HRzKp5sn297Wzav6Ubp/FFQ
9FRPjxWqh9AhXEqmXylESug+cY0HW48FI6zKxSgojDNYJ0w39ts/sC3p9uI3d2YO
XkF2mI1fg6SsudWs+8o2AtMCgYEAvKWteSuw6Nli0qzexVGtWuv4w+zRQ3fS4rBx
HEsNf8b/2HzZPhuqvlv0ykz42L6pRM4GAOZfVNhVLnOFnL3B5IMKLSqzu6180/We
n9H65cL9s3d+Ol/eMWOlGwZoGm+HF3gWud8fJFgZ33jb8ZMEffz3fcvBqKzlzoIW
9mzw5MUCgYEAzwl49lLQCIxAFtVvy9MGw67xl1FSlV36+D5HI4YOO1WxbQfn71NU
157dh0fa3Cw7droDBEyfw+WOlSOhXp4yyzaBFPOZpma/KlTP5uMsFF/FHOhkxSR8
azBOs4rd3zq+aN9JU/7z2SnJhpEAIg1dcwaecibefHopMvcs7p48/7I=
-----END RSA PRIVATE KEY-----
)EOF";

// =============================================================================
// Global Variables
// =============================================================================

Preferences nvs_wifi;
Preferences nvs_syscfg;

// State
typedef enum
{
    STATE_FACTORY_RESET_DETECT,
    STATE_PROVISIONING,
    STATE_APP_RUNNING,
} system_state_t;

typedef enum
{
    WIFI_IDLE = 0,
    WIFI_CONNECTING,
    WIFI_CONNECTED,
    WIFI_FAILED,
} wifi_state_t;

struct
{
    system_state_t system_state;
    wifi_state_t wifi_state;
    char wifi_ip[16];
    char device_name[32];
} g_state = {STATE_FACTORY_RESET_DETECT, WIFI_IDLE, "", ""};

// BLE
BLEServer *pServer = NULL;
BLECharacteristic *pDebugLogTx = NULL;
BLECharacteristic *pDebugCmdRx = NULL;
BLECharacteristic *pDebugStat = NULL;
BLECharacteristic *pProvWifiConfig = NULL;
BLECharacteristic *pOtaControl = NULL;
BLECharacteristic *pOtaData = NULL;
BLECharacteristic *pOtaStatus = NULL;

// OTA via BLE state
bool ota_mode_active = false;
size_t ota_expected_size = 0;
size_t ota_received_size = 0;
size_t ota_last_reported_size = 0;
bool ota_in_progress = false;
bool ota_finalize_requested = false;
bool ota_abort_requested = false;

void status_led_init()
{
    pinMode(STATUS_LED_GPIO_PIN, OUTPUT);
    digitalWrite(STATUS_LED_GPIO_PIN, HIGH);
    neopixelWrite(STATUS_LED_RGB_PIN, 0, 0, 0);
}

void status_led_blink_aws()
{
    digitalWrite(STATUS_LED_GPIO_PIN, LOW);
    neopixelWrite(STATUS_LED_RGB_PIN, 0, 24, 0);
    delay(120);
    digitalWrite(STATUS_LED_GPIO_PIN, HIGH);
    neopixelWrite(STATUS_LED_RGB_PIN, 0, 0, 0);
}

bool ble_device_connected = false;

Adafruit_MPU6050 mpu;
bool mpu_initialized = false;

void log_println(const char *msg);

WiFiClientSecure aws_secure_client;
PubSubClient aws_mqtt_client(aws_secure_client);
bool aws_client_initialized = false;
unsigned long last_aws_connect_try = 0;
unsigned long last_aws_publish_time = 0;
String last_activity_status = "None";
bool has_last_activity_status = false;
char aws_client_id[48] = {0};

// Acceleration buffer for averaging (10 samples every 0.5s = 5 seconds)
float accel_magnitude_buffer[ACCEL_BUFFER_SIZE] = {0.0f};
int accel_buffer_index = 0;

const unsigned long AWS_RECONNECT_INTERVAL_MS = 5000;

const char *activity_status_from_magnitude(float accel_magnitude)
{
    if (accel_magnitude > 30.0f)
    {
        return "Run";
    }

    if (accel_magnitude > 20.0f)
    {
        return "Walk";
    }

    return "None";
}

void aws_iot_init(void)
{
    if (aws_client_initialized)
    {
        return;
    }

    // Generate unique client ID from MAC address
    uint8_t mac[6];
    WiFi.macAddress(mac);
    snprintf(aws_client_id, sizeof(aws_client_id), "esp32-%02x%02x%02x%02x%02x%02x",
             mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);

    char id_log[96];
    snprintf(id_log, sizeof(id_log), "[AWS] Client ID: %s", aws_client_id);
    log_println(id_log);

    log_println("[AWS] Setting up secure client certificates...");
    aws_secure_client.setCACert(AWS_ROOT_CA);
    aws_secure_client.setCertificate(AWS_DEVICE_CERT);
    aws_secure_client.setPrivateKey(AWS_PRIVATE_KEY);

    // Set timeouts to prevent hanging
    aws_secure_client.setTimeout(5000);        // 5 second socket timeout
    aws_secure_client.setHandshakeTimeout(15); // 15 second handshake timeout

    log_println("[AWS] Configuring MQTT client...");
    aws_mqtt_client.setServer(AWS_IOT_ENDPOINT, AWS_IOT_PORT);
    aws_mqtt_client.setSocketTimeout(5); // 5 second MQTT timeout
    aws_mqtt_client.setKeepAlive(30);    // 30 second keepalive

    aws_client_initialized = true;
    log_println("[AWS] MQTT client initialized");
}

void aws_iot_connect_if_needed(void)
{
    if (g_state.wifi_state != WIFI_CONNECTED)
    {
        return;
    }

    if (!aws_client_initialized)
    {
        aws_iot_init();
    }

    if (aws_mqtt_client.connected())
    {
        return;
    }

    if (millis() - last_aws_connect_try < AWS_RECONNECT_INTERVAL_MS)
    {
        return;
    }
    last_aws_connect_try = millis();

    char connect_msg[128];
    snprintf(connect_msg, sizeof(connect_msg), "[AWS] Attempting connection with client ID: %s", aws_client_id);
    log_println(connect_msg);

    char endpoint_msg[128];
    snprintf(endpoint_msg, sizeof(endpoint_msg), "[AWS] Endpoint: %s:%d", AWS_IOT_ENDPOINT, AWS_IOT_PORT);
    log_println(endpoint_msg);

    log_println("[AWS] Starting TLS handshake...");

    unsigned long connect_start = millis();
    bool connected = aws_mqtt_client.connect(aws_client_id);
    unsigned long connect_duration = millis() - connect_start;

    char duration_msg[64];
    snprintf(duration_msg, sizeof(duration_msg), "[AWS] Connect attempt took %lu ms", connect_duration);
    log_println(duration_msg);

    if (connected)
    {
        log_println("[AWS] Successfully connected to AWS IoT Core");
    }
    else
    {
        int state = aws_mqtt_client.state();
        char err[128];
        snprintf(err, sizeof(err), "[AWS] Connection failed: state=%d", state);
        log_println(err);

        // Decode error state
        const char *state_desc = "UNKNOWN";
        switch (state)
        {
        case -4:
            state_desc = "TIMEOUT";
            break;
        case -3:
            state_desc = "CONNECTION_LOST";
            break;
        case -2:
            state_desc = "CONNECT_FAILED";
            break;
        case -1:
            state_desc = "DISCONNECTED";
            break;
        case 1:
            state_desc = "PROTOCOL_VERSION";
            break;
        case 2:
            state_desc = "CLIENT_ID_REJECTED";
            break;
        case 3:
            state_desc = "SERVER_UNAVAILABLE";
            break;
        case 4:
            state_desc = "BAD_CREDENTIALS";
            break;
        case 5:
            state_desc = "NOT_AUTHORIZED";
            break;
        }

        char state_msg[96];
        snprintf(state_msg, sizeof(state_msg), "[AWS] Error: %s", state_desc);
        log_println(state_msg);

        // Explicitly disconnect secure client to reset state
        aws_secure_client.stop();
    }
}

bool aws_iot_publish_sensor(float accel_magnitude, const char *status, bool status_changed)
{
    if (!aws_mqtt_client.connected())
    {
        return false;
    }

    // Get current time in ISO 8601 format
    time_t now = time(nullptr);
    struct tm *timeinfo = gmtime(&now);
    char iso8601[32];
    strftime(iso8601, sizeof(iso8601), "%Y-%m-%dT%H:%M:%SZ", timeinfo);

    JsonDocument doc;
    doc["status"] = status;
    doc["bpm"] = accel_magnitude;
    doc["timestamp"] = iso8601;
    doc["device_id"] = g_state.device_name;

    char payload[256];
    size_t payload_len = serializeJson(doc, payload, sizeof(payload));
    if (payload_len == 0)
    {
        log_println("[AWS] Failed to serialize JSON payload");
        return false;
    }

    char reason[32];
    snprintf(reason, sizeof(reason), "%s", status_changed ? "STATUS_CHANGE" : "INTERVAL");

    char prelog[128];
    snprintf(prelog, sizeof(prelog), "[AWS][BLE] Publish reason=%s status=%s bpm=%.3f",
             reason, status, accel_magnitude);
    log_println(prelog);

    bool published = aws_mqtt_client.publish(AWS_IOT_TOPIC, payload);
    if (published)
    {
        char oklog[128];
        snprintf(oklog, sizeof(oklog), "[AWS][BLE] Publish success topic=%s", AWS_IOT_TOPIC);
        log_println(oklog);
    }
    else
    {
        char nglog[128];
        snprintf(nglog, sizeof(nglog), "[AWS][BLE] Publish failed state=%d", aws_mqtt_client.state());
        log_println(nglog);
    }

    return published;
}

// =============================================================================
// Utility Functions
// =============================================================================

void log_println(const char *msg)
{
    if (LOG_SERIAL_ENABLED)
    {
        Serial.println(msg);
        Serial.flush();
    }

    // Send via BLE if connected (real-time only) - but NOT during OTA
    if (ble_device_connected && pDebugLogTx && !ota_in_progress)
    {
        size_t len = strlen(msg);
        if (len > 0)
        {
            // BLE can send up to 512 bytes, but keep it safe at 200
            if (len > 200)
                len = 200;
            pDebugLogTx->setValue((uint8_t *)msg, len);
            pDebugLogTx->notify();
            delay(10); // Small delay to avoid overwhelming BLE stack
        }
    }
}

void wifi_mgr_init(void)
{
    // Initialize Wi-Fi manager (non-blocking setup)
    WiFi.mode(WIFI_STA);
    g_state.wifi_state = WIFI_IDLE;
}

esp_err_t wifi_mgr_connect(void)
{
    if (g_state.wifi_state == WIFI_CONNECTING || g_state.wifi_state == WIFI_CONNECTED)
    {
        return ESP_OK;
    }

    char ssid[WIFI_SSID_MAX] = {0};
    char pass[WIFI_PASS_MAX] = {0};

    nvs_wifi.begin(NVS_WIFI_NS, true);
    size_t ssid_len = nvs_wifi.getString("ssid", ssid, sizeof(ssid));
    size_t pass_len = nvs_wifi.getString("pass", pass, sizeof(pass));
    nvs_wifi.end();

    if (ssid_len == 0)
    {
        log_println("[E] No Wi-Fi config found");
        g_state.wifi_state = WIFI_FAILED;
        return ESP_FAIL;
    }

    // Debug: Show what we're trying to connect to
    char debug_msg[128];
    snprintf(debug_msg, sizeof(debug_msg), "[I] Connecting to SSID: '%s' (len=%d, pass_len=%d)",
             ssid, ssid_len, pass_len);
    log_println(debug_msg);

    log_println("[I] Starting Wi-Fi connection...");
    g_state.wifi_state = WIFI_CONNECTING;

    WiFi.begin(ssid, pass);
    return ESP_OK;
}

bool wifi_mgr_is_connected(void)
{
    return g_state.wifi_state == WIFI_CONNECTED;
}

const char *wifi_mgr_get_ip_str(void)
{
    return g_state.wifi_ip;
}

bool sensor_init_mpu6050(void)
{
    Wire.begin(MPU6050_SDA_PIN, MPU6050_SCL_PIN);

    if (!mpu.begin())
    {
        log_println("[E] MPU6050 not found. Check wiring and power");
        return false;
    }

    mpu.setAccelerometerRange(MPU6050_RANGE_8_G);
    mpu.setGyroRange(MPU6050_RANGE_500_DEG);
    mpu.setFilterBandwidth(MPU6050_BAND_21_HZ);

    log_println("[I] MPU6050 initialized");
    return true;
}

// =============================================================================
// BLE Callback Classes
// =============================================================================

class MyServerCallbacks : public BLEServerCallbacks
{
    void onConnect(BLEServer *pServer)
    {
        ble_device_connected = true;
        log_println("[I] BLE device connected");

        // Send initial status immediately on connection
        delay(100); // Give BLE stack time to settle

        char status[128];
        snprintf(status, sizeof(status), "[STATUS] MPU6050=%s, WIFI=%d, OTA=%s",
                 mpu_initialized ? "OK" : "NOT_FOUND",
                 g_state.wifi_state,
                 ota_mode_active ? "ACTIVE" : "IDLE");
        log_println(status);
    }

    void onDisconnect(BLEServer *pServer)
    {
        ble_device_connected = false;
        log_println("[I] BLE device disconnected");
    }
};

class MyCharacteristicCallbacks : public BLECharacteristicCallbacks
{
    void onWrite(BLECharacteristic *pCharacteristic)
    {
        std::string rxValue = pCharacteristic->getValue();
        if (rxValue.length() > 0)
        {
            String command = String(rxValue.c_str());
            command.trim();

            // Log via BLE as well
            char ble_log[128];
            snprintf(ble_log, sizeof(ble_log), "[BLE RX] %s", command.c_str());
            log_println(ble_log);
            Serial.println("[BLE RX] Command received via Serial");

            // Handle special commands
            if (command == "RESET_NVS" || command == "FACTORY_RESET")
            {
                log_println("[I] Factory reset requested via BLE");
                log_println("[I] Clearing NVS...");

                // Clear all NVS namespaces
                nvs_wifi.begin(NVS_WIFI_NS, false);
                nvs_wifi.clear();
                nvs_wifi.end();

                nvs_syscfg.begin(NVS_SYSCFG_NS, false);
                nvs_syscfg.clear();
                nvs_syscfg.end();

                log_println("[I] NVS cleared. Rebooting in 2 seconds...");
                delay(2000);
                ESP.restart();
            }
            else if (command == "STATUS")
            {
                log_println("[I] Status requested");
                char msg[128];
                snprintf(msg, sizeof(msg), "[I] STATE=%d,WIFI=%d,OTA_MODE=%d,IP=%s",
                         g_state.system_state, g_state.wifi_state, ota_mode_active ? 1 : 0, g_state.wifi_ip);
                log_println(msg);
            }
            else if (command == "OTA_MODE")
            {
                log_println("[I] OTA mode activation requested via BLE");
                ota_mode_active = true;
                log_println("[I] OTA mode activated - ready to receive firmware data");
            }
        }
    }
};

class ProvisioningCallbacks : public BLECharacteristicCallbacks
{
    void onWrite(BLECharacteristic *pCharacteristic)
    {
        std::string rxValue = pCharacteristic->getValue();
        if (rxValue.length() == 0)
        {
            log_println("[E] Empty provisioning data");
            return;
        }

        // Format: SSID\nPassword (separated by newline)
        String data = String(rxValue.c_str());
        int separatorIndex = data.indexOf('\n');

        if (separatorIndex == -1)
        {
            log_println("[E] Invalid provisioning format (no separator)");
            return;
        }

        String ssid = data.substring(0, separatorIndex);
        String password = data.substring(separatorIndex + 1);

        if (ssid.length() == 0 || ssid.length() > WIFI_SSID_MAX)
        {
            log_println("[E] Invalid SSID length");
            return;
        }

        if (password.length() > WIFI_PASS_MAX)
        {
            log_println("[E] Invalid password length");
            return;
        }

        log_println("[I] Received Wi-Fi credentials via BLE");

        // Log SSID and lengths (via BLE too)
        char ssid_info[128];
        snprintf(ssid_info, sizeof(ssid_info), "[I] SSID: %s", ssid.c_str());
        log_println(ssid_info);

        char len_info[64];
        snprintf(len_info, sizeof(len_info), "[I] SSID length: %d", ssid.length());
        log_println(len_info);

        snprintf(len_info, sizeof(len_info), "[I] Password length: %d", password.length());
        log_println(len_info);

        // Save to NVS
        nvs_wifi.begin(NVS_WIFI_NS, false);
        nvs_wifi.putString("ssid", ssid.c_str());
        nvs_wifi.putString("pass", password.c_str());
        nvs_wifi.end();

        // Verify what was saved
        char verify_ssid[WIFI_SSID_MAX] = {0};
        nvs_wifi.begin(NVS_WIFI_NS, true);
        size_t verify_len = nvs_wifi.getString("ssid", verify_ssid, sizeof(verify_ssid));
        nvs_wifi.end();

        char verify_info[128];
        snprintf(verify_info, sizeof(verify_info), "[I] Verified saved SSID: %s", verify_ssid);
        log_println(verify_info);

        snprintf(verify_info, sizeof(verify_info), "[I] Verified SSID length: %d", verify_len);
        log_println(verify_info);

        // Mark as provisioned
        nvs_syscfg.begin(NVS_SYSCFG_NS, false);
        nvs_syscfg.putUChar("prov", 1);
        nvs_syscfg.end();

        log_println("[I] Wi-Fi config saved! Connecting to Wi-Fi...");

        // Update state and start WiFi connection
        g_state.system_state = STATE_PROVISIONING;

        // Add small delay before attempting connection
        delay(500);
        wifi_mgr_connect();
    }
};

// =============================================================================
// BLE OTA Callbacks
// =============================================================================

class OtaControlCallbacks : public BLECharacteristicCallbacks
{
    void onWrite(BLECharacteristic *pCharacteristic)
    {
        std::string rxValue = pCharacteristic->getValue();
        if (rxValue.length() == 0)
        {
            log_println("[E] Empty OTA control data");
            return;
        }

        String command = String(rxValue.c_str());
        command.trim();

        String msg = "[OTA] Control command: " + command;
        log_println(msg.c_str());

        // Format: START:<size> or END
        if (command.startsWith("START:"))
        {
            size_t size = command.substring(6).toInt();
            if (size == 0 || size > 2000000) // Max 2MB
            {
                log_println("[E] Invalid OTA size");
                if (pOtaStatus)
                {
                    pOtaStatus->setValue("ERROR:INVALID_SIZE");
                    pOtaStatus->notify();
                }
                return;
            }

            log_println("[OTA] Starting OTA update...");
            Serial.printf("[OTA] Expected size: %u bytes\n", size);

            ota_expected_size = size;
            ota_received_size = 0;
            ota_last_reported_size = 0;
            ota_in_progress = true;
            ota_finalize_requested = false;
            ota_abort_requested = false;

            if (!Update.begin(size, U_FLASH))
            {
                Update.printError(Serial);
                log_println("[E] Update.begin() failed");
                ota_in_progress = false;
                if (pOtaStatus)
                {
                    pOtaStatus->setValue("ERROR:BEGIN_FAILED");
                    pOtaStatus->notify();
                }
                return;
            }

            log_println("[I] OTA update started successfully");
            if (pOtaStatus)
            {
                pOtaStatus->setValue("READY");
                pOtaStatus->notify();
            }
        }
        else if (command == "END")
        {
            if (!ota_in_progress)
            {
                log_println("[E] OTA not in progress");
                if (pOtaStatus)
                {
                    pOtaStatus->setValue("ERROR:NOT_STARTED");
                    pOtaStatus->notify();
                }
                return;
            }

            if (ota_received_size != ota_expected_size)
            {
                char err[64];
                snprintf(err, sizeof(err), "[E] OTA incomplete: %u / %u", ota_received_size, ota_expected_size);
                log_println(err);
                if (pOtaStatus)
                {
                    pOtaStatus->setValue("ERROR:INCOMPLETE");
                    pOtaStatus->notify();
                }
                return;
            }

            log_println("[OTA] Finalize requested - will process in main loop");
            ota_finalize_requested = true;
        }
        else if (command == "ABORT")
        {
            log_println("[W] OTA abort requested by user");
            ota_abort_requested = true;
        }
    }
};

class OtaDataCallbacks : public BLECharacteristicCallbacks
{
    void onWrite(BLECharacteristic *pCharacteristic)
    {
        if (!ota_in_progress)
        {
            log_println("[E] OTA not started, ignoring data");
            return;
        }

        std::string rxValue = pCharacteristic->getValue();
        size_t len = rxValue.length();

        if (len == 0)
        {
            log_println("[E] Empty OTA data packet");
            return;
        }

        if (ota_received_size + len > ota_expected_size)
        {
            log_println("[E] OTA data overflow (received more than expected)");
            Update.abort();
            ota_in_progress = false;
            ota_mode_active = false;

            if (pOtaStatus)
            {
                pOtaStatus->setValue("ERROR:OVERFLOW");
                pOtaStatus->notify();
            }
            return;
        }

        // Write data to flash
        size_t written = Update.write((uint8_t *)rxValue.data(), len);
        if (written != len)
        {
            Update.printError(Serial);
            log_println("[E] OTA write failed");
            Update.abort();
            ota_in_progress = false;

            if (pOtaStatus)
            {
                pOtaStatus->setValue("ERROR:WRITE_FAILED");
                pOtaStatus->notify();
            }
            return;
        }

        ota_received_size += written;

        // Progress notification every 100KB or at completion (reduce overhead)
        if (ota_received_size - ota_last_reported_size >= 102400 || ota_received_size == ota_expected_size)
        {
            ota_last_reported_size = ota_received_size;
            Serial.printf("[OTA] Progress: %u / %u bytes (%.1f%%)\n",
                          ota_received_size, ota_expected_size,
                          (ota_received_size * 100.0) / ota_expected_size);

            // Only notify progress occasionally to reduce BLE stack load
            if (pOtaStatus && (ota_received_size % 204800 == 0 || ota_received_size == ota_expected_size))
            {
                char progress[32];
                snprintf(progress, sizeof(progress), "PROGRESS:%u/%u",
                         ota_received_size, ota_expected_size);
                pOtaStatus->setValue(progress);
                pOtaStatus->notify();
            }
        }
    }
};

// =============================================================================
// BLE Setup
// =============================================================================

void setup_ble_debug_service(void)
{
    BLEService *pService = pServer->createService(DEBUG_SERVICE_UUID);

    // DebugLogTx (Notify)
    pDebugLogTx = pService->createCharacteristic(
        DEBUG_LOG_TX_UUID,
        BLECharacteristic::PROPERTY_NOTIFY);
    pDebugLogTx->addDescriptor(new BLE2902());

    // DebugCmdRx (Write)
    pDebugCmdRx = pService->createCharacteristic(
        DEBUG_CMD_RX_UUID,
        BLECharacteristic::PROPERTY_WRITE |
            BLECharacteristic::PROPERTY_WRITE_NR);
    pDebugCmdRx->setCallbacks(new MyCharacteristicCallbacks());

    // DebugStat (Read/Notify)
    pDebugStat = pService->createCharacteristic(
        DEBUG_STAT_UUID,
        BLECharacteristic::PROPERTY_READ |
            BLECharacteristic::PROPERTY_NOTIFY);
    pDebugStat->addDescriptor(new BLE2902());

    pService->start();
}

void setup_ble_provisioning_service(void)
{
    BLEService *pProvService = pServer->createService(PROV_SERVICE_UUID);

    // WiFi Config (Write)
    pProvWifiConfig = pProvService->createCharacteristic(
        PROV_WIFI_CONFIG_UUID,
        BLECharacteristic::PROPERTY_WRITE |
            BLECharacteristic::PROPERTY_WRITE_NR);
    pProvWifiConfig->setCallbacks(new ProvisioningCallbacks());

    pProvService->start();
    log_println("[I] BLE Provisioning service started");
}

void setup_ble_ota_service(void)
{
    BLEService *pOtaService = pServer->createService(OTA_SERVICE_UUID);

    // OTA Control (Write) - for START, END, ABORT commands
    pOtaControl = pOtaService->createCharacteristic(
        OTA_CONTROL_UUID,
        BLECharacteristic::PROPERTY_WRITE |
            BLECharacteristic::PROPERTY_WRITE_NR);
    pOtaControl->setCallbacks(new OtaControlCallbacks());

    // OTA Data (Write) - for firmware binary data
    pOtaData = pOtaService->createCharacteristic(
        OTA_DATA_UUID,
        BLECharacteristic::PROPERTY_WRITE |
            BLECharacteristic::PROPERTY_WRITE_NR);
    pOtaData->setCallbacks(new OtaDataCallbacks());
    pOtaData->setValue((uint8_t *)"", 0); // Initialize empty

    // OTA Status (Read/Notify) - for progress and status updates
    pOtaStatus = pOtaService->createCharacteristic(
        OTA_STATUS_UUID,
        BLECharacteristic::PROPERTY_READ |
            BLECharacteristic::PROPERTY_NOTIFY);
    pOtaStatus->addDescriptor(new BLE2902());
    pOtaStatus->setValue("IDLE");

    pOtaService->start();
    log_println("[I] BLE OTA service started");
}

void init_ble(void)
{
    log_println("[I] Starting BLE device init...");
    BLEDevice::init("ESP32-S3-MICON");

    // Request larger MTU for better OTA throughput
    BLEDevice::setMTU(517);

    log_println("[I] BLE device initialized");

    delay(100);

    log_println("[I] Creating BLE server...");
    pServer = BLEDevice::createServer();
    pServer->setCallbacks(new MyServerCallbacks());
    log_println("[I] BLE server created");

    log_println("[I] Setting up debug service...");
    setup_ble_debug_service();
    log_println("[I] Debug service ready");

    // Setup OTA service (always available)
    log_println("[I] Setting up OTA service...");
    setup_ble_ota_service();

    // Setup provisioning service (always available for WiFi re-provisioning during operation)
    log_println("[I] Setting up provisioning service...");
    setup_ble_provisioning_service();

    log_println("[I] Starting advertising...");
    BLEAdvertising *pAdvertising = BLEDevice::getAdvertising();
    pAdvertising->addServiceUUID(DEBUG_SERVICE_UUID);
    pAdvertising->addServiceUUID(OTA_SERVICE_UUID);
    pAdvertising->addServiceUUID(PROV_SERVICE_UUID); // Always advertise provisioning service
    pAdvertising->setScanResponse(true);
    pAdvertising->setMinPreferred(0x06);
    pAdvertising->setMaxPreferred(0x12);
    BLEDevice::startAdvertising();

    log_println("[I] BLE initialized successfully");
}

// =============================================================================
// Factory Reset / NVS Management
// =============================================================================

void config_store_init(void)
{
    nvs_wifi.begin(NVS_WIFI_NS, false);
    nvs_syscfg.begin(NVS_SYSCFG_NS, false);
}

void config_store_check_provisioned(void)
{
    nvs_wifi.begin(NVS_WIFI_NS, true);
    uint8_t is_provisioned = nvs_wifi.getUChar("prov", 0);
    nvs_wifi.end();

    if (is_provisioned)
    {
        log_println("[I] Wi-Fi config found, entering APP mode");
        g_state.system_state = STATE_APP_RUNNING;
    }
    else
    {
        log_println("[I] No Wi-Fi config, entering PROVISIONING mode");
        g_state.system_state = STATE_PROVISIONING;
    }
}

void factory_reset_check(void)
{
    // Simplified: Check if BOOT button held for 3 seconds
    // In real implementation, use GPIO interrupt
    // For now, just check a flag in preferences

    nvs_syscfg.begin(NVS_SYSCFG_NS, true);
    uint8_t factory_reset_flag = nvs_syscfg.getUChar("factory_reset", 0);
    nvs_syscfg.end();

    if (factory_reset_flag)
    {
        log_println("[W] Factory reset triggered!");
        nvs_wifi.begin(NVS_WIFI_NS, false);
        nvs_wifi.clear();
        nvs_wifi.end();

        nvs_syscfg.begin(NVS_SYSCFG_NS, false);
        nvs_syscfg.putUChar("factory_reset", 0);
        nvs_syscfg.end();

        log_println("[I] NVS cleared, rebooting...");
        delay(1000);
        ESP.restart();
    }
}

// =============================================================================
// Wi-Fi Event Handler
// =============================================================================

void wifi_event_handler(WiFiEvent_t event)
{
    switch (event)
    {
    case ARDUINO_EVENT_WIFI_STA_CONNECTED:
        log_println("[I] Wi-Fi connected");
        break;

    case ARDUINO_EVENT_WIFI_STA_GOT_IP:
    {
        g_state.wifi_state = WIFI_CONNECTED;
        IPAddress ip = WiFi.localIP();
        snprintf(g_state.wifi_ip, sizeof(g_state.wifi_ip), "%d.%d.%d.%d",
                 ip[0], ip[1], ip[2], ip[3]);

        char msg[64];
        snprintf(msg, sizeof(msg), "[I] Got IP: %s", g_state.wifi_ip);
        log_println(msg);

        // If in provisioning mode, mark as provisioned
        if (g_state.system_state == STATE_PROVISIONING)
        {
            nvs_wifi.begin(NVS_WIFI_NS, false);
            nvs_wifi.putUChar("prov", 1);
            nvs_wifi.end();

            log_println("[I] WiFi provisioned successfully");
            g_state.system_state = STATE_APP_RUNNING;
        }
        break;
    }

    case ARDUINO_EVENT_WIFI_STA_DISCONNECTED:
    {
        g_state.wifi_state = WIFI_FAILED;

        if (aws_mqtt_client.connected())
        {
            aws_mqtt_client.disconnect();
            log_println("[AWS] MQTT disconnected due to Wi-Fi disconnect");
        }

        // Get detailed disconnect reason
        char reason_msg[128];
        snprintf(reason_msg, sizeof(reason_msg),
                 "[W] Wi-Fi disconnected (status=%d)", WiFi.status());
        log_println(reason_msg);

        // Additional debug info
        if (WiFi.status() == WL_NO_SSID_AVAIL)
        {
            log_println("[E] SSID not found - check if SSID is correct");
        }
        else if (WiFi.status() == WL_CONNECT_FAILED)
        {
            log_println("[E] Connection failed - check password");
        }
        break;
    }

    default:
        break;
    }
}

// =============================================================================
// Setup
// =============================================================================

void setup()
{
    Serial.begin(SERIAL_BAUD);
    delay(500);

    // Boot sequence with repeated messages - allows time to catch output after USB reconnect
    Serial.println("\n\n=== ESP32-S3 BOOT SEQUENCE STARTING ===");
    Serial.println("=== Waiting 5 seconds for monitor to connect... ===\n");

    for (int i = 5; i > 0; i--)
    {
        Serial.print("[BOOT] ");
        Serial.print(i);
        Serial.println(" seconds until initialization continues...");
        delay(1000);
    }

    Serial.println("\n=== Proceeding with initialization ===\n");

    // Direct output to confirm serial is working
    Serial.println("=== ESP32-S3 Booting ===");
    Serial.println("=== If you see this, application started! ===");

#ifdef LOG_SERIAL_ENABLED
    Serial.println("LOG_SERIAL_ENABLED is defined");
#else
    Serial.println("WARNING: LOG_SERIAL_ENABLED is NOT defined");
#endif

    log_println("\n\n[System] ESP32-S3 Starting...");
    log_println("[Version] FW v1.0.0");

    // Initialize components - add checkpoint logging
    Serial.println("[CHECKPOINT] Calling config_store_init...");
    config_store_init();
    Serial.println("[CHECKPOINT] config_store_init done");

    Serial.println("[CHECKPOINT] Calling factory_reset_check...");
    factory_reset_check();
    Serial.println("[CHECKPOINT] factory_reset_check done");

    Serial.println("[CHECKPOINT] Calling config_store_check_provisioned...");
    config_store_check_provisioned();
    Serial.println("[CHECKPOINT] config_store_check_provisioned done");

    log_println("[Setup] Initializing WiFi...");
    wifi_mgr_init();

    // Setup status LED
    status_led_init();

    log_println("[Setup] Initializing MPU6050...");
    mpu_initialized = sensor_init_mpu6050();

    delay(500); // Give time for WiFi stack to initialize

    log_println("[Setup] Initializing BLE...");
    init_ble();

    delay(500); // Give time for BLE stack to initialize

    // WiFi event handler
    WiFi.onEvent(wifi_event_handler);

    snprintf(g_state.device_name, sizeof(g_state.device_name), "ESP32-S3-SUPERMINI");

    log_println("[Setup] Initialization complete");
    log_println("[Info] Waiting for BLE provisioning or app commands...");
}

// =============================================================================
// Loop
// =============================================================================

void loop()
{
    // Handle OTA finalization request (moved from BLE callback to avoid stack issues)
    if (ota_finalize_requested)
    {
        ota_finalize_requested = false;

        log_println("[OTA] Finalizing update...");
        Serial.printf("[OTA] Received: %u bytes / Expected: %u bytes\n", ota_received_size, ota_expected_size);

        if (Update.end(true)) // true = do checksum validation
        {
            Serial.printf("[OTA] Update Success: %u bytes\n", ota_received_size);
            log_println("[I] OTA update successful!");
            ota_in_progress = false;
            ota_mode_active = false;

            if (pOtaStatus)
            {
                pOtaStatus->setValue("SUCCESS");
                pOtaStatus->notify();
            }

            delay(1000);
            log_println("[I] Rebooting...");
            delay(500);
            ESP.restart();
        }
        else
        {
            Serial.println("\n=== Update.end() FAILED ===");
            Serial.printf("[OTA] ota_received_size = %u\n", ota_received_size);
            Serial.printf("[OTA] ota_expected_size = %u\n", ota_expected_size);
            Update.printError(Serial);
            log_println("[E] Update.end() failed");
            ota_in_progress = false;

            if (pOtaStatus)
            {
                pOtaStatus->setValue("ERROR:END_FAILED");
                pOtaStatus->notify();
            }
        }
    }

    // Handle OTA abort request
    if (ota_abort_requested)
    {
        ota_abort_requested = false;
        log_println("[W] OTA aborted by user");
        if (ota_in_progress)
        {
            Update.abort();
            ota_in_progress = false;
        }
        ota_mode_active = false;

        if (pOtaStatus)
        {
            pOtaStatus->setValue("ABORTED");
            pOtaStatus->notify();
        }
    }

    // If OTA mode is active, stop normal app operation
    if (ota_mode_active)
    {
        // Only handle BLE and OTA processing
        delay(10); // Reduced delay for faster response
        return;
    }

    // Wi-Fi state monitoring and auto-reconnect management
    static unsigned long last_wifi_check = 0;
    static unsigned long last_wifi_reconnect_try = 0;
    static unsigned long wifi_connect_start_time = 0;

    if (millis() - last_wifi_check > 5000) // Check WiFi state every 5 seconds
    {
        last_wifi_check = millis();

        if (g_state.wifi_state == WIFI_CONNECTING)
        {
            if (WiFi.status() == WL_CONNECTED)
            {
                // Will be handled by event handler
            }
            else
            {
                // Check for connection timeout (30 seconds)
                if (wifi_connect_start_time > 0 &&
                    (millis() - wifi_connect_start_time > 30000))
                {
                    log_println("[E] WiFi connection timeout - marking as failed");
                    g_state.wifi_state = WIFI_FAILED;
                    wifi_connect_start_time = 0;
                    WiFi.disconnect();
                }
            }
        }

        // Auto-reconnect: if WiFi config exists but not connected, try to connect
        if ((g_state.wifi_state == WIFI_IDLE || g_state.wifi_state == WIFI_FAILED) &&
            (millis() - last_wifi_reconnect_try > 30000)) // Retry every 30 seconds
        {
            char ssid[WIFI_SSID_MAX] = {0};
            nvs_wifi.begin(NVS_WIFI_NS, true);
            size_t ssid_len = nvs_wifi.getString("ssid", ssid, sizeof(ssid));
            nvs_wifi.end();

            if (ssid_len > 0) // WiFi config exists
            {
                log_println("[I] Loop: WiFi config found, initiating connection...");
                last_wifi_reconnect_try = millis();
                wifi_connect_start_time = millis();
                wifi_mgr_connect();
            }
        }
        else if (g_state.wifi_state == WIFI_CONNECTING && wifi_connect_start_time == 0)
        {
            // Initialize connection start time if not set
            wifi_connect_start_time = millis();
        }
    }

    // AWS MQTT connection keep-alive
    aws_iot_connect_if_needed();
    if (aws_mqtt_client.connected())
    {
        aws_mqtt_client.loop();
    }

    // Every 10 seconds, update BLE debug stat
    static unsigned long last_stat_update = 0;
    if (millis() - last_stat_update > 10000)
    {
        last_stat_update = millis();

        if (ble_device_connected && pDebugStat)
        {
            char stat_str[128];
            snprintf(stat_str, sizeof(stat_str),
                     "STATE:BLE=%d,WIFI=%d,OTA_MODE=%d,IP=%s",
                     ble_device_connected ? 1 : 0,
                     g_state.wifi_state,
                     ota_mode_active ? 1 : 0,
                     g_state.wifi_ip);
            pDebugStat->setValue((uint8_t *)stat_str, strlen(stat_str));
            pDebugStat->notify();
        }
    }

    // Sample acceleration data every 0.5 sec, calculate average over 5 sec, and send to AWS every 5 sec
    static unsigned long last_sensor_sample = 0;
    static unsigned long last_sensor_send = 0;
    static unsigned long last_sensor_error_notify = 0;

    if (mpu_initialized && millis() - last_sensor_sample >= SENSOR_SAMPLE_INTERVAL_MS)
    {
        last_sensor_sample = millis();

        sensors_event_t accel;
        sensors_event_t gyro;
        sensors_event_t temp;
        mpu.getEvent(&accel, &gyro, &temp);

        float accel_magnitude = fabs(accel.acceleration.x) + fabs(accel.acceleration.y) + fabs(accel.acceleration.z);

        // Store magnitude in circular buffer
        accel_magnitude_buffer[accel_buffer_index] = accel_magnitude;
        accel_buffer_index = (accel_buffer_index + 1) % ACCEL_BUFFER_SIZE;

        // Calculate average of all samples in buffer
        float avg_accel_magnitude = 0.0f;
        for (int i = 0; i < ACCEL_BUFFER_SIZE; i++)
        {
            avg_accel_magnitude += accel_magnitude_buffer[i];
        }
        avg_accel_magnitude /= ACCEL_BUFFER_SIZE;

        const char *current_status = activity_status_from_magnitude(avg_accel_magnitude);

        bool interval_due = millis() - last_aws_publish_time >= AWS_PUBLISH_INTERVAL_MS;

        if (interval_due && aws_mqtt_client.connected())
        {
            if (aws_iot_publish_sensor(avg_accel_magnitude, current_status, false))
            {
                last_aws_publish_time = millis();
                last_activity_status = current_status;
                has_last_activity_status = true;

                status_led_blink_aws();
            }
        }

        if (millis() - last_sensor_send >= SENSOR_SEND_INTERVAL_MS && ble_device_connected && pDebugLogTx)
        {
            last_sensor_send = millis();

            // Calculate average for BLE send
            float avg_accel_magnitude = 0.0f;
            for (int i = 0; i < ACCEL_BUFFER_SIZE; i++)
            {
                avg_accel_magnitude += accel_magnitude_buffer[i];
            }
            avg_accel_magnitude /= ACCEL_BUFFER_SIZE;

            char csv[64];
            snprintf(csv, sizeof(csv), "%.3f", avg_accel_magnitude);

            pDebugLogTx->setValue((uint8_t *)csv, strlen(csv));
            pDebugLogTx->notify();
        }
    }
    else if (!mpu_initialized && ble_device_connected && pDebugLogTx)
    {
        // Send error notification every 1s (throttled)
        if (millis() - last_sensor_error_notify >= SENSOR_ERROR_NOTIFY_INTERVAL_MS)
        {
            last_sensor_error_notify = millis();
            const char *err = "[E] MPU6050_NOT_FOUND";
            pDebugLogTx->setValue((uint8_t *)err, strlen(err));
            pDebugLogTx->notify();
        }
    }

    delay(100);
}
