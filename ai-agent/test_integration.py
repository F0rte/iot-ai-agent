"""subscriber.py の統合テスト - workspace_root が正しく連携するかを確認"""
import asyncio
import sys
from unittest.mock import patch, AsyncMock, MagicMock


async def integration_test():
    """統合テスト: subscriber -> graph -> tools の連携を確認"""
    from iot import subscriber
    from agent import tools
    
    print("🧪 統合テスト開始")
    print("=" * 60)
    
    # 1. setup() でworkspace_rootが設定されることを確認
    print("\n[Step 1] setup() でworkspace_rootを取得")
    
    with patch.dict("os.environ", {
        "AWS_IOT_ENDPOINT": "test.endpoint",
        "AWS_ACCESS_KEY_ID": "test_key",
        "AWS_SECRET_ACCESS_KEY": "test_secret",
    }):
        with patch("iot.subscriber.mqtt_connection_builder") as mock_builder:
            mock_connection = MagicMock()
            mock_builder.websockets_with_default_aws_signing.return_value = mock_connection
            mock_connection.connect.return_value.result.return_value = None
            mock_connection.subscribe.return_value = (MagicMock(), None)
            mock_connection.subscribe.return_value[0].result.return_value = None
            
            loop = asyncio.new_event_loop()
            subscriber.setup(loop)
            
            assert subscriber._workspace_root != ""
            print(f"  ✅ workspace_root: {subscriber._workspace_root}")
            
            # 2. _handle_message経由でset_workspace_rootが呼ばれることを確認
            print("\n[Step 2] _handle_message から run_agent への workspace_root 渡し")
            
            original_set_workspace = tools.set_workspace_root
            workspace_set_called = []
            
            def mock_set_workspace(path: str):
                workspace_set_called.append(path)
                original_set_workspace(path)
            
            with patch("agent.tools.set_workspace_root", side_effect=mock_set_workspace):
                with patch("agent.graph.graph.ainvoke", new_callable=AsyncMock) as mock_ainvoke:
                    mock_ainvoke.return_value = {"agent_response": "test response"}
                    
                    with patch("api.events.broadcast", new_callable=AsyncMock):
                        test_message = {"test": "data"}
                        await subscriber._handle_message("test/topic", test_message)
                        
                        # workspace_root が set_workspace_root に渡されていることを確認
                        assert len(workspace_set_called) > 0
                        assert workspace_set_called[0] == subscriber._workspace_root
                        print(f"  ✅ set_workspace_root が呼ばれました: {workspace_set_called[0]}")
            
            # 3. tools._workspace_rootが設定されていることを確認
            print("\n[Step 3] tools._workspace_root の確認")
            print(f"  ✅ tools._workspace_root: {tools._workspace_root}")
            
            # cleanup
            subscriber._mqtt_connection = None
            loop.close()
    
    print("\n" + "=" * 60)
    print("✅ 統合テスト成功: subscriber -> graph -> tools の連携が正常に動作")
    print("=" * 60)
    return True


if __name__ == "__main__":
    try:
        result = asyncio.run(integration_test())
        sys.exit(0 if result else 1)
    except Exception as e:
        print(f"\n❌ 統合テスト失敗: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
