# 調査レポート：AWS IoT Core データ送信実装

**調査日**: 2026-02-28  
**対象**: IotDevice(ESP32)にAWS IoT Core送信機能を追加

---

## 概要

IotDeviceプロジェクト(ESP32-S3)に、加速度センサーデータをAWS IoT Coreに送信する機能を追加する実装調査

---

## 現在の実装状況

### IotDevice (main.cpp)

- **加速度センサー**: MPU6050から取得
  - 計算方法: `accel_magnitude = |ax| + |ay| + |az|` (10秒間隔)
  - BLE経由でテキスト形式で送信中
- **WiFi接続**: 実装済み
  - BLE経由でWiFi認証情報を受け取り
  - WiFi接続状態の管理あり
  - IP取得後に `STATE_APP_RUNNING` に遷移

- **AWS IoT Core接続**: 未実装
  - PubSubClientライブラリなし
  - MQTT接続・データ送信コードなし

### watch-app (ContentView.swift)

AWS IoT Core接続の参考実装：

- AWS SDKを使用 (`AWSCore`, `AWSIoT`)
- WebSocket経由でMQTT接続
- 資格情報ベースの認証（AccessKey/SecretKey）
- Topic: `hackathon/run/test` へJSON形式でPublish
- メッセージ形式: `{"is_running": boolean, "bpm": integer}`

### データ仕様 (IOT_DATA_SPECIFICATION.md)

```json
{
  "is_running": boolean,  // 走っているかどうか（StatusがNone以外で true）
  "bpm": integer,         // 加速度の大きさ
  "timestamp": string,    // ISO 8601形式（オプション）
  "device_id": string     // デバイスID（オプション）
}
```

---

## 実装に必要な要素

### 1. ライブラリ追加

- **PubSubClient**: MQTT Publish/Subscribe機能
- **ArduinoJson**: JSON生成機能

### 2. AWS接続情報

- **IoT Endpoint**: AWS IoT Coreのエンドポイント
- **CA証明書**: ルート認証局証明書
- **クライアント証明書**: デバイス証明書
- **秘密鍵**: デバイス秘密鍵

### 3. 実装項目（main.cpp）

1. MQTT接続機能（WiFi接続後に初期化）
2. Status判定ロジック：
   - 加速度 >= 30 → "Run"
   - 15 <= 加速度 < 30 → "Walk"
   - 加速度 < 15 → "None"
3. データ送信ロジック：
   - 10秒おき：BPM + 現在のStatus
   - Status変更時：即座に送信
4. BLE経由デバッグログ出力

### 4. グローバル変数の追加

- 前回送信時刻
- 前回のStatus値
- MQTT接続状態フラグ
- WiFi接続状態の監視

---

## 参考仕様

- **Topic**: `hackathon/run/test`
- **QoS**: 0 (At Most Once)
- **送信間隔**: 10秒またはStatus変更時
- **遠隔開始**: WiFi接続後自動開始

---

## 注意事項

- WiFi接続前はAWS送信スキップ
- BLE と AWS の両方にデバッグログ出力
- 加速度データの計算方法は既存実装（BLE用）と統一
- **Keep Alive**: 30秒

**送信データフォーマット:**

```json
{
  "is_running": true,
  "bpm": 135
}
```

**送信トピック**: `hackathon/run/test`

**QoS レベル**: `0` (At Most Once - テスト送信)

**実装コード:**

```swift
func publishRunStatus() {
    let topic = "hackathon/run/test"
    let payloadString = "{\"is_running\": true, \"bpm\": 135}"

    iotDataManager?.publishString(
        payloadString,
        onTopic: topic,
        qoS: .messageDeliveryAttemptedAtMostOnce
    )
}
```

**接続処理:**

```swift
func setupAWSConnection() {
    let credentialsProvider = AWSStaticCredentialsProvider(
        accessKey: Secrets.accessKey,
        secretKey: Secrets.secretKey
    )

    let endpointURL = URL(string: "https://\(Secrets.iotEndpoint)")
    let endpoint = AWSEndpoint(url: endpointURL)

    let iotConfig = AWSServiceConfiguration(
        region: .APNortheast1,
        endpoint: endpoint,
        credentialsProvider: credentialsProvider
    )

    AWSIoTDataManager.register(with: iotConfig!, forKey: "HackathonIoTManager")
    iotDataManager = AWSIoTDataManager(forKey: "HackathonIoTManager")

    let clientId = "swift-client-\(UUID().uuidString.prefix(8))"
    iotDataManager?.connectUsingWebSocket(
        withClientId: clientId,
        cleanSession: true
    ) { status in
        // ステータス更新
        if status == .connected {
            self.isConnected = true
        }
    }
}
```

