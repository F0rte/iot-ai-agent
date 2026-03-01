# ESP32-S3 Super Mini - IoT Device Firmware (PlatformIO)

MPU6050 加速度センサーを使った活動検知と AWS IoT Core へのデータ送信機能を備えた ESP32-S3 Super Mini 用のファームウェアです。BLE による Wi-Fi プロビジョニング、OTA アップデート、デバッグモニタ機能も搭載しています。

## 機能

- ✅ MPU6050 加速度センサーによる活動検知（Run / Walk / None）
- ✅ AWS IoT Core への MQTT 接続とセンサーデータ送信（5秒間隔）
- ✅ BLE Wi-Fi プロビジョニング
- ✅ BLE 経由のファームウェア OTA アップデート
- ✅ BLE デバッグシリアルモニタ
- ✅ ステータス LED（GPIO + RGB）制御

## 必要なもの

### ハードウェア

- ESP32-S3 Super Mini
- MPU6050 加速度センサーモジュール（I2C 接続）
- USB ケーブル（プログラム書き込み用）
- ジャンパーワイヤー（MPU6050 接続用）

**MPU6050 配線:**

- SDA: GPIO 12
- SCL: GPIO 11
- VCC: 3.3V
- GND: GND

### ソフトウェア

- Python 3.x
- PlatformIO CLI または VSCode + PlatformIO Extension
- AWS IoT Core アカウント（証明書設定済み）

## インストール

### 1. PlatformIO CLI のインストール（初回のみ）

```bash
pip install platformio
```

### 2. VSCode + PlatformIO Extension（推奨）

1. VSCode をインストール
2. Extension で "PlatformIO" を検索・インストール
3. VSCode を再起動

## セットアップ

### 1. AWS IoT Core 証明書の設定

main.cpp 内の以下の証明書を自分の AWS IoT Core 証明書に置き換えてください：

- `AWS_ROOT_CA` - Amazon Root CA
- `AWS_DEVICE_CERT` - デバイス証明書
- `AWS_PRIVATE_KEY` - デバイス秘密鍵

エンドポイントとトピックも必要に応じて変更：

```cpp
#define AWS_IOT_ENDPOINT "your-endpoint.iot.ap-northeast-1.amazonaws.com"
#define AWS_IOT_TOPIC "your/iot/topic"
```

### 2. ビルド・実行手順

#### 方法1: PlatformIO CLI（ターミナル）

```bash
# プロジェクトディレクトリに移動
cd c:\Users\naka6\Projects\iot-ai-agent\IotDevice

# ビルド
platformio run

# デバイスに書き込み
platformio run --target upload

# シリアルモニタを開く
platformio device monitor
```

#### 方法2: VSCode + PlatformIO GUI（推奨）

1. VSCode でプロジェクトフォルダを開く
2. 左下の PlatformIO アイコンをクリック
3. **Build** でコンパイル
4. **Upload** でデバイスに書き込み
5. **Open Serial Monitor** でシリアル出力を確認

### 3. COM ポートの確認

**Windows:**

```bash
# デバイスマネージャーで "COM3" などを確認
# または
platformio device list
```

**platformio.ini の修正（必要に応じて）**

```ini
upload_port = COM3  ; 自分のポートに変更
```

## 動作確認

シリアルモニタで以下のようなログが表示されれば成功：

```
[System] ESP32-S3 Starting...
[MPU6050] Initializing...
[MPU6050] OK
[AWS] Client ID: esp32-xxxxxxxxxxxx
[AWS] Setting up secure client certificates...
[AWS] Configuring MQTT client...
[AWS] MQTT client initialized
[BLE] Initialized
[Setup] Initialization complete
[AWS] Connecting to AWS IoT Core...
[AWS] Connected!
[AWS] Publishing: {"timestamp":1234567890,"client_id":"esp32-xxx","accel_x":0.00,...,"activity":"None"}
```

**MPU6050 センサー動作確認:**

- デバイスを動かすと加速度データが変化します
- 静止: "activity": "None"
- 歩く: "activity": "Walk"（加速度 > 20.0）
- 走る: "activity": "Run"（加速度 > 30.0）

**AWS IoT Core での確認:**
AWS IoT Core のコンソールで MQTT Test Client を使用し、設定したトピックをサブスクライブすると、5秒ごとにセンサーデータが受信できます。

## トラブルシューティング

### Port が見つからない

```bash
# デバイスリスト表示
platformio device list

# または Windows のデバイスマネージャーで COM ポートを確認
```

