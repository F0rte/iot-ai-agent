# IoT Data Communication Specification

**Project**: Running Driven Development (RDD) Agent
**Version**: 1.0.0
**Last Updated**: 2026-02-28

---

## 📋 Table of Contents

1. [System Architecture](#system-architecture)
2. [MQTT Topics](#mqtt-topics)
3. [Data Flow](#data-flow)
4. [Message Schemas](#message-schemas)
5. [Connection Specifications](#connection-specifications)
6. [Error Handling](#error-handling)
7. [Implementation Examples](#implementation-examples)

---

## 🏗 System Architecture

```
┌─────────────────┐
│  IoT Device     │
│  (Apple Watch / │  ──┐
│   Custom HW)    │    │
└─────────────────┘    │ MQTT Publish
                       │ (via WebSocket)
                       ↓
              ┌────────────────┐
              │  AWS IoT Core  │
              └────────────────┘
                       │ MQTT Subscribe
                       ↓
              ┌────────────────┐
              │   AI Agent     │
              │   (Python)     │
              └────────────────┘
                       │ Server-Sent Events
                       ↓
              ┌────────────────┐
              │  VS Code Ext   │
              └────────────────┘
```

### Components

| Component             | Role                                    | Technology                                 |
| --------------------- | --------------------------------------- | ------------------------------------------ |
| **IoT Device**        | Sensor data source (motion, heart rate) | Swift (iOS/watchOS SDK) or custom firmware |
| **AWS IoT Core**      | MQTT broker, message routing            | AWS managed service                        |
| **AI Agent**          | Receives IoT data, processes with LLM   | Python, FastAPI, LangGraph, Claude AI      |
| **VS Code Extension** | Displays real-time events, UI control   | TypeScript, WebView API                    |

---

## 📡 MQTT Topics

### Topic Naming Convention

```
hackathon/run/{environment}
```

### Current Topics

| Topic                | Purpose               | Publisher  | Subscriber |
| -------------------- | --------------------- | ---------- | ---------- |
| `hackathon/run/test` | Development/testing   | IoT Device | AI Agent   |
| `hackathon/run/prod` | Production (reserved) | IoT Device | AI Agent   |

### Topic Design Notes

- **Namespace**: `hackathon/` - project identifier
- **Feature**: `run/` - running/activity related
- **Environment**: `test`, `prod` - deployment environment

---

## 🔄 Data Flow

### 1. Device → IoT Core (MQTT Publish)

**Direction**: IoT Device → AWS IoT Core
**Protocol**: MQTT over WebSockets
**QoS**: 0 (At Most Once) or 1 (At Least Once)
**Format**: JSON string

### 2. IoT Core → AI Agent (MQTT Subscribe)

**Direction**: AWS IoT Core → AI Agent
**Protocol**: MQTT over WebSockets
**Trigger**: Message arrives on subscribed topic
**Format**: JSON object (parsed from string)

### 3. AI Agent → VS Code Extension (SSE)

**Direction**: AI Agent → VS Code Extension
**Protocol**: Server-Sent Events (HTTP)
**Endpoint**: `http://localhost:8000/events`
**Format**: JSON event stream

---

## 📦 Message Schemas

### 1. Running Status Message (Device → IoT Core)

**Topic**: `hackathon/run/test`

#### Schema (JSON)

```json
{
  "is_running": boolean,
  "bpm": integer,
  "timestamp": string (ISO 8601, optional),
  "device_id": string (optional)
}
```

#### Field Descriptions

| Field        | Type    | Required | Description                               | Example                   |
| ------------ | ------- | -------- | ----------------------------------------- | ------------------------- |
| `is_running` | boolean | ✅ Yes   | Whether the user is currently running     | `true`, `false`           |
| `bpm`        | integer | ✅ Yes   | Heart rate in beats per minute            | `135`                     |
| `timestamp`  | string  | ❌ No    | ISO 8601 timestamp when data was captured | `"2026-02-28T10:30:00Z"`  |
| `device_id`  | string  | ❌ No    | Unique identifier for the device          | `"swift-client-a1b2c3d4"` |

#### Validation Rules

- `is_running`: Must be `true` or `false`
- `bpm`: Must be integer, range 30-220 (typical human heart rate)
- `timestamp`: Must be valid ISO 8601 format if provided
- `device_id`: Max 64 characters

#### Example Messages

**Minimal (current implementation)**:

```json
{
  "is_running": true,
  "bpm": 135
}
```

**Complete**:

```json
{
  "is_running": true,
  "bpm": 142,
  "timestamp": "2026-02-28T10:45:32Z",
  "device_id": "swift-client-a1b2c3d4"
}
```

**Running stopped**:

```json
{
  "is_running": false,
  "bpm": 98,
  "timestamp": "2026-02-28T11:15:00Z",
  "device_id": "swift-client-a1b2c3d4"
}
```

---

### 2. Enhanced Running Status (Future Extension)

For more advanced fitness tracking, the schema can be extended:

```json
{
  "is_running": boolean,
  "bpm": integer,
  "timestamp": string,
  "device_id": string,
  "metrics": {
    "speed": float,        // km/h
    "distance": float,     // meters
    "cadence": integer,    // steps per minute
    "elevation": float     // meters
  },
  "location": {
    "latitude": float,
    "longitude": float
  }
}
```

**Note**: Extended fields are optional and should not break existing implementations.

---

### 3. SSE Event Messages (AI Agent → VS Code Extension)

The AI Agent broadcasts three types of events via Server-Sent Events.

#### Event Type: `iot`

Sent immediately when IoT data is received.

```json
{
  "type": "iot",
  "topic": "hackathon/run/test",
  "data": {
    "is_running": true,
    "bpm": 135
  }
}
```

#### Event Type: `agent`

Sent after AI agent processes the IoT data.

```json
{
  "type": "agent",
  "response": "ランニング中のデータを受信しました。心拍数は135bpmで、適度な運動強度です。"
}
```

#### Event Type: `error`

Sent when an error occurs during processing.

```json
{
  "type": "error",
  "message": "Failed to process IoT message: Invalid JSON format"
}
```

#### Event Type: `ping`

Keep-alive message (ignored by client).

```json
{
  "type": "ping"
}
```

---

## 🔌 Connection Specifications

### IoT Device Connection

#### Authentication

- **Method**: AWS IAM Static Credentials
- **Required Credentials**:
  - `AWS_ACCESS_KEY_ID`
  - `AWS_SECRET_ACCESS_KEY`
  - `AWS_IOT_ENDPOINT` (e.g., `xxxxx.iot.ap-northeast-1.amazonaws.com`)

#### Connection Parameters

- **Protocol**: MQTT over WebSockets
- **Region**: `ap-northeast-1` (Tokyo)
- **Client ID Format**: `swift-client-{UUID_PREFIX}` or `custom-device-{UUID}`
- **Clean Session**: `true` (don't persist session state)
- **Keep Alive**: 30 seconds (configurable)

#### Swift (iOS/watchOS) Example

```swift
let clientId = "swift-client-\(UUID().uuidString.prefix(8))"
iotDataManager?.connectUsingWebSocket(
    withClientId: clientId,
    cleanSession: true
) { status in
    // Handle connection status
}
```

#### Generic MQTT Client Example

```python
# Using paho-mqtt or similar
client_id = f"custom-device-{uuid.uuid4().hex[:8]}"
client.connect(
    host="xxxxx.iot.ap-northeast-1.amazonaws.com",
    port=443,
    protocol="websockets"
)
```

---

### AI Agent Connection

#### MQTT Subscriber Configuration

**File**: `ai-agent/iot/subscriber.py`

```python
# Environment variables required
AWS_IOT_ENDPOINT=xxxxx.iot.ap-northeast-1.amazonaws.com
AWS_REGION=ap-northeast-1
AWS_ACCESS_KEY_ID=AKIAXXXXXXXXXXXXXXXX
AWS_SECRET_ACCESS_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

#### Connection Parameters

- **Protocol**: MQTT over WebSockets with AWS SigV4 signing
- **Client ID**: `ai-agent-{RANDOM_HEX}` (8 characters)
- **Clean Session**: `true`
- **Keep Alive**: 30 seconds
- **QoS**: 1 (At Least Once)

---

### VS Code Extension Connection

#### SSE Client Configuration

**File**: `vscode-extension/src/panel.ts`

```javascript
const es = new EventSource("http://localhost:8000/events");
```

- **Protocol**: HTTP Server-Sent Events
- **Endpoint**: `http://localhost:8000/events`
- **Retry Logic**: Automatic reconnection after 5 seconds on disconnect
- **CORS**: Enabled for development

---

## ⚠️ Error Handling

### Device-Side Errors

| Error             | Cause                           | Handling                         |
| ----------------- | ------------------------------- | -------------------------------- |
| Connection Failed | Invalid credentials or endpoint | Retry with exponential backoff   |
| Publish Failed    | Network issue or QoS=1 timeout  | Log error, retry next data point |
| Disconnected      | Network interruption            | Auto-reconnect via SDK           |

### AI Agent-Side Errors

| Error            | Cause                         | Handling                                 |
| ---------------- | ----------------------------- | ---------------------------------------- |
| JSON Parse Error | Invalid message format        | Log error, send error event to extension |
| LLM API Error    | Bedrock/Anthropic API failure | Catch exception, broadcast error event   |
| Connection Lost  | IoT Core disconnected         | Auto-reconnect via SDK callback          |

### VS Code Extension Errors

| Error                 | Cause                | Handling                          |
| --------------------- | -------------------- | --------------------------------- |
| SSE Connection Failed | AI agent not running | Show error status, retry every 5s |
| Invalid Event Data    | Malformed JSON       | Ignore event, log to console      |

---

## 💻 Implementation Examples

### Example 1: Custom IoT Device (Python)

```python
import json
import uuid
from awscrt import mqtt, auth
from awsiot import mqtt_connection_builder

# Setup credentials
credentials_provider = auth.AwsCredentialsProvider.new_static(
    access_key_id="YOUR_ACCESS_KEY",
    secret_access_key="YOUR_SECRET_KEY",
)

# Build connection
mqtt_connection = mqtt_connection_builder.websockets_with_default_aws_signing(
    endpoint="xxxxx.iot.ap-northeast-1.amazonaws.com",
    region="ap-northeast-1",
    credentials_provider=credentials_provider,
    client_id=f"custom-device-{uuid.uuid4().hex[:8]}",
    clean_session=True,
    keep_alive_secs=30,
)

# Connect
connect_future = mqtt_connection.connect()
connect_future.result()

# Publish data
topic = "hackathon/run/test"
message = {
    "is_running": True,
    "bpm": 145,
    "timestamp": "2026-02-28T10:45:00Z",
    "device_id": "custom-sensor-001"
}

mqtt_connection.publish(
    topic=topic,
    payload=json.dumps(message),
    qos=mqtt.QoS.AT_LEAST_ONCE
)

# Disconnect
mqtt_connection.disconnect()
```

---

### Example 2: Custom IoT Device (ESP32 Arduino)

```cpp
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

const char* mqtt_server = "xxxxx.iot.ap-northeast-1.amazonaws.com";
const int mqtt_port = 8883; // or 443 for WebSockets
const char* topic = "hackathon/run/test";

WiFiClientSecure espClient;
PubSubClient client(espClient);

void publishRunData(bool isRunning, int bpm) {
    StaticJsonDocument<200> doc;
    doc["is_running"] = isRunning;
    doc["bpm"] = bpm;
    doc["timestamp"] = getCurrentTimestamp(); // Implement this
    doc["device_id"] = "esp32-001";

    char buffer[256];
    serializeJson(doc, buffer);

    client.publish(topic, buffer);
}

void loop() {
    bool isRunning = detectMotion(); // Implement sensor logic
    int bpm = readHeartRate();       // Implement sensor logic

    publishRunData(isRunning, bpm);
    delay(5000); // Send every 5 seconds
}
```

---

### Example 3: Testing with MQTT CLI

```bash
# Install mosquitto-clients or awscli
# Using AWS IoT SDK Test Client (recommended)

# Publish test message
aws iot-data publish \
  --topic "hackathon/run/test" \
  --payload '{"is_running":true,"bpm":120}' \
  --endpoint-url https://xxxxx.iot.ap-northeast-1.amazonaws.com

# Or using mosquitto_pub with WebSockets
mosquitto_pub \
  -h xxxxx.iot.ap-northeast-1.amazonaws.com \
  -p 443 \
  -t "hackathon/run/test" \
  -m '{"is_running":true,"bpm":120}' \
  --cafile AmazonRootCA1.pem
```

---

## 📚 Additional Resources

### AWS IoT Core Documentation

- [AWS IoT Core WebSocket Connection](https://docs.aws.amazon.com/iot/latest/developerguide/protocols.html#mqtt-ws)
- [MQTT Topic Design Best Practices](https://docs.aws.amazon.com/whitepapers/latest/designing-mqtt-topics-aws-iot-core/designing-mqtt-topics-aws-iot-core.html)

### Project-Specific Files

- **AI Agent Subscriber**: `ai-agent/iot/subscriber.py`
- **Swift App Publisher**: `watch-app/AgentController/AgentController/ContentView.swift`
- **VS Code Extension**: `vscode-extension/src/panel.ts`

---

## 🔄 Version History

| Version | Date       | Changes                                               |
| ------- | ---------- | ----------------------------------------------------- |
| 1.0.0   | 2026-02-28 | Initial specification based on current implementation |

---

## 📝 Notes

- This specification is designed to be **platform-agnostic** to support migration from Swift to custom IoT devices
- All timestamps should use **ISO 8601 format** in UTC
- Message size should be kept under **128 KB** (AWS IoT Core limit)
- Consider implementing **message compression** for large payloads
- For production, implement **TLS certificate-based authentication** instead of static credentials
