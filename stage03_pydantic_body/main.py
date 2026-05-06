"""阶段 03：请求体与 Pydantic 模型示例。"""

from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI(
    title="FastAPI 学习实验室 - 阶段 03",
    version="0.1.0",
    description="演示请求体校验、默认值、可选字段与 response_model。",
)


class ItemCreate(BaseModel):
    """创建商品的请求体。"""

    name: str = Field(..., min_length=1, max_length=50)
    price: float = Field(..., gt=0)
    in_stock: bool = True
    description: str | None = None


class ItemResponse(BaseModel):
    """对外返回模型：隐藏内部字段，仅返回业务需要内容。"""

    id: int
    name: str
    price: float
    in_stock: bool
    description: str | None = None


@app.post("/items", response_model=ItemResponse)
def create_item(item: ItemCreate) -> dict[str, int | str | float | bool | None]:
    """使用请求体创建商品，并通过 response_model 规范输出。"""
    # 模拟数据库创建结果：包含内部字段 internal_note，最终会被 response_model 过滤。
    return {
        "id": 1,
        "name": item.name,
        "price": item.price,
        "in_stock": item.in_stock,
        "description": item.description,
        "internal_note": "only for server",
    }
