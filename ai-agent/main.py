import asyncio
import contextlib

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from api.routes import router
from iot import subscriber


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    loop = asyncio.get_event_loop()
    # MQTT 接続はブロッキングなので別スレッドで実行
    await asyncio.get_event_loop().run_in_executor(None, subscriber.setup, loop)
    yield
    await asyncio.get_event_loop().run_in_executor(None, subscriber.teardown)


app = FastAPI(title="ai-agent", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(router)


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)

