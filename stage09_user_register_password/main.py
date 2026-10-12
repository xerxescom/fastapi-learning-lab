"""阶段 09：用户注册与密码安全。"""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.routers import router

app = FastAPI(title="FastAPI 学习实验室 - 阶段 09", version="0.1.0")
app.include_router(router)


@app.exception_handler(RequestValidationError)
def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    # 默认校验错误可能包含原始 input；注册接口不回显用户提交的数据。
    errors = [
        {"loc": list(error["loc"]), "msg": error["msg"], "type": error["type"]}
        for error in exc.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": errors})
