"""带锁的内存状态，独立应用实例之间不共享数据。"""

from threading import Lock
from uuid import UUID, uuid4

from fastapi import HTTPException

from app.schemas import Mail, NotificationRead, UserCreate, UserRead


class LabState:
    def __init__(self, capacity: int = 1000):
        self.capacity = capacity
        self._lock = Lock()
        self._users: dict[int, UserRead] = {}
        self._notifications: dict[UUID, NotificationRead] = {}
        self._outbox: list[Mail] = []

    def register(self, body: UserCreate) -> tuple[UserRead, NotificationRead]:
        with self._lock:
            if any(user.username == body.username or user.email.casefold() == str(body.email).casefold() for user in self._users.values()):
                raise HTTPException(409, "Username or email already registered")
            if len(self._users) >= self.capacity:
                raise HTTPException(503, "Demo registration capacity reached")
            user = UserRead(id=len(self._users) + 1, username=body.username, email=str(body.email))
            notification = NotificationRead(id=uuid4(), user_id=user.id)
            self._users[user.id] = user
            self._notifications[notification.id] = notification
            return user, notification

    def get_user(self, user_id: int) -> UserRead | None:
        with self._lock:
            return self._users.get(user_id)

    def get_notification(self, notification_id: UUID) -> NotificationRead | None:
        with self._lock:
            return self._notifications.get(notification_id)

    def start_notification(self, notification_id: UUID) -> bool:
        with self._lock:
            notification = self._notifications.get(notification_id)
            if notification is None or notification.status != "pending":
                return False
            self._notifications[notification_id] = notification.model_copy(update={"status": "running", "attempts": notification.attempts + 1})
            return True

    def finish_notification(self, notification_id: UUID, *, error: str | None = None) -> None:
        with self._lock:
            notification = self._notifications[notification_id]
            self._notifications[notification_id] = notification.model_copy(update={"status": "failed" if error else "succeeded", "error": error})

    def send_demo_mail(self, mail: Mail) -> None:
        if mail.recipient.casefold() == "fail@example.com":
            raise RuntimeError("simulated mail transport failure")
        with self._lock:
            self._outbox.append(mail)

    def outbox(self) -> list[Mail]:
        with self._lock:
            return list(self._outbox)
