"""分离注册输入与公开用户响应。"""

from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr, field_validator

from app.permissions import Role


class UserCreate(BaseModel):
    # 角色和账号状态由服务端管理，拒绝公开注册时传入这些字段。
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=3, max_length=30, pattern=r"^[a-z][a-z0-9_]*$")
    email: EmailStr = Field(max_length=254)
    password: SecretStr = Field(min_length=8, max_length=128)

    @field_validator("username", mode="before")
    @classmethod
    def normalize_username(cls, value: object) -> object:
        return value.strip().lower() if isinstance(value, str) else value

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.lower()


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: EmailStr
    role: Role


class AdminUserRead(UserRead):
    is_active: bool


class UserStats(BaseModel):
    total_users: int
    active_users: int


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
