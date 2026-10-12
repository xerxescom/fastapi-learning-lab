"""显式声明成功、错误及业务数据模型。"""

from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class SuccessResponse(BaseModel, Generic[T]):
    code: Literal[0] = 0
    message: str = "ok"
    data: T


class ValidationIssue(BaseModel):
    loc: list[str | int]
    message: str
    type: str


class ValidationDetails(BaseModel):
    errors: list[ValidationIssue]


class ErrorResponse(BaseModel):
    code: int
    message: str
    data: ValidationDetails | None = None


class ItemRead(BaseModel):
    id: int
    name: str
    price: float
    stock: int


class QuoteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    quantity: int = Field(ge=1, le=10)


class QuoteRead(BaseModel):
    item_id: int
    quantity: int
    total: float
