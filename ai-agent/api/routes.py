import asyncio
import json
import logging

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from api.events import add_subscriber, remove_subscriber

logger = logging.getLogger(__name__)

router = APIRouter()


async def _event_generator(q: asyncio.Queue):
    """
    SSEイベントストリームのジェネレーター
    
    Args:
        q: クライアント専用のイベントキュー
    """
    try:
        while True:
            try:
                # 30秒のタイムアウトでイベントを待つ
                event = await asyncio.wait_for(q.get(), timeout=30.0)
                # SSE形式でイベントを送信
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            except asyncio.TimeoutError:
                # 接続維持のための ping（ハートビート）
                yield "data: {\"type\": \"ping\"}\n\n"
    except asyncio.CancelledError:
        logger.info("Event generator cancelled (client disconnected)")
    except Exception as e:
        logger.error(f"Error in event generator: {e}")
    finally:
        # クライアント切断時にサブスクライバーを削除
        remove_subscriber(q)
        logger.info("Event generator finished, subscriber removed")


@router.get("/events")
async def sse_events():
    """
    Server-Sent Events (SSE) エンドポイント
    
    クライアントはこのエンドポイントに接続することで、
    リアルタイムでサーバーからのイベントを受信できます。
    
    Returns:
        StreamingResponse: SSEストリーム
    """
    logger.info("New SSE connection established")
    q = add_subscriber()
    
    return StreamingResponse(
        _event_generator(q),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",
            "Connection": "keep-alive",
        },
    )


@router.get("/events/health")
async def events_health():
    """
    SSEサービスのヘルスチェックエンドポイント
    
    Returns:
        dict: サービスの状態情報
    """
    from api.events import get_subscriber_count
    
    return {
        "status": "ok",
        "subscribers": get_subscriber_count(),
    }


@router.post("/start-agent")
async def start_agent(request: dict):
    """
    自律開発エージェントを起動するエンドポイント。

    Request body:
        plan_content (str): エージェントに渡す実行計画のテキスト
        model_tier (str, optional): モデルティア ("sonnet" | "sonnet-3" | "haiku")。デフォルト "sonnet"

    Returns:
        dict: 起動結果
    """
    import os
    from agent.graph import run_dev_agent
    from agent.tools import set_workspace_root

    plan_content = request.get("plan_content", "")
    model_tier = request.get("model_tier", "sonnet")

    if not plan_content:
        return {"status": "error", "message": "plan_content is required"}

    # workspace_root はプロジェクトルートを使用
    workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    set_workspace_root(workspace_root)

    # plan.md に書き込む
    plan_path = os.path.join(workspace_root, "docs", "plan.md")
    os.makedirs(os.path.dirname(plan_path), exist_ok=True)
    with open(plan_path, "w", encoding="utf-8") as f:
        f.write(plan_content)

    # バックグラウンドでエージェント起動
    asyncio.create_task(run_dev_agent(workspace_root, model_tier=model_tier))
    logger.info(f"start-agent: workspace={workspace_root}, model_tier={model_tier}")

    return {"status": "started", "workspace_root": workspace_root, "model_tier": model_tier}