**必要な認証情報 (Secrets):**

- `Secrets.accessKey` - AWS Access Key ID
- `Secrets.secretKey` - AWS Secret Access Key
- `Secrets.iotEndpoint` - AWS IoT Endpoint (例: `xxxxx.iot.ap-northeast-1.amazonaws.com`)

---

### 2. AWS IoT Core → AI Agent

#### ファイル: [ai-agent/iot/subscriber.py](../ai-agent/iot/subscriber.py)

**実装内容:**

- **認証方式**: AWS 静的認証情報 + SigV4 署名
- **プロトコル**: MQTT over WebSocket with AWS SigV4 signing
- **クライアント ID**: `ai-agent-{RANDOM_HEX}` (8文字)
- **Clean Session**: `true`
- **Keep Alive**: 30秒
- **QoS**: 1 (At Least Once - 確実な配信)

**環境変数:**

```
AWS_IOT_ENDPOINT=xxxxx.iot.ap-northeast-1.amazonaws.com
AWS_REGION=ap-northeast-1
AWS_ACCESS_KEY_ID=AKIAXXXXXXXXXXXXXXXX
AWS_SECRET_ACCESS_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

**接続処理:**

```python
def setup(loop: asyncio.AbstractEventLoop) -> None:
    endpoint = os.environ["AWS_IOT_ENDPOINT"]
    region = os.environ.get("AWS_REGION", "ap-northeast-1")
    access_key_id = os.environ["AWS_ACCESS_KEY_ID"]
    secret_access_key = os.environ["AWS_SECRET_ACCESS_KEY"]

    credentials_provider = auth.AwsCredentialsProvider.new_static(
        access_key_id=access_key_id,
        secret_access_key=secret_access_key,
    )

    _mqtt_connection = mqtt_connection_builder.websockets_with_default_aws_signing(
        endpoint=endpoint,
        region=region,
        credentials_provider=credentials_provider,
        client_id=f"ai-agent-{uuid.uuid4().hex[:8]}",
        clean_session=True,
        keep_alive_secs=30,
        on_connection_interrupted=_on_connection_interrupted,
        on_connection_resumed=_on_connection_resumed,
    )

    connect_future = _mqtt_connection.connect()
    connect_future.result()

    subscribe_future, _ = _mqtt_connection.subscribe(
        topic=TOPIC,
        qos=mqtt.QoS.AT_LEAST_ONCE,
        callback=_on_message_received,
    )
    subscribe_future.result()
```

**メッセージ受信処理:**

```python
TOPIC = "hackathon/run/test"

def _on_message_received(topic, payload, dup, qos, retain, **kwargs):
    try:
        message = json.loads(payload.decode("utf-8"))
    except Exception as e:
        print(f"[subscriber] JSON parse error: {e}")
        return

    asyncio.run_coroutine_threadsafe(_handle_message(topic, message), _loop)

async def _handle_message(topic: str, message: dict) -> None:
    from agent.graph import run_agent

    print(f"[subscriber] received: topic={topic} data={message}")

    # IoT 受信イベントを配信
    await broadcast({"type": "iot", "topic": topic, "data": message})

    # LangGraph エージェントで処理
    try:
        response = await run_agent(message)
        await broadcast({"type": "agent", "response": response})
    except Exception as e:
        await broadcast({"type": "error", "message": str(e)})
```

**接続状態管理:**

```python
def _on_connection_interrupted(connection, error, **kwargs):
    print(f"[subscriber] connection interrupted: {error}")

def _on_connection_resumed(connection, return_code, session_present, **kwargs):
    print(f"[subscriber] connection resumed: return_code={return_code}")

def teardown() -> None:
    if _mqtt_connection:
        _mqtt_connection.disconnect().result()
        print("[subscriber] disconnected from AWS IoT Core")
```

---

### 3. AI Agent → VS Code Extension

#### ファイル: [ai-agent/api/routes.py](../ai-agent/api/routes.py)

**実装内容:**

- **プロトコル**: Server-Sent Events (SSE) / HTTP
- **エンドポイント**: `GET /events`
- **メディアタイプ**: `text/event-stream`
- **レスポンスヘッダ**:
  - `Cache-Control: no-cache`
  - `X-Accel-Buffering: no`
  - `Access-Control-Allow-Origin: *`

**実装コード:**

```python
async def _event_generator(q: asyncio.Queue):
    try:
        while True:
            try:
                event = await asyncio.wait_for(q.get(), timeout=30.0)
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            except asyncio.TimeoutError:
                # 接続維持のための ping
                yield "data: {\"type\": \"ping\"}\n\n"
    except asyncio.CancelledError:
        pass

