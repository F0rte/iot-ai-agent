# 実装計画：AWS IoT Core データ送信機能

**作成日**: 2026-02-28  
**対象**: IotDevice(ESP32-S3)にAWS IoT Core送信機能を追加

---

## 実装タスク一覧

### 1. ライブラリの追加

**ファイル**: `IotDevice/platformio.ini`

**変更内容**:

- `PubSubClient` (MQTT クライアント)
- `ArduinoJson` (JSON 生成)

**現在**:

```ini
lib_deps =
  adafruit/Adafruit MPU6050
  adafruit/Adafruit Unified Sensor
```

**変更後**:

```ini
lib_deps =
  adafruit/Adafruit MPU6050
  adafruit/Adafruit Unified Sensor
  pubsubclient/PubSubClient
  bblanchon/ArduinoJson
```

### 2. AWS 接続情報の定義

**ファイル**: `IotDevice/src/main.cpp` (ヘッダ部分)

**追加内容**:

- AWS IoT Endpoint URL
- CA 証明書（const char\* として）
- クライアント証明書（const char\* として）
- クライアント秘密鍵（const char\* として）
- MQTT topic: `hackathon/run/test`

**定数追加**:

- デバイスID: `esp32-iot-device-001`（または同様の識別子）

### 3. グローバル変数追加

**ファイル**: `IotDevice/src/main.cpp` (グローバル変数セクション)

**追加するグローバル変数**:

```cpp
// MQTT & AWS
WiFiClientSecure wifiClientSecure;
PubSubClient mqttClient(wifiClientSecure);
bool mqtt_connected = false;
unsigned long last_mqtt_publish_time = 0;
float last_accel_magnitude = 0.0;
String last_status = "None";  // None, Walk, Run

// AWS接続パラメータ
const char* AWS_IOT_ENDPOINT = "your-endpoint.iot.ap-northeast-1.amazonaws.com";
const char* AWS_IOT_TOPIC = "hackathon/run/test";
```

### 4. MQTT 接続・初期化関数

**ファイル**: `IotDevice/src/main.cpp`

**実装する関数**:

- `aws_iot_connect()` : MQTT 接続
  - WiFi接続中のみ実行
  - 証明書検証あり
  - 接続失敗時のリトライ機構
- `aws_iot_disconnect()` : MQTT 切断

### 5. Status 判定関数

**ファイル**: `IotDevice/src/main.cpp`

**実装する関数**:

- `getActivityStatus(float accel_magnitude)` → String
  - accel >= 30 → "Run"
  - 15 <= accel < 30 → "Walk"
  - accel < 15 → "None"

### 6. AWS IoT Core データ送信関数

**ファイル**: `IotDevice/src/main.cpp`

**実装する関数**:

- `publishToAWSIoT(float accel_magnitude, const String& status)`
  - JSON生成: `{"is_running": boolean, "bpm": accel_magnitude, "timestamp": ISO8601, "device_id": "..."}`
  - MQTT Publish
  - BLE ログ出力

### 7. メインループの修正

**ファイル**: `IotDevice/src/main.cpp` (loop 関数内)

**追加処理**:

1. **WiFi接続時の MQTT初期化**
   - `wifi_state == WIFI_CONNECTED` かつ `mqtt_connected == false` の場合、`aws_iot_connect()` を実行

2. **MQTT疎通維持**
   - `mqttClient.loop()` を定期的に呼び出し

3. **加速度データ送信処理**
   - 現在の BLE送信ロジックを参考に：
     - 10秒おきに加速度+Status を collect
     - Status が前回と異なる場合は即座に送信
     - 定期的に 10秒おきに送信

4. **デバッグログ**
   - MQTT 送信直前に BLE ログを出力

### 8. 証明書の統合

**方法1**: 証明書をファイルとして保存

- `IotDevice/data/ca.crt`
- `IotDevice/data/client.crt`
- `IotDevice/data/client.key`
- LittleFS で読み込み

**方法2**: 証明書をヘッダに組み込み（推奨）

- main.cpp 内に const char\* として定義
- 行末に `\n` を含める

---

## 変更ファイル一覧

| ファイルパス               | 変更内容                                   |
| -------------------------- | ------------------------------------------ |
| `IotDevice/platformio.ini` | ライブラリ追加 (PubSubClient, ArduinoJson) |
| `IotDevice/src/main.cpp`   | AWS IoT 接続・送信ロジック追加             |

---

## 実装フロー

1. **ライブラリ追加** → platformio.ini 修正
2. **定数・変数定義** → AWS接続情報、グローバル変数
3. **関数実装** → MQTT接続、Status判定、送信
4. **ループ統合** → メインループからの呼び出し
5. **BLE ログ出力** → 送信タイミングで BLE 通知
6. **テスト** → AWS IoT Core で受信化認

---

## 実装依存関係

- WiFi 接続機能（既実装）
- BLE ログ機能（既実装）
- 加速度センサー読み込み（既実装）

---

## 注意事項

- **WiFi接続前**: AWS送信スキップ（`g_state.wifi_state == WIFI_CONNECTED` チェック必須）
- **証明書期限**: 定期的に更新確認
- **リソース制限**: ESP32のメモリ考慮（JSON生成時のバッファサイズ）
- **電力消費**: MQTT接続により消費電力増加（WiFiオフ時の対応検討）
