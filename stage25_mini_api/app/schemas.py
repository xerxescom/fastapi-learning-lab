from typing import Annotated, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr, StringConstraints, field_validator, model_validator

T = TypeVar("T")
Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]


class Success(BaseModel, Generic[T]):
    data: T


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: list[dict] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    error: ErrorDetail


class UserCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(min_length=3, max_length=30, pattern=r"^[a-z][a-z0-9_]*$")
    email: EmailStr = Field(max_length=254)
    password: SecretStr = Field(min_length=8, max_length=128)

    @field_validator("username", mode="before")
    @classmethod
    def normalize_username(cls, value):
        return value.strip().lower() if isinstance(value, str) else value

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value):
        return value.lower()


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    email: EmailStr
    role: Literal["user", "admin"]
    is_active: bool


class Token(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"


class TaskCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: Title
    description: str = Field(default="", max_length=2000)
    completed: bool = Field(default=False, strict=True)
    priority: int = Field(default=3, ge=1, le=5, strict=True)


class TaskPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: Title | None = None
    description: str | None = Field(default=None, max_length=2000)
    completed: bool | None = Field(default=None, strict=True)
    priority: int | None = Field(default=None, ge=1, le=5, strict=True)

    @model_validator(mode="after")
    def require_changes(self):
        if not self.model_fields_set or any(getattr(self, field) is None for field in self.model_fields_set):
            raise ValueError("Provide at least one non-null task field")
        return self


class TaskRead(TaskCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    owner_id: int


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
