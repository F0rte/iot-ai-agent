#!/usr/bin/env python3
"""
running_check_node 関数の task_index インクリメント機能をテストする
"""

import sys
import os

# パスを追加してモジュールをインポート
sys.path.insert(0, os.path.dirname(__file__))

from agent.dev_graph import running_check_node
from agent.state import DevAgentState


def test_running_check_node_increments_task_index():
    """running_check_node が task_index を正しくインクリメントすることを確認"""
    
    print("\n" + "="*60)
    print("🧪 running_check_node task_index インクリメントテスト")
    print("="*60 + "\n")
    
    # テストケース1: task_index = 0 から始める
    print("📝 テストケース1: task_index = 0")
    state1 = {
        "workspace_root": "/test",
        "model_tier": "haiku",
        "task_list": [
            {"task": "タスク1", "read_files": [], "write_files": []},
            {"task": "タスク2", "read_files": [], "write_files": []},
        ],
        "current_task": "タスク1",
        "current_read_files": [],
        "current_write_files": [],
        "is_running": True,
        "messages": [],
        "review_result": "",
        "needs_revision": False,
        "revision_count": 0,
        "task_index": 0,
    }
    
    result1 = running_check_node(state1)
    expected_task_index1 = 1
    actual_task_index1 = result1.get("task_index")
    
    print(f"  入力 task_index: 0")
    print(f"  期待 task_index: {expected_task_index1}")
    print(f"  実際 task_index: {actual_task_index1}")
    
    if actual_task_index1 == expected_task_index1:
        print("  ✅ テストケース1 PASS")
    else:
        print("  ❌ テストケース1 FAIL")
        return False
    
    # テストケース2: task_index = 5 から始める
    print("\n📝 テストケース2: task_index = 5")
    state2 = {
        "workspace_root": "/test",
        "model_tier": "haiku",
        "task_list": [
            {"task": "タスク6", "read_files": [], "write_files": []},
        ],
        "current_task": "タスク6",
        "current_read_files": [],
        "current_write_files": [],
        "is_running": True,
        "messages": [],
        "review_result": "",
        "needs_revision": False,
        "revision_count": 0,
        "task_index": 5,
    }
    
    result2 = running_check_node(state2)
    expected_task_index2 = 6
    actual_task_index2 = result2.get("task_index")
    
    print(f"  入力 task_index: 5")
    print(f"  期待 task_index: {expected_task_index2}")
    print(f"  実際 task_index: {actual_task_index2}")
    
    if actual_task_index2 == expected_task_index2:
        print("  ✅ テストケース2 PASS")
    else:
        print("  ❌ テストケース2 FAIL")
        return False
    
    # テストケース3: タスクリストが空の場合
    print("\n📝 テストケース3: タスクリストが空")
    state3 = {
        "workspace_root": "/test",
        "model_tier": "haiku",
        "task_list": [],
        "current_task": "",
        "current_read_files": [],
        "current_write_files": [],
        "is_running": True,
        "messages": [],
        "review_result": "",
        "needs_revision": False,
        "revision_count": 0,
        "task_index": 10,
    }
    
    result3 = running_check_node(state3)
    expected_task_index3 = 11
    actual_task_index3 = result3.get("task_index")
    
    print(f"  入力 task_index: 10")
    print(f"  期待 task_index: {expected_task_index3}")
    print(f"  実際 task_index: {actual_task_index3}")
    
    if actual_task_index3 == expected_task_index3:
        print("  ✅ テストケース3 PASS")
    else:
        print("  ❌ テストケース3 FAIL")
        return False
    
    # テストケース4: 複数タスクの連続インクリメント
    print("\n📝 テストケース4: 複数タスクの連続インクリメント")
    state4 = {
        "workspace_root": "/test",
        "model_tier": "haiku",
        "task_list": [
            {"task": "タスクA", "read_files": [], "write_files": []},
            {"task": "タスクB", "read_files": [], "write_files": []},
            {"task": "タスクC", "read_files": [], "write_files": []},
        ],
        "current_task": "タスクA",
        "current_read_files": [],
        "current_write_files": [],
        "is_running": True,
        "messages": [],
        "review_result": "",
        "needs_revision": False,
        "revision_count": 0,
        "task_index": 0,
    }
    
    print("  初期 task_index: 0")
    for i in range(3):
        result = running_check_node(state4)
        task_index = result.get("task_index")
        print(f"  {i+1}回目実行後 task_index: {task_index}")
        
        if task_index != i + 1:
            print(f"  ❌ テストケース4 FAIL (期待: {i+1}, 実際: {task_index})")
            return False
        
        # 次の実行のために状態を更新
        state4 = {
            **state4,
            "task_list": result.get("task_list", []),
            "task_index": task_index,
        }
    
    print("  ✅ テストケース4 PASS")
    
    print("\n" + "="*60)
    print("✅ すべてのテスト PASS")
    print("="*60 + "\n")
    
    return True


