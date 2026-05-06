"""阶段 02：路径参数与查询参数。"""

from fastapi import FastAPI, Query

app = FastAPI(
    title="FastAPI 学习实验室 - 阶段 02",
    version="0.1.0",
    description="演示路径参数、查询参数与基础校验。",
)


@app.get("/users/{user_id}")
def get_user(user_id: int) -> dict[str, int]:
    """路径参数示例：user_id 会自动进行类型转换与校验。"""
    return {"user_id": user_id}


@app.get("/items")
def list_items(
    limit: int = Query(10, ge=1, le=50, description="单次返回数量，范围 1~50"),
    offset: int = Query(0, ge=0, description="起始偏移量，最小为 0"),
    is_active: bool = Query(True, description="是否仅查看激活数据"),
) -> dict[str, int | bool]:
    """查询参数示例：包含默认值与范围校验。"""
    return {"limit": limit, "offset": offset, "is_active": is_active}
