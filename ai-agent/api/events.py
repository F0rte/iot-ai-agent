import asyncio
from typing import List

# SSE クライアントごとのキューを管理するリスト
_subscribers: List[asyncio.Queue] = []


def add_subscriber() -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue()
    _subscribers.append(q)
    return q


def remove_subscriber(q: asyncio.Queue) -> None:
    try:
        _subscribers.remove(q)
    except ValueError:
        pass


async def broadcast(event: dict) -> None:
    for q in list(_subscribers):
        await q.put(event)