@router.get("/events")
async def sse_events():
    q = add_subscriber()
    return StreamingResponse(
        _event_generator(q),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",
        }
    )
```

**イベント配信管理:** [ai-agent/api/events.py](../ai-agent/api/events.py)

```python
_subscribers: List[asyncio.Queue] = []

def add_subscriber() -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue()
    _subscribers.append(q)
    return q

def remove_subscriber(q: asyncio.Queue) -> None:
    try:
        _subscribers.remove(q)
    except ValueError:
        pass

async def broadcast(event: dict) -> None:
    for q in list(_subscribers):
        await q.put(event)
```

---

## 📨 MQTT トピック仕様

### トピック命名規則

```
hackathon/run/{environment}
```

### 現在のトピック一覧

| トピック             | 用途              | パブリッシャー         | サブスクライバー |
| -------------------- | ----------------- | ---------------------- | ---------------- |
| `hackathon/run/test` | 開発・テスト用    | Watch-App / IoT Device | AI Agent         |
| `hackathon/run/prod` | 本番用 (予約済み) | Watch-App / IoT Device | AI Agent         |

### トピック設計ポイント

- **Namespace**: `hackathon/` - プロジェクト識別子
- **Feature**: `run/` - ランニング・活動関連
- **Environment**: `test`, `prod` - 環境区分

---

## 📦 メッセージスキーマ

### 1. ランニングステータスメッセージ (Device → IoT Core)

**トピック**: `hackathon/run/test`

```json
{
  "is_running": boolean,
  "bpm": integer,
  "timestamp": string (ISO 8601 、オプション),
  "device_id": string (オプション)
}
```

**フィール説明:**

| フィール     | 型      | 必須 | 説明                    | 例                        |
| ------------ | ------- | ---- | ----------------------- | ------------------------- |
| `is_running` | boolean | ✅   | ランニング中かどうか    | `true`, `false`           |
| `bpm`        | integer | ✅   | 心拍数 (拍数/分)        | `135`                     |
| `timestamp`  | string  | ❌   | ISO 8601 タイムスタンプ | `"2026-02-28T10:30:00Z"`  |
| `device_id`  | string  | ❌   | デバイス一意識別子      | `"swift-client-a1b2c3d4"` |

**バリデーション:**

- `is_running`: `true` または `false`
- `bpm`: 整数、範囲 30-220 (標準的な心拍数)
- `timestamp`: 有効な ISO 8601 形式 (提供されている場合)
- `device_id`: 最大 64 文字

**現在の実装 (ミニマル版):**

```json
{
  "is_running": true,
  "bpm": 135
}
```

**完全版:**

```json
{
  "is_running": true,
  "bpm": 142,
  "timestamp": "2026-02-28T10:45:32Z",
  "device_id": "swift-client-a1b2c3d4"
}
```

### 2. IoT 受信イベント (AI Agent → VS Code Extension)

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

### 3. エージェント処理結果イベント (AI Agent → VS Code Extension)

```json
{
  "type": "agent",
  "response": "ランニング中のデータを受信しました。心拍数は135bpmで、適度な運動強度です。"
}
```

### 4. エラーイベント (AI Agent → VS Code Extension)

```json
{
  "type": "error",
  "message": "Failed to process IoT message: Invalid JSON format"
}
```

---

## 🔄 データフロー詳細

### フロー 1: Device → IoT Core (MQTT Publish)

**方向**: Watch-App → AWS IoT Core  
**プロトコル**: MQTT over WebSocket  
**QoS**: 0 (最大1回) または 1 (最低1回)  
**フォーマット**: JSON文字列  
**トリガー**: ボタン押下時またはセンサーイベント時

### フロー 2: IoT Core → AI Agent (MQTT Subscribe)

**方向**: AWS IoT Core → AI Agent  
**プロトコル**: MQTT over WebSocket with SigV4 署名  
**QoS**: 1 (最低1回)  
**トリガー**: トピックにメッセージ到着時  
**フォーマット**: JSON オブジェクト (解析済み)

### フロー 3: AI Agent → VS Code Extension (SSE)

**方向**: AI Agent → VS Code Extension  
**プロトコル**: Server-Sent Events (HTTP)  
**エンドポイント**: `http://localhost:8000/events`  
**フォーマット**: JSON イベントストリーム  
**継続性**: 30秒タイムアウト、自動パルス (ping)

---

## ⚠️ エラーハンドリング

### Watch-App 側エラー

