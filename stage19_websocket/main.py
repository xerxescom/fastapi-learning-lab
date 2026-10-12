"""Stage 19：文本 JSON 协议的单房间 WebSocket 聊天室。"""

from typing import Annotated

from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from app.chat import MAX_MESSAGE_BYTES, ChatMessage, ConnectionManager

DEFAULT_ORIGINS = {"http://127.0.0.1:8000", "http://localhost:8000"}


def create_app(*, allowed_origins: set[str] | None = None, capacity: int = 20) -> FastAPI:
    origins = DEFAULT_ORIGINS if allowed_origins is None else allowed_origins
    manager = ConnectionManager(capacity=capacity)
    application = FastAPI(title="Stage 19：WebSocket 入门")

    @application.get("/health")
    async def health() -> dict:
        return {"status": "ok", "online": manager.online}

    @application.websocket("/ws/chat")
    async def chat(websocket: WebSocket, name: Annotated[str, Query(pattern=r"^[a-z][a-z0-9_]{2,19}$")]):
        origin = websocket.headers.get("origin")
        # 浏览器会发送 Origin；命令行可不发送，但 Origin 不是身份凭证。
        if origin is not None and origin not in origins:
            await websocket.close(code=1008, reason="Origin not allowed")
            return
        await websocket.accept()
        connection = None
        try:
            connection = await manager.connect(websocket, name)
            if connection is None:
                return
            while True:
                event = await websocket.receive()
                if event["type"] == "websocket.disconnect":
                    raise WebSocketDisconnect(event.get("code", 1000))
                if event.get("bytes") is not None:
                    await websocket.close(code=1003, reason="Text JSON messages only")
                    return
                raw = event.get("text", "")
                if len(raw.encode("utf-8")) > MAX_MESSAGE_BYTES:
                    await websocket.close(code=1009, reason="Message exceeds 4096 bytes")
                    return
                try:
                    message = ChatMessage.model_validate_json(raw)
                except ValidationError:
                    await websocket.close(code=1008, reason="Invalid chat message")
                    return
                await manager.broadcast(connection, message.text)
        except (WebSocketDisconnect, OSError, TimeoutError):
            pass
        finally:
            if connection is not None:
                manager.disconnect(connection.id)

    return application


app = create_app()
