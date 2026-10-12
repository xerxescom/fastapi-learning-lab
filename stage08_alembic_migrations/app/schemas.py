"""请求校验与 ORM 响应序列化。"""

from pydantic import BaseModel, ConfigDict, Field


class ItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    price: float = Field(gt=0, allow_inf_nan=False)
    in_stock: bool = True


class ItemRead(ItemCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
