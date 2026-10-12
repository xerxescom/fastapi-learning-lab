from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, StringConstraints


class UserCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^[a-z][a-z0-9_]{2,29}$")]
    email: EmailStr


class UserRead(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int
    username: str
    email: str


class NotificationRead(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: UUID
    user_id: int
    status: Literal["pending", "running", "succeeded", "failed"] = "pending"
    attempts: int = 0
    error: str | None = None


class RegistrationResponse(BaseModel):
    user: UserRead
    notification: NotificationRead


class Mail(BaseModel):
    model_config = ConfigDict(frozen=True)

    notification_id: UUID
    recipient: str
    subject: str
    body: str
