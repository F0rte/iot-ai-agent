#!/usr/bin/env python3
"""
ローカル動作確認用テストスクリプト

サーバーやIoT接続なしで、LangGraphエージェントの動作を確認できます。

使い方:
    uv run python test_agent.py

環境変数:
    AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION (またはAWS_BEDROCK_REGION)
"""

import asyncio
import json
from dotenv import load_dotenv

# 環境変数をロード
load_dotenv()

from agent.graph import graph


async def test_with_mock_data():
    """モックデータでエージェントをテスト"""

    # テストデータ1: 心拍センサーデータ
    test_message_1 = {
        "heart_rate": 82,
        "heart_rate_variability": 45,
        "timestamp": "2026-02-28T03:00:00Z"
    }

    # テストデータ2: 動作センサーデータ（IMU）
    test_message_2 = {
        "acceleration": {
            "x": 0.12,
            "y": 9.81,
            "z": -0.05
        },
        "gyroscope": {
            "x": 12.5,
            "y": -3.2,
            "z": 0.8
        },
    }

    # テストデータ3: 不明データ（genericノードへ）
    test_message_3 = {
        "message": "Hello from Apple Watch",
        "battery": 72,
    }

    test_messages = [test_message_1, test_message_2, test_message_3]

    for i, msg in enumerate(test_messages, 1):
        print(f"\n{'='*60}")
        print(f"テスト {i}/{len(test_messages)}")
        print(f"{'='*60}")
        print(f"\n📨 送信データ:")
        print(json.dumps(msg, indent=2, ensure_ascii=False))

        try:
            print(f"\n⏳ エージェント処理中...")
            result = await graph.ainvoke({"iot_message": msg, "agent_response": "", "sensor_type": ""})
            print(f"\n🔍 センサー種別: {result['sensor_type']}")
            print(f"\n🤖 エージェント応答:")
            print(result["agent_response"])

        except Exception as e:
            print(f"\n❌ エラー発生: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n{'='*60}")
    print("✅ テスト完了")
    print(f"{'='*60}\n")


def main():
    """メイン実行関数"""
    print("\n" + "="*60)
    print("🧪 AIエージェント ローカルテスト")
    print("="*60 + "\n")

    print("📝 注意事項:")
    print("  - AWS認証情報が .env ファイルに設定されている必要があります")
    print("  - AWS Bedrockへのアクセス権限が必要です")
    print("  - インターネット接続が必要です（Bedrock API呼び出し）")
    print()

    try:
        asyncio.run(test_with_mock_data())
    except KeyboardInterrupt:
        print("\n\n⚠️  ユーザーによって中断されました")
    except Exception as e:
        print(f"\n\n❌ 予期しないエラー: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
