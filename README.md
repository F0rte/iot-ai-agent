# 🏃‍♂️ Running Driven Development (RDD) Agent

エンジニアの運動不足を解消する、新感覚の開発体験。
**「あなたが走っている間だけ、AIが代わりにコードを書く」** 自律型AIエージェントシステムです。

## 🌟 プロジェクト概要

本プロジェクトは、Apple WatchのセンサーデータとローカルPCの開発環境をAWS経由でリアルタイムに連動させます。
ユーザーがランニングを開始すると、エディタ裏で待機していたAIエージェントが起動し、設計書の読み込みから実装、テスト、Pull Requestの作成までを自律的に行います。

AIエージェントのコアロジックは独立したCLIツールとして設計されているため、VS Codeからの利用だけでなく、Neovim等を用いたターミナル駆動開発の環境からでもシームレスに実行可能です。

## 🛠 技術スタック

システムは大きく3つのサブプロジェクト（役割）で構成されています。

### 1. Watch Controller (iOS / watchOS)
* **言語/FW**: Swift, SwiftUI, watchOS SDK
* **主要技術**: CoreMotion / HealthKit (センサー取得)
* **通信**: AWS IoT Core (MQTT over WebSockets) または AWS SDK for iOS

### 2. Editor Integration (VS Code Extension)
* **言語/FW**: TypeScript, Node.js
* **主要技術**: VS Code Extension API
* **通信**: `aws-iot-device-sdk-v2` (MQTT Subscribe)

### 3. Autonomous AI Agent (Core Logic)
* **言語/FW**: Python または TypeScript
* **主要技術**: LangGraph (ワークフロー・状態管理)
* **AIモデル**: Amazon Bedrock (Claude 3.5 Sonnet)
* **ツール連携**: MCP (Model Context Protocol) サーバーの実装（ファイル操作、コマンド実行、Git操作）

---

## 📁 ディレクトリ構成

このリポジトリはモノレポ構成となっており、各役割ごとにディレクトリが分割されています。

```text
.
├── infrastructure/       # AWSインフラ構築用（CDK, CloudFormationなど）
├── watch-app/            # ウェアラブル/モバイルアプリ用（Swiftなどを想定）
├── vscode-extension/     # エディタUI・コントローラー用（Node.js / TSなどを想定）
├── ai-agent/             # 自律AIエージェントのコアロジック（言語自由）
└── README.md
```

---

## 📝 開発・運用ルール

### AIエージェントのGitコミット規約

最終的なアウトプット（Pull Request）の品質を保つため、AIエージェントが自動生成するGitのコミットメッセージは、本リポジトリのルールとして以下の形式をプロンプトで厳格に強制します。

* **言語**: コミットメッセージは必ず**英語表記**とすること。
* **フォーマット**: `prefix: hoge fuga` 形式に従うこと。
* *(例: `feat: implement user login function`, `fix: resolve layout bug on dashboard`)*



### 環境変数の取り扱い

AWSのアクセスキーを含む `.env` ファイルや `Config.swift` は絶対にGitにコミットしないでください。
（※各ディレクトリの `.gitignore` に必ず追加すること）