### コンパイルエラー

```bash
# キャッシュクリア
platformio run --target clean

# 再度ビルド
platformio run
```

### MPU6050 が初期化できない

- I2C 配線を確認（SDA: GPIO 12, SCL: GPIO 11）
- MPU6050 の電源（3.3V と GND）を確認
- I2C アドレス（0x68 または 0x69）を確認

### AWS IoT Core に接続できない

- Wi-Fi 接続を確認（BLE プロビジョニングが必要）
- 証明書（Root CA、Device Cert、Private Key）が正しく設定されているか確認
- AWS IoT エンドポイントが正しいか確認
- Thing のポリシーで接続・パブリッシュ権限が付与されているか確認

### シリアルモニタが開かない

- USB ドライバをインストール（[CH340 ドライバ](https://sparks.gogo.co.nz/ch340.html)など）
- ボーレート: 115200

## ファイル構成

```
IotDevice/
├── src/
│   └── main.cpp             # メインプログラム
├── platformio.ini           # PlatformIO 設定
├── partitions_ota_2m.csv    # OTA 対応パーティションテーブル
├── partitions.csv           # 通常パーティションテーブル
└── README.md               # このファイル
```

## 依存ライブラリ

platformio.ini で自動的にインストールされます：

- **Adafruit MPU6050** - 加速度センサー制御
- **Adafruit Unified Sensor** - センサー共通ライブラリ
- **PubSubClient** - MQTT クライアント
- **ArduinoJson** - JSON シリアライズ/デシリアライズ

## BLE サービス

### Debug Service

- Debug Service: `7f3f0001-6b7c-4f2e-9b8a-1a2b3c4d5e6f`
- DebugLogTx (Notify): `7f3f0002-6b7c-4f2e-9b8a-1a2b3c4d5e6f`
- DebugCmdRx (Write): `7f3f0003-6b7c-4f2e-9b8a-1a2b3c4d5e6f`
- DebugStat (Read/Notify): `7f3f0005-6b7c-4f2e-9b8a-1a2b3c4d5e6f`

### Provisioning Service

- Provisioning Service: `8f4f0001-7c8d-5f3e-ac9b-2b3c4d5e6f70`
- WiFi Config (Write): `8f4f0002-7c8d-5f3e-ac9b-2b3c4d5e6f70`

### OTA Service

- OTA Service: `9f5f0001-8d9e-6f4e-bd0c-3c4d5e6f7180`
- OTA Control (Write/Read): `9f5f0002-8d9e-6f4e-bd0c-3c4d5e6f7180`
- OTA Data (Write): `9f5f0003-8d9e-6f4e-bd0c-3c4d5e6f7180`
- OTA Status (Read/Notify): `9f5f0004-8d9e-6f4e-bd0c-3c4d5e6f7180`

BLE 経由でファームウェアの OTA アップデートが可能です。詳細は仕様書を参照してください。

## オプション設定

### ビルドオプション（platformio.ini）

**デバッグレベルの変更**

```ini
build_flags =
  -DCORE_DEBUG_LEVEL=5    ; 0=None, 5=Verbose
  -DLOG_SERIAL_ENABLED=1  ; シリアルログ有効化
```

**センサーデータ送信間隔の変更（main.cpp）**

```cpp
#define AWS_PUBLISH_INTERVAL_MS 5000        // AWS への送信間隔（ミリ秒）
#define SENSOR_SAMPLE_INTERVAL_MS 500       // センサーサンプリング間隔（ミリ秒）
#define SENSOR_SEND_INTERVAL_MS 10000       // BLE デバッグログへの送信間隔（ミリ秒）
```

**活動検知の閾値変更（main.cpp）**

```cpp
// activity_status_from_magnitude() 関数内
if (accel_magnitude > 30.0f) return "Run";     // 走り
if (accel_magnitude > 20.0f) return "Walk";    // 歩き
return "None";                                 // 静止
```

## 仕様書参照

詳細な仕様については、以下のドキュメントを参照してください：

- [IOT_DATA_SPECIFICATION.md](../IOT_DATA_SPECIFICATION.md) - IoT データ仕様
- プロジェクトルートの仕様書

## 関連プロジェクト

- AI Agent: [ai-agent/](../ai-agent/) - LangGraph による AI エージェント
- Watch App: [watch-app/](../watch-app/) - Apple Watch コントロールアプリ
- VSCode Extension: [vscode-extension/](../vscode-extension/) - VSCode 拡張機能
