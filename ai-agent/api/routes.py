import asyncio
import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from api.events import add_subscriber, remove_subscriber

router = APIRouter()


async def _event_generator(q: asyncio.Queue):
    try:
        while True:
            try:
                event = await asyncio.wait_for(q.get(), timeout=30.0)
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            except asyncio.TimeoutError:
                # 接続維持のための ping
                yield "data: {\"type\": \"ping\"}\n\n"
    except asyncio.CancelledError:
        pass


@router.get("/events")
async def sse_events():
    q = add_subscriber()
    return StreamingResponse(
        _event_generator(q),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",
        },
        background=None,
    )
