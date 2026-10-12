"""Stage 16：用显式 ASGI 包装展示中间件顺序和全局 CORS。"""

import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.types import ASGIApp

from app.middleware import OrderMiddleware, RequestLogMiddleware

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")

DEFAULT_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]
EXPOSE_HEADERS = ["X-Request-ID", "X-Process-Time-Ms", "X-Middleware-Order"]


class Item(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    quantity: int = Field(ge=1, le=100)


def create_app(*, allow_origins: list[str] | None = None) -> ASGIApp:
    origins = DEFAULT_ORIGINS if allow_origins is None else allow_origins
    if "*" in origins:
        raise ValueError("Use explicit origins when allowing credentials")
    api = FastAPI(title="Stage 16：中间件与 CORS", debug=False)

    @api.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @api.get("/items/{item_id}")
    def read_item(item_id: int) -> dict[str, int]:
        return {"item_id": item_id}

    @api.post("/items", response_model=Item)
    def create_item(item: Item) -> Item:
        return item

    @api.get("/middleware-order")
    def order(request: Request) -> dict[str, list[str]]:
        request.state.middleware_trace.append("handler")
        # 响应开始前只能看到进入阶段；完整顺序稍后写入响应头。
        return {"trace": list(request.state.middleware_trace)}

    @api.get("/errors/http")
    def http_error() -> None:
        raise HTTPException(409, "Demonstration conflict")

    @api.get("/errors/unhandled")
    def unhandled_error() -> None:
        raise RuntimeError("internal demo error: do not return this text")

    @api.exception_handler(Exception)
    async def server_error(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

    # 包装由里向外构造；CORS 在 FastAPI 的错误响应层之外，500 也有跨域头。
    inner = OrderMiddleware(api, name="inner")
    outer = OrderMiddleware(inner, name="outer")
    cors = CORSMiddleware(
        outer,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-CSRF-Token"],
        expose_headers=EXPOSE_HEADERS,
        max_age=600,
    )
    # 日志在 CORS 外面，预检不进入路由，但仍会被统计和记录。
    return RequestLogMiddleware(cors)


app = create_app()
