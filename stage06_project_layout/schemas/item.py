"""商品相关 Pydantic 模型。"""

from pydantic import BaseModel, Field


class ItemCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    price: float = Field(..., gt=0)
    in_stock: bool = True


class ItemRead(BaseModel):
    id: int
    name: str
    price: float
    in_stock: bool


class ItemResponse(BaseModel):
    code: int = 0
    message: str = "ok"
    data: ItemRead


class ItemListResponse(BaseModel):
    code: int = 0
    message: str = "ok"
    data: list[ItemRead]
