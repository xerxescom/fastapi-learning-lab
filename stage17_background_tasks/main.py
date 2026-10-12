"""Stage 17：注册资料后通过 BackgroundTasks 发送模拟通知。"""

import logging
from collections.abc import Callable
from uuid import UUID

from fastapi import BackgroundTasks, FastAPI, HTTPException, Response

from app.schemas import Mail, NotificationRead, RegistrationResponse, UserCreate, UserRead
from app.state import LabState
from app.tasks import send_welcome_email

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")


def create_app(*, state: LabState | None = None, sender: Callable[[Mail], None] | None = None) -> FastAPI:
    state = state if state is not None else LabState()
    sender = sender if sender is not None else state.send_demo_mail
    application = FastAPI(title="Stage 17：后台任务与邮件发送模拟")

    @application.post("/users", status_code=201, response_model=RegistrationResponse)
    def register(body: UserCreate, background_tasks: BackgroundTasks, response: Response) -> RegistrationResponse:
        user, notification = state.register(body)
        # 传不可变的任务参数；不要在路由里直接调用耗时发送函数。
        background_tasks.add_task(
            send_welcome_email,
            notification_id=notification.id, recipient=user.email, username=user.username,
            state=state, sender=sender,
        )
        response.headers["Cache-Control"] = "no-store"
        return RegistrationResponse(user=user, notification=notification)

    @application.get("/users/{user_id}", response_model=UserRead)
    def read_user(user_id: int, response: Response) -> UserRead:
        user = state.get_user(user_id)
        if user is None:
            raise HTTPException(404, "User not found")
        response.headers["Cache-Control"] = "no-store"
        return user

    @application.get("/notifications/{notification_id}", response_model=NotificationRead)
    def read_notification(notification_id: UUID, response: Response) -> NotificationRead:
        notification = state.get_notification(notification_id)
        if notification is None:
            raise HTTPException(404, "Notification not found")
        response.headers["Cache-Control"] = "no-store"
        return notification

    @application.get("/demo/outbox", response_model=list[Mail])
    def outbox(response: Response) -> list[Mail]:
        response.headers["Cache-Control"] = "no-store"
        return state.outbox()

    return application


app = create_app()
