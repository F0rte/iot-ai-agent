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

    # テストデータ1: 静止状態（magnitude ≒ 9.8 m/s²）
    test_message_1 = {
        "acceleration": {"x": 0.1, "y": 9.8, "z": 0.1},
        "gyroscope": {"x": 0.1, "y": 0.1, "z": 0.1},
    }

    # テストデータ2: 走行中（magnitude > 12.0 m/s²）→ running_start
    test_message_2 = {
        "acceleration": {"x": 3.0, "y": 9.8, "z": 7.5},
        "gyroscope": {"x": 12.5, "y": -3.2, "z": 0.8},
    }

    # テストデータ3: 走行継続（none）
    test_message_3 = {
        "acceleration": {"x": 2.5, "y": 9.8, "z": 8.0},
        "gyroscope": {"x": 10.0, "y": -2.0, "z": 1.0},
    }

    # テストデータ4: 静止に戻る → running_stop
    test_message_4 = {
        "acceleration": {"x": 0.1, "y": 9.8, "z": 0.2},
        "gyroscope": {"x": 0.1, "y": 0.1, "z": 0.1},
    }

    # テストデータ5: 心拍センサーデータ（triggerには関係しない）
    test_message_5 = {
        "heart_rate": 145,
        "heart_rate_variability": 30,
    }

    test_messages = [test_message_1, test_message_2, test_message_3, test_message_4, test_message_5]

    for i, msg in enumerate(test_messages, 1):
        print(f"\n{'='*60}")
        print(f"テスト {i}/{len(test_messages)}")
        print(f"{'='*60}")
        print(f"\n📨 送信データ:")
        print(json.dumps(msg, indent=2, ensure_ascii=False))

        try:
            print(f"\n⏳ エージェント処理中...")
            result = await graph.ainvoke({
                "iot_message": msg,
                "agent_response": "",
                "sensor_type": "",
                "trigger": "none",
                "messages": [],
            })
            print(f"\n🔍 センサー種別: {result['sensor_type']}")
            print(f"🎯 トリガー: {result['trigger']}")
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
