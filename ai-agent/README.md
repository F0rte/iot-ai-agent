# AI Agent

IoTデバイスからのデータを受信し、LangGraph + AWS Bedrockで処理する自律型AIエージェント。

---

## 🚀 クイックスタート

### 1. 環境変数の設定

```bash
cp .env.example .env
# .env を編集してAWS認証情報を設定
```

`.env` ファイルの例：
```bash
AWS_ACCESS_KEY_ID=AKIAXXXXXXXXXXXXXXXX
AWS_SECRET_ACCESS_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
AWS_REGION=us-east-1
AWS_IOT_ENDPOINT=xxxxx.iot.ap-northeast-1.amazonaws.com
AWS_BEDROCK_REGION=us-east-1
```

### 2. 依存関係のインストール

```bash
uv sync
```

---

## 🧪 ローカルテスト（サーバー不要）

IoT接続やサーバー起動なしで、エージェントの動作を確認できます。

```bash
uv run python test_agent.py
```

このスクリプトは：
- モックデータでLangGraphエージェントを呼び出し
- Bedrock APIにリクエストを送信
- エージェントの応答を表示

**必要な権限**:
- AWS Bedrockへのアクセス権限（`bedrock:InvokeModel`）
- インターネット接続

---

## 🌐 サーバーモード（本番・開発）

FastAPI + SSEでリアルタイムイベントを配信します。

### サーバー起動

```bash
uv run uvicorn main:app --reload
```

### 動作確認

1. **ヘルスチェック**
   ```bash
   curl http://localhost:8000/
   ```

2. **SSEエンドポイント**
   ```bash
   curl http://localhost:8000/events
   ```

3. **テストメッセージ送信**（AWS IoT Core経由）
   ```bash
   aws iot-data publish \
     --topic "hackathon/run/test" \
     --payload '{"message": "test", "timestamp": "2026-02-28T12:00:00Z"}' \
     --endpoint-url https://xxxxx.iot.ap-northeast-1.amazonaws.com
   ```

---

## 📁 プロジェクト構成

```
ai-agent/
├── main.py              # FastAPIサーバーのエントリポイント
├── test_agent.py        # ローカルテストスクリプト
├── agent/
│   ├── graph.py         # LangGraphエージェント定義
│   └── state.py         # エージェント状態の型定義
├── iot/
│   └── subscriber.py    # AWS IoT Core MQTTサブスクライバー
├── api/
│   ├── routes.py        # FastAPI ルート定義
│   └── events.py        # SSE イベント管理
├── pyproject.toml       # 依存関係定義
└── .env.example         # 環境変数テンプレート
```

---

## 🔧 技術スタック

| レイヤー | 技術 |
|---------|------|
| 言語 | Python 3.13+ |
| LLM | AWS Bedrock (Claude 3 Haiku) |
| エージェント | LangGraph |
| APIサーバー | FastAPI + Uvicorn |
| IoT接続 | AWS IoT Device SDK v2 |
| 認証 | AWS IAM (Static Credentials) |

---

## ⚙️ AWS Bedrock 設定

### 必要な IAM 権限

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-*"
    }
  ]
}
```

### モデルアクセスのリクエスト

1. [AWS Bedrock コンソール](https://console.aws.amazon.com/bedrock/) を開く
2. **Model access** メニューを選択
3. **Anthropic Claude** モデルへのアクセスをリクエスト
4. 承認を待つ（通常は即時）

### 利用可能なモデル

| モデル | Model ID | 用途 |
|-------|----------|------|
| Claude 3 Haiku | `anthropic.claude-3-haiku-20240307-v1:0` | 高速・低コスト |
| Claude 3.5 Sonnet | `anthropic.claude-3-5-sonnet-20240620-v1:0` | バランス型 |
| Claude 3 Opus | `anthropic.claude-3-opus-20240229-v1:0` | 高性能 |

モデルを変更する場合は `agent/graph.py` の `model_id` を編集してください。

---

## 🐛 トラブルシューティング

### エラー: `NoCredentialsError`

**原因**: AWS認証情報が設定されていない

**解決策**:
```bash
# .env ファイルに以下を設定
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
```

### エラー: `ResourceNotFoundException` (Bedrock)

**原因**: Bedrockモデルへのアクセス権限がない

**解決策**:
1. AWS Bedrockコンソールでモデルアクセスをリクエスト
2. IAM権限で `bedrock:InvokeModel` を許可

### エラー: `botocore.exceptions.EndpointConnectionError`

**原因**: 指定したリージョンでBedrockが利用できない

**解決策**:
```bash
# .env で利用可能なリージョンを指定
AWS_BEDROCK_REGION=us-east-1  # または us-west-2
```

---

## 📚 参考リンク

- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [AWS IoT Core Developer Guide](https://docs.aws.amazon.com/iot/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

---

## 📝 開発メモ

### IoT統合について

現在、IoT周りは別の担当者が実装中です。
ローカルテストスクリプト（`test_agent.py`）を使用してエージェントの動作確認を行ってください。

### センサーデータ形式

将来的に6軸IMUセンサー（加速度+角速度）データに対応予定：
```json
{
  "acceleration": {"x": 0.12, "y": 9.81, "z": -0.05},
  "gyroscope": {"x": 12.5, "y": -3.2, "z": 0.8}
}
```

現在は任意のJSONデータで動作確認可能です。
