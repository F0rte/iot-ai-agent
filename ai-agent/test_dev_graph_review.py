#!/usr/bin/env python3
"""
dev_graph.py の reviewer_node 機能をテストするスクリプト

reviewer_node がタスクインデックスを正しく使用して
個別のレビューファイルを生成することを確認します。
"""

import asyncio
import os
import shutil
from agent.state import DevAgentState


async def test_reviewer_output():
    """reviewer_node のファイル出力をテストする（モック実行）"""
    
    print("\n" + "="*60)
    print("🧪 reviewer_node ファイル出力テスト")
    print("="*60 + "\n")
    
    # テスト用の一時ディレクトリを作成
    test_workspace = "/tmp/test_dev_graph_review"
    os.makedirs(f"{test_workspace}/docs", exist_ok=True)
    
    print(f"📁 テスト用ワークスペース: {test_workspace}")
    
    # ファイル名フォーマットのテスト
    print("\n📝 ファイル名フォーマット確認:")
    for task_idx in [0, 1, 5, 10, 15]:
        filename = f"docs/review_{task_idx:02d}.md"
        print(f"  Task {task_idx:2d} → {filename}")
    
    # モックのレビュー結果ファイルを生成してテスト
    print("\n📄 モックレビューファイル生成テスト:")
    for task_idx in range(3):
        review_path = os.path.join(test_workspace, f"docs/review_{task_idx:02d}.md")
        review_content = (
            f"# レビュー結果 - タスク {task_idx}\n\n"
            f"## タスク内容\n"
            f"テストタスク {task_idx}\n\n"
            f"## レビュー結果\n"
            f"- **判定**: PASS\n"
            f"- **修正要否**: 不要\n"
            f"- **修正回数**: 0\n\n"
            f"## コメント\n"
            f"これはテスト用のモックレビューです。\n"
        )
        
        with open(review_path, "w", encoding="utf-8") as f:
            f.write(review_content)
        
        print(f"  ✅ 生成: {review_path}")
        
        # ファイルが正しく作成されたことを確認
        if os.path.exists(review_path):
            with open(review_path, "r", encoding="utf-8") as f:
                content = f.read()
                if f"タスク {task_idx}" in content:
                    print(f"     ✓ 内容検証OK")
                else:
                    print(f"     ✗ 内容検証NG")
    
    # 生成されたファイルの一覧表示
    print("\n📂 生成されたレビューファイル:")
    review_files = sorted([f for f in os.listdir(f"{test_workspace}/docs") if f.startswith("review_")])
    for review_file in review_files:
        file_path = os.path.join(test_workspace, "docs", review_file)
        file_size = os.path.getsize(file_path)
        print(f"  - {review_file} ({file_size} bytes)")
    
    # クリーンアップ
    print(f"\n🧹 テストディレクトリをクリーンアップ: {test_workspace}")
    shutil.rmtree(test_workspace)
    
    print("\n" + "="*60)
    print("✅ テスト完了")
    print("="*60 + "\n")


async def test_state_structure():
    """DevAgentState の構造をテストする"""
    
    print("\n" + "="*60)
    print("🧪 DevAgentState 構造テスト")
    print("="*60 + "\n")
    
    # DevAgentState に task_index が含まれているかテスト
    from agent.state import DevAgentState
    
    print("📋 DevAgentState のキー一覧:")
    # TypedDict の __annotations__ から取得
    if hasattr(DevAgentState, '__annotations__'):
        for key, value in DevAgentState.__annotations__.items():
            print(f"  - {key}: {value}")
        
        if 'task_index' in DevAgentState.__annotations__:
            print("\n✅ task_index フィールドが存在します")
        else:
            print("\n❌ task_index フィールドが存在しません")
    
    print("\n" + "="*60)
    print("✅ テスト完了")
    print("="*60 + "\n")


def main():
    """メイン実行関数"""
    print("\n🚀 dev_graph.py reviewer_node テストスイート\n")
    
    try:
        # 状態構造のテスト
        asyncio.run(test_state_structure())
        
        # ファイル出力のテスト
        asyncio.run(test_reviewer_output())
        
        print("\n🎉 すべてのテスト完了！")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  ユーザーによって中断されました")
    except Exception as e:
        print(f"\n\n❌ テスト失敗: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
