"""subscriber.py のユニットテスト"""
import subprocess
import sys
from unittest.mock import MagicMock, patch, AsyncMock


def test_workspace_root_detection():
    """git rev-parse --show-toplevel でワークスペースルートを取得できることを確認"""
    # 実際に git コマンドを実行してリポジトリルートを取得
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        workspace_root = result.stdout.strip()
        print(f"✅ workspace_root detected: {workspace_root}")
        assert workspace_root != ""
        assert workspace_root.endswith("iot-ai-agent")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ git rev-parse failed: {e.stderr}")
        return False
    except FileNotFoundError:
        print("❌ git command not found")
        return False
    except Exception as e:
        print(f"❌ error: {e}")
        return False


def test_handle_message_with_workspace_root():
    """_handle_message が run_agent に workspace_root を渡すことを確認"""
    import asyncio
    from iot import subscriber
    
    # モックの workspace_root を設定
    subscriber._workspace_root = "/test/workspace"
    
    # run_agent をモック化（AsyncMock を使用）
    with patch("agent.graph.run_agent", new_callable=AsyncMock) as mock_run_agent:
        mock_run_agent.return_value = "test response"
        
        # broadcast もモック化
        with patch("api.events.broadcast", new_callable=AsyncMock) as mock_broadcast:
            mock_broadcast.return_value = None
            
            # _handle_message を実行
            test_message = {"test": "data"}
            asyncio.run(subscriber._handle_message("test/topic", test_message))
            
            # run_agent が workspace_root 付きで呼ばれたことを確認
            mock_run_agent.assert_called_once()
            call_args = mock_run_agent.call_args
            assert call_args[0][0] == test_message
            assert call_args[1]["workspace_root"] == "/test/workspace"
            
            print("✅ _handle_message correctly passes workspace_root to run_agent")
            return True


def test_setup_extracts_workspace_root():
    """setup() が _workspace_root をグローバル変数に設定することを確認"""
    import asyncio
    from unittest.mock import MagicMock
    from iot import subscriber
    
    # 環境変数をモック化
    with patch.dict("os.environ", {
        "AWS_IOT_ENDPOINT": "test.endpoint",
        "AWS_ACCESS_KEY_ID": "test_key",
        "AWS_SECRET_ACCESS_KEY": "test_secret",
    }):
        # MQTT接続関連をモック化
        with patch("iot.subscriber.mqtt_connection_builder") as mock_builder:
            mock_connection = MagicMock()
            mock_builder.websockets_with_default_aws_signing.return_value = mock_connection
            mock_connection.connect.return_value.result.return_value = None
            mock_connection.subscribe.return_value = (MagicMock(), None)
            mock_connection.subscribe.return_value[0].result.return_value = None
            
            # setup を実行
            loop = asyncio.new_event_loop()
            subscriber.setup(loop)
            
            # _workspace_root が設定されていることを確認
            assert subscriber._workspace_root != ""
            print(f"✅ setup() set _workspace_root: {subscriber._workspace_root}")
            
            # cleanup
            subscriber._mqtt_connection = None
            loop.close()
            return True


if __name__ == "__main__":
    print("=" * 60)
    print("Testing subscriber.py modifications")
    print("=" * 60)
    
    tests = [
        ("Workspace root detection", test_workspace_root_detection),
        ("Handle message with workspace_root", test_handle_message_with_workspace_root),
        ("Setup extracts workspace_root", test_setup_extracts_workspace_root),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        print(f"\n[TEST] {name}")
        print("-" * 60)
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    sys.exit(0 if failed == 0 else 1)
