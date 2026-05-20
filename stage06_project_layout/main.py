"""阶段 06：项目结构化与路由拆分。"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from routers.items import router as items_router
from services.item_service import ItemNotFoundError

app = FastAPI(
    title="FastAPI 学习实验室 - 阶段 06",
    version="0.1.0",
    description="演示 routers、schemas、services 分层，以及轻量统一异常响应。",
)


@app.exception_handler(ItemNotFoundError)
def handle_item_not_found(_: Request, exc: ItemNotFoundError) -> JSONResponse:
    """把业务异常转换为统一的 API 错误格式。"""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"code": 404, "message": str(exc), "data": None},
    )


@app.get("/")
def read_root() -> dict[str, int | str | None]:
    return {"code": 0, "message": "Stage 06 project layout", "data": None}


app.include_router(items_router)
