import asyncio
import logging
from typing import List, Optional
from datetime import datetime

# ロガーの設定
logger = logging.getLogger(__name__)

# SSE クライアントごとのキューを管理するリスト
_subscribers: List[asyncio.Queue] = []


def add_subscriber() -> asyncio.Queue:
    """
    新しいSSEクライアントを登録し、専用のキューを返す
    
    Returns:
        asyncio.Queue: クライアント専用のイベントキュー
    """
    q: asyncio.Queue = asyncio.Queue()
    _subscribers.append(q)
    logger.info(f"New subscriber added. Total subscribers: {len(_subscribers)}")
    return q


def remove_subscriber(q: asyncio.Queue) -> None:
    """
    SSEクライアントの登録を解除する
    
    Args:
        q: 削除するクライアントのキュー
    """
    try:
        _subscribers.remove(q)
        logger.info(f"Subscriber removed. Total subscribers: {len(_subscribers)}")
    except ValueError:
        logger.warning("Attempted to remove non-existent subscriber")


async def broadcast(event: dict) -> None:
    """
    すべてのSSEクライアントにイベントをブロードキャストする
    
    Args:
        event: 送信するイベント辞書
    """
    if not _subscribers:
        logger.debug("No subscribers to broadcast to")
        return
    
    # タイムスタンプを追加（イベントに timestamp がない場合）
    if 'timestamp' not in event:
        event['timestamp'] = datetime.utcnow().isoformat()
    
    logger.info(f"Broadcasting event to {len(_subscribers)} subscribers: {event.get('type', 'unknown')}")
    
    # 切断されたクライアントのキューを追跡
    failed_queues = []
    
    for q in list(_subscribers):
        try:
            # ノンブロッキングでキューに追加（キューが満杯の場合はスキップ）
            if q.qsize() < 100:  # キューサイズの上限を設定
                await q.put(event)
            else:
                logger.warning(f"Queue is full ({q.qsize()} items), skipping subscriber")
                failed_queues.append(q)
        except Exception as e:
            logger.error(f"Error broadcasting to subscriber: {e}")
            failed_queues.append(q)
    
    # 失敗したキューを削除
    for q in failed_queues:
        remove_subscriber(q)


def get_subscriber_count() -> int:
    """
    現在のサブスクライバー数を返す
    
    Returns:
        int: アクティブなサブスクライバーの数
    """
    return len(_subscribers)


async def broadcast_system_event(message: str, level: str = "info") -> None:
    """
    システムイベントをブロードキャストするヘルパー関数
    
    Args:
        message: メッセージ内容
        level: ログレベル (info, warning, error)
    """
    event = {
        "type": "system",
        "level": level,
        "message": message
    }
    await broadcast(event)


async def broadcast_sensor_data(sensor_id: str, data: dict) -> None:
    """
    センサーデータをブロードキャストするヘルパー関数
    
    Args:
        sensor_id: センサーID
        data: センサーデータ
    """
    event = {
        "type": "sensor_data",
        "sensor_id": sensor_id,
        "data": data
    }
    await broadcast(event)


async def broadcast_ai_response(query: str, response: str, metadata: Optional[dict] = None) -> None:
    """
    AI応答をブロードキャストするヘルパー関数
    
    Args:
        query: ユーザーのクエリ
        response: AIの応答
        metadata: 追加のメタデータ（オプション）
    """
    event = {
        "type": "ai_response",
        "query": query,
        "response": response,
        "metadata": metadata or {}
    }
    await broadcast(event)