def test_other_state_values():
    """running_check_node が他のstate値を正しく設定することを確認"""
    
    print("\n" + "="*60)
    print("🧪 running_check_node その他の状態値テスト")
    print("="*60 + "\n")
    
    state = {
        "workspace_root": "/test",
        "model_tier": "haiku",
        "task_list": [
            {"task": "タスク1", "read_files": ["file1.py"], "write_files": ["file2.py"]},
            {"task": "タスク2", "read_files": ["file3.py"], "write_files": ["file4.py"]},
        ],
        "current_task": "タスク1",
        "current_read_files": ["file1.py"],
        "current_write_files": ["file2.py"],
        "is_running": True,
        "messages": [],
        "review_result": "前回のレビュー",
        "needs_revision": True,
        "revision_count": 2,
        "task_index": 0,
    }
    
    result = running_check_node(state)
    
    print("📋 状態値の検証:")
    
    # task_list から最初の要素が削除されているか確認
    expected_task_list_len = 1
    actual_task_list_len = len(result.get("task_list", []))
    print(f"  task_list 長さ: {actual_task_list_len} (期待: {expected_task_list_len})")
    if actual_task_list_len != expected_task_list_len:
        print("  ❌ task_list FAIL")
        return False
    print("  ✅ task_list OK")
    
    # current_task が次のタスクに更新されているか確認
    expected_current_task = "タスク2"
    actual_current_task = result.get("current_task")
    print(f"  current_task: {actual_current_task} (期待: {expected_current_task})")
    if actual_current_task != expected_current_task:
        print("  ❌ current_task FAIL")
        return False
    print("  ✅ current_task OK")
    
    # revision_count がリセットされているか確認
    expected_revision_count = 0
    actual_revision_count = result.get("revision_count")
    print(f"  revision_count: {actual_revision_count} (期待: {expected_revision_count})")
    if actual_revision_count != expected_revision_count:
        print("  ❌ revision_count FAIL")
        return False
    print("  ✅ revision_count OK")
    
    # needs_revision がリセットされているか確認
    expected_needs_revision = False
    actual_needs_revision = result.get("needs_revision")
    print(f"  needs_revision: {actual_needs_revision} (期待: {expected_needs_revision})")
    if actual_needs_revision != expected_needs_revision:
        print("  ❌ needs_revision FAIL")
        return False
    print("  ✅ needs_revision OK")
    
    # review_result がクリアされているか確認
    expected_review_result = ""
    actual_review_result = result.get("review_result")
    print(f"  review_result: '{actual_review_result}' (期待: '{expected_review_result}')")
    if actual_review_result != expected_review_result:
        print("  ❌ review_result FAIL")
        return False
    print("  ✅ review_result OK")
    
    print("\n" + "="*60)
    print("✅ すべてのテスト PASS")
    print("="*60 + "\n")
    
    return True


def main():
    """メイン実行関数"""
    print("\n🚀 running_check_node テストスイート\n")
    
    try:
        # task_index インクリメントテスト
        success1 = test_running_check_node_increments_task_index()
        
        # その他の状態値テスト
        success2 = test_other_state_values()
        
        if success1 and success2:
            print("\n🎉 すべてのテスト成功！")
            return 0
        else:
            print("\n❌ 一部のテストが失敗しました")
            return 1
        
    except KeyboardInterrupt:
        print("\n\n⚠️  ユーザーによって中断されました")
        return 1
    except Exception as e:
        print(f"\n\n❌ テスト実行エラー: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
