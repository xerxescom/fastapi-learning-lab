"""后台任务不接收 Request、UploadFile 或请求作用域数据库会话。"""

import logging
from collections.abc import Callable
from uuid import UUID

from app.schemas import Mail
from app.state import LabState

logger = logging.getLogger("stage17.notifications")
logger.setLevel(logging.INFO)


def send_welcome_email(
    *, notification_id: UUID, recipient: str, username: str,
    state: LabState, sender: Callable[[Mail], None],
) -> None:
    if not state.start_notification(notification_id):
        return
    mail = Mail(
        notification_id=notification_id,
        recipient=recipient,
        subject="Welcome to FastAPI Learning Lab",
        body=f"Hello {username}, your demo registration is complete.",
    )
    try:
        sender(mail)
    except Exception:
        # 响应已发出，不能把注册结果改成 500；记录失败供后续查询。
        state.finish_notification(notification_id, error="Notification delivery failed")
        logger.error("notification_failed notification_id=%s", notification_id)
    else:
        state.finish_notification(notification_id)
        logger.info("notification_succeeded notification_id=%s", notification_id)
