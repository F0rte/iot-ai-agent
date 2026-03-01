import asyncio
import json
import logging
import os
import subprocess
import uuid

logger = logging.getLogger(__name__)

from awscrt import auth, mqtt
from awsiot import mqtt_connection_builder

from api.events import broadcast

_loop: asyncio.AbstractEventLoop | None = None
_mqtt_connection = None
_workspace_root: str = ""
TOPIC = "hackathon/run/test"


def _on_message_received(topic, payload, dup, qos, retain, **kwargs):
    if _loop is None:
        return
    try:
        message = json.loads(payload.decode("utf-8"))
    except Exception as e:
        print(f"[subscriber] JSON parse error: {e}")
        return

    asyncio.run_coroutine_threadsafe(_handle_message(topic, message), _loop)


async def _handle_message(topic: str, message: dict) -> None:
    from agent.graph import run_agent

    print(f"[subscriber] received: topic={topic} data={message}")
    logger.info(f"[subscriber] received: topic={topic} payload={json.dumps(message, ensure_ascii=False)}")

    # IoT 受信イベントをまず配信
    await broadcast({"type": "iot", "topic": topic, "data": message})

    # LangGraph エージェントで処理（workspace_rootを渡す）
    try:
        response = await run_agent(message, workspace_root=_workspace_root)
        await broadcast({"type": "agent", "response": response})
    except Exception as e:
        print(f"[subscriber] agent error: {e}")
        await broadcast({"type": "error", "message": str(e)})


def _on_connection_interrupted(connection, error, **kwargs):
    print(f"[subscriber] connection interrupted: {error}")


def _on_connection_resumed(connection, return_code, session_present, **kwargs):
    print(f"[subscriber] connection resumed: return_code={return_code}")


def setup(loop: asyncio.AbstractEventLoop) -> None:
    global _loop, _mqtt_connection, _workspace_root

    _loop = loop

    # git rev-parse --show-toplevel を実行してリポジトリルートを取得
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        _workspace_root = result.stdout.strip()
        print(f"[subscriber] workspace_root: {_workspace_root}")
    except subprocess.CalledProcessError as e:
        print(f"[subscriber] git rev-parse failed: {e.stderr}")
        _workspace_root = ""
    except FileNotFoundError:
        print("[subscriber] git command not found")
        _workspace_root = ""
    except Exception as e:
        print(f"[subscriber] error getting workspace_root: {e}")
        _workspace_root = ""

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
    print("[subscriber] connected to AWS IoT Core")

    subscribe_future, _ = _mqtt_connection.subscribe(
        topic=TOPIC,
        qos=mqtt.QoS.AT_LEAST_ONCE,
        callback=_on_message_received,
    )
    subscribe_future.result()
    print(f"[subscriber] subscribed to {TOPIC}")


def teardown() -> None:
    if _mqtt_connection:
        _mqtt_connection.disconnect().result()
        print("[subscriber] disconnected from AWS IoT Core")
