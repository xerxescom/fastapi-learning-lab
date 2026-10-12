"""单进程教学用会话存储；生产环境应使用成熟的共享会话方案。"""

from collections.abc import Callable
from dataclasses import dataclass
from secrets import token_urlsafe
from threading import Lock
from time import monotonic

from fastapi import HTTPException


@dataclass(frozen=True)
class Session:
    session_id: str
    csrf_token: str
    username: str | None
    expires_at: float


class SessionStore:
    def __init__(self, ttl: int, *, clock: Callable[[], float] = monotonic, capacity: int = 1000):
        self.ttl = ttl
        self.clock = clock
        self.capacity = capacity
        self._sessions: dict[str, Session] = {}
        self._lock = Lock()

    def get(self, session_id: str | None) -> Session | None:
        with self._lock:
            session = self._sessions.get(session_id) if session_id else None
            if session is not None and session.expires_at <= self.clock():
                self._sessions.pop(session.session_id)
                return None
            return session

    def create(self, *, username: str | None = None, previous_id: str | None = None) -> Session:
        with self._lock:
            now = self.clock()
            # 新建时回收过期记录，并限制容量，避免匿名会话无限增长。
            self._sessions = {key: value for key, value in self._sessions.items() if value.expires_at > now}
            if previous_id:
                self._sessions.pop(previous_id, None)
            if len(self._sessions) >= self.capacity:
                raise HTTPException(503, "Session capacity reached")
            session = Session(token_urlsafe(32), token_urlsafe(32), username, now + self.ttl)
            self._sessions[session.session_id] = session
            return session

    def delete(self, session_id: str) -> None:
        with self._lock:
            self._sessions.pop(session_id, None)
