"""阶段 02：路径参数与查询参数示例。"""

from fastapi import FastAPI, Query

app = FastAPI(
    title="FastAPI 学习实验室 - 阶段 02",
    version="0.1.0",
    description="演示路径参数、查询参数与基础类型校验。",
)


@app.get("/users/{user_id}")
def get_user(user_id: int, short: bool = False) -> dict[str, int | str | bool]:
    """路径参数 user_id 为 int，并演示 bool 查询参数 short。"""
    return {
        "user_id": user_id,
        "username": f"user-{user_id}",
        "short": short,
    }


@app.get("/items")
def list_items(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    q: str = "",
    active: bool = True,
) -> dict[str, int | str | bool]:
    """查询参数示例：limit/offset/q/active。"""
    return {
        "limit": limit,
        "offset": offset,
        "q": q,
        "active": active,
    }
