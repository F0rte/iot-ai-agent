# AI Agent

Apple Watch の走行検知をトリガーに、**planner → coder → reviewer** のマルチエージェントが  
`docs/plan.md` を読んでタスクを分解し、コードの実装・レビューを人間なしに自律的に進める。

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
AWS_BEDROCK_REGION=us-east-1
```

### 2. 依存関係のインストール

```bash
uv sync
```

---

## 🧪 ローカルテスト（サーバー不要）

### IoTトリガーテスト

走行開始・終了のトリガー検知とセンサー分類を確認します。

```bash
uv run python test_agent.py
```

### 自律開発エージェントを直接実行

`docs/plan.md` を用意すれば、IoTトリガーなしに自律開発を試せます。

**1. `docs/plan.md` を作成する**

plannerが読むファイル。**実現したいことを自然言語で自由に記述するだけでOKです。**  
AIが既存コードを読んだ上で、具体的なタスクに分解します。

```markdown
# やりたいこと

ユーザー認証機能を追加したい。
JWTベースで、ログイン・ログアウト・トークンリフレッシュが必要。
パスワードは bcrypt でハッシュ化すること。
```

**2. スクリプトから実行する**

```python
import asyncio
from agent.dev_graph import run_dev_agent

asyncio.run(run_dev_agent(
    workspace_root="/path/to/your/project",  # プロジェクトのルートパス
    model_tier="sonnet",                     # 使用するモデルティア（省略時: "haiku"）
))
```

または `uv run` で直接実行：

```bash
uv run python -c "
import asyncio
from agent.dev_graph import run_dev_agent
asyncio.run(run_dev_agent('/path/to/your/project', model_tier='sonnet'))
"
```

#### モデルティアの指定

`model_tier` パラメータで使用モデルを制御できます。

| `model_tier` | planner / coder | reviewer |
|---|---|---|
| `"haiku"` | Claude 3 Haiku（高速・低コスト） | Claude 3 Haiku |
| `"sonnet"` | Claude 3.5 Sonnet（バランス型） | Claude 3 Haiku |
| `"opus"` | Claude 3 Opus（高性能） | Claude 3.5 Sonnet |

> **Note:** reviewer は常に1ティア下のモデルを使用します。  
> IoTトリガー経由の場合は走行時の加速度 magnitude から自動決定されます（`<12→haiku`, `12–18→sonnet`, `≥18→opus`）。

---

## 🤖 アーキテクチャ

### IoTトリガー処理（`agent/graph.py`）

```
IoTメッセージ受信
  └─ classify（センサー種別判定: motion / heart_rate / unknown）
        ├─ motion → trigger_check（加速度から走行状態を判定）
        │     ├─ running_start → notify_start → 自律開発エージェント起動
        │     ├─ running_stop  → notify_stop  → 走行フラグをOFFに
        │     └─ none          → END
        └─ heart_rate / unknown → agent（LLM + ToolNode ReAct）→ END
```

### 自律開発エージェント（`agent/dev_graph.py`）

```
run_dev_agent(workspace_root) が呼ばれると:
  └─ planner（docs/plan.md を読んでタスクに分解）
        ↓
     ループ（タスクがある & 走行中の間）:
       ├─ coder    （1タスク分のコードを実装・write_file で書き込み）
       ├─ reviewer （実装をレビュー・docs/review.md に書き出し）
       └─ running_check（走行継続 → 次タスクへ / 停止 → END）
```

---

## 📁 プロジェクト構成

```
ai-agent/
├── main.py              # FastAPIサーバーのエントリポイント
├── test_agent.py        # IoTトリガーのローカルテストスクリプト
├── agent/
│   ├── state.py         # AgentState / DevAgentState の型定義
│   ├── graph.py         # IoTセンサー処理グラフ（トリガー検知）
│   ├── dev_graph.py     # 自律開発マルチエージェントグラフ
│   └── tools.py         # エージェントが使うツール群
├── iot/
│   └── subscriber.py    # AWS IoT Core MQTTサブスクライバー
├── api/
│   ├── routes.py        # FastAPI ルート定義
│   └── events.py        # SSE イベント管理
├── pyproject.toml       # 依存関係定義
└── .env.example         # 環境変数テンプレート
```

---

## 🛠️ ツール一覧

| ツール | 分類 | 内容 |
|--------|------|------|
| `save_record(sensor_type, data)` | センサー | データをインメモリに保存 |
| `get_history(sensor_type, n)` | センサー | 直近n件の履歴を取得 |
| `detect_anomaly(sensor_type, data)` | センサー | 閾値ベースの異常検知 |
| `read_file(path)` | ファイル | ワークスペース内のファイルを読み込む |
| `write_file(path, content)` | ファイル | ファイルを新規作成・上書き |
| `list_files(directory)` | ファイル | ディレクトリのファイル一覧を取得 |
| `run_shell(command, cwd)` | 実行 | シェルコマンドを実行（テスト・ビルド用） |

---

## 🔧 技術スタック

| レイヤー | 技術 |
|---------|------|
| 言語 | Python 3.14+ |
| LLM | AWS Bedrock (Claude 3 Haiku via Converse API) |
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
        "bedrock:Converse"
      ],
      "Resource": "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-*"
    }
  ]
}
```

### 利用可能なモデル

| モデル | Model ID | 用途 |
|-------|----------|------|
| Claude 3 Haiku | `anthropic.claude-3-haiku-20240307-v1:0` | 高速・低コスト（デフォルト） |
| Claude 3.5 Sonnet | `anthropic.claude-3-5-sonnet-20240620-v1:0` | バランス型（複雑な実装向け） |
| Claude 3 Opus | `anthropic.claude-3-opus-20240229-v1:0` | 高性能 |

モデルを変更する場合は `agent/graph.py` と `agent/dev_graph.py` の `model` を編集してください。

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
2. IAM権限で `bedrock:InvokeModel` と `bedrock:Converse` を許可

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

