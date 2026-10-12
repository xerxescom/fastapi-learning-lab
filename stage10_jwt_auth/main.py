"""阶段 10：JWT 登录与鉴权进阶。"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.routers import router


@asynccontextmanager
async def lifespan(_: FastAPI):
    # 启动时检查密钥配置，避免服务接到登录请求才发现配置缺失。
    get_settings()
    yield


app = FastAPI(title="FastAPI 学习实验室 - 阶段 10", version="0.1.0", lifespan=lifespan)
app.include_router(router)


@app.exception_handler(RequestValidationError)
def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    errors = [
        {"loc": list(error["loc"]), "msg": error["msg"], "type": error["type"]}
        for error in exc.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": errors})
