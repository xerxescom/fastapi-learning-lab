"""查询参数模型及两种分页响应。"""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator


class FilterParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    q: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)] | None = None
    category: Literal["office", "accessories"] | None = None
    in_stock: bool | None = None
    min_price: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    max_price: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    sort_by: Literal["id", "name", "price"] = "id"
    order: Literal["asc", "desc"] = "asc"

    @model_validator(mode="after")
    def validate_price_range(self) -> "FilterParams":
        if self.min_price is not None and self.max_price is not None and self.min_price > self.max_price:
            raise ValueError("min_price must be less than or equal to max_price")
        return self


class OffsetParams(FilterParams):
    limit: int = Field(default=10, ge=1, le=100)
    offset: int = Field(default=0, ge=0, le=1_000_000)


class PageParams(FilterParams):
    page: int = Field(default=1, ge=1, le=10_000)
    page_size: int = Field(default=10, ge=1, le=100)


class ItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    price: float
    category: str
    in_stock: bool


class OffsetResponse(BaseModel):
    items: list[ItemRead]
    total: int
    limit: int
    offset: int


class PageResponse(BaseModel):
    items: list[ItemRead]
    total: int
    page: int
    page_size: int
    pages: int