| エラー           | 原因                                      | 対応                                   |
| ---------------- | ----------------------------------------- | -------------------------------------- |
| 接続失敗         | 無効な認証情報またはエンドポイント        | リトライ (指数バックオフ)              |
| パブリッシュ失敗 | ネットワークエラーまたはQoS=1タイムアウト | エラー記録、次のデータポイントで再試行 |
| 切断             | ネットワーク中断                          | SDK 自動再接続                         |

### AI Agent 側エラー

| エラー            | 原因                         | 対応                                           |
| ----------------- | ---------------------------- | ---------------------------------------------- |
| JSON パースエラー | 無効なメッセージフォーマット | エラー記録、Extension に error イベント送信    |
| LLM API エラー    | Bedrock/Anthropic API 失敗   | 例外キャッチ、error イベントをブロードキャスト |
| 接続喪失          | IoT Core 接続切断            | SDK 自動再接続コールバック                     |

### VS Code Extension 側エラー

| エラー               | 原因                     | 対応                                    |
| -------------------- | ------------------------ | --------------------------------------- |
| SSE 接続失敗         | AI Agent 起動していない  | エラーステータス表示、5秒ごとにリトライ |
| 無効なイベントデータ | 不正な JSON フォーマット | イベント無視、コンソールにログ          |

---

## 🔐 セキュリティ仕様

### 認証方式

**現在 (テスト/開発):**

- AWS IAM 静的認証情報 (Access Key / Secret Key)
- `Secrets` ファイルまたは環境変数に保存

**本番推奨:**

- TLS 証明書ベース認証
- AWS IoT Core 証明書 (X.509)

### 通信暗号化

- MQTT over WebSocket: TLS 1.2+
- AWS SigV4 署名による追加認証 (AI Agent)
- AWS IoT Core エンドポイント: https://

### アクセス制御

- IAM ポリシーによる IoT アクション制限
- トピック単位のパブリッシュ/サブスクライブ制限 (可能)

---

## 📝 関連ファイル一覧

### Watch-App (Swift)

- [watch-app/AgentController/AgentController/ContentView.swift](../watch-app/AgentController/AgentController/ContentView.swift) - AWS 接続・データ送信実装

### AI Agent (Python)

- [ai-agent/iot/subscriber.py](../ai-agent/iot/subscriber.py) - AWS IoT Core 接続・メッセージ受信
- [ai-agent/api/routes.py](../ai-agent/api/routes.py) - SSE エンドポイント実装
- [ai-agent/api/events.py](../ai-agent/api/events.py) - イベント配信管理
- [ai-agent/main.py](../ai-agent/main.py) - FastAPI アプリケーション起動・ライフサイクル管理

### ドキュメント

- [IOT_DATA_SPECIFICATION.md](../IOT_DATA_SPECIFICATION.md) - 完全な IoT データ通信仕様書

---

## 🔍 テスト方法

### 1. AWS CLI での メッセージパブリッシュ

```bash
aws iot-data publish \
  --topic "hackathon/run/test" \
  --payload '{"is_running":true,"bpm":120}' \
  --endpoint-url https://xxxxx.iot.ap-northeast-1.amazonaws.com
```

### 2. Mosquitto での メッセージパブリッシュ

```bash
mosquitto_pub \
  -h xxxxx.iot.ap-northeast-1.amazonaws.com \
  -p 443 \
  -t "hackathon/run/test" \
  -m '{"is_running":true,"bpm":120}' \
  --cafile AmazonRootCA1.pem
```

### 3. VS Code Extension での SSE 接続確認

```
GET http://localhost:8000/events
```

---

## 📚 参考リンク

- [AWS IoT Core WebSocket Connection](https://docs.aws.amazon.com/iot/latest/developerguide/protocols.html#mqtt-ws)
- [MQTT Topic Design Best Practices](https://docs.aws.amazon.com/whitepapers/latest/designing-mqtt-topics-aws-iot-core/designing-mqtt-topics-aws-iot-core.html)
- [AWS SDK for Swift](https://github.com/awslabs/aws-sdk-swift)
- [AWS IoT SDK for Python (awsiot)](https://github.com/aws/aws-iot-device-sdk-python-v2)

---

## 🚀 今後の改善案

1. **本番認証**: TLS 証明書ベース認証への移行
2. **メッセージ圧縮**: 大型ペイロード向け圧縮実装
3. **タイムスタンプ追加**: より正確な時刻追跡
4. **デバイス ID 追加**: 複数デバイスからのデータ区別
5. **リトライ機構**: より堅牢な接続管理
6. **オフライン対応**: ローカルキャッシュとの同期
