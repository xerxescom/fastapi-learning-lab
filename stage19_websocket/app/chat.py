import asyncio
from contextlib import suppress
from dataclasses import dataclass
from typing import Annotated, Literal
from uuid import uuid4

from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel, ConfigDict, StringConstraints

MAX_MESSAGE_BYTES = 4096


class ChatMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["chat"]
    text: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


@dataclass(frozen=True)
class Connection:
    id: str
    name: str
    websocket: WebSocket


class ConnectionManager:
    def __init__(self, *, capacity: int = 20, send_timeout: float = 1):
        self.capacity = capacity
        self.send_timeout = send_timeout
        self._connections: dict[str, Connection] = {}
        self._send_lock = asyncio.Lock()

    @property
    def online(self) -> int:
        return len(self._connections)

    async def connect(self, websocket: WebSocket, name: str) -> Connection | None:
        async with self._send_lock:
            if self.online >= self.capacity:
                await websocket.close(code=1013, reason="Chat is full")
                return None
            connection = Connection(uuid4().hex, name, websocket)
            self._connections[connection.id] = connection
            try:
                await asyncio.wait_for(websocket.send_json({"type": "welcome", "client_id": connection.id, "name": name, "online": self.online}), timeout=self.send_timeout)
            except BaseException:
                self.disconnect(connection.id)
                raise
            return connection

    def disconnect(self, connection_id: str) -> None:
        # 所有调用都在同一事件循环中；无 await 的删除不会被取消打断。
        self._connections.pop(connection_id, None)

    async def broadcast(self, connection: Connection, text: str) -> None:
        payload = {"type": "chat", "sender_id": connection.id, "name": connection.name, "text": text}
        # 串行发送避免两个广播同时写同一连接；快照允许断开时删除成员。
        async with self._send_lock:
            for peer in list(self._connections.values()):
                try:
                    await asyncio.wait_for(peer.websocket.send_json(payload), timeout=self.send_timeout)
                except (WebSocketDisconnect, OSError, TimeoutError):
                    self.disconnect(peer.id)
                    with suppress(WebSocketDisconnect, OSError, TimeoutError, RuntimeError):
                        await asyncio.wait_for(peer.websocket.close(code=1013, reason="Unable to deliver messages"), timeout=self.send_timeout)
