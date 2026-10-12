"""集中处理业务、HTTP、请求校验及未知服务器异常。"""

import logging
from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.exceptions import BusinessError
from app.schemas import ErrorResponse, ValidationDetails, ValidationIssue

logger = logging.getLogger(__name__)


async def handle_business_error(_: Request, exc: BusinessError) -> JSONResponse:
    body = ErrorResponse(code=exc.code, message=exc.message)
    return JSONResponse(status_code=exc.status_code, content=body.model_dump(mode="json"))


async def handle_http_error(_: Request, exc: HTTPException) -> JSONResponse:
    if exc.status_code >= 500:
        message = "Internal server error"
    elif isinstance(exc.detail, str):
        message = exc.detail
    else:
        try:
            message = HTTPStatus(exc.status_code).phrase
        except ValueError:
            message = "HTTP error"
    body = ErrorResponse(code=exc.status_code * 100, message=message)
    # 保留认证挑战、Allow、Retry-After 等 HTTP 语义。
    return JSONResponse(
        status_code=exc.status_code,
        content=body.model_dump(mode="json"),
        headers=exc.headers,
    )


async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    issues = [
        ValidationIssue(loc=list(error["loc"]), message=error["msg"], type=error["type"])
        for error in exc.errors()
    ]
    body = ErrorResponse(
        code=42200, message="Request validation failed", data=ValidationDetails(errors=issues)
    )
    return JSONResponse(status_code=422, content=body.model_dump(mode="json"))


async def handle_server_error(_: Request, exc: Exception) -> JSONResponse:
    # 内部堆栈写入服务端日志，不返回异常消息或请求体。
    logger.error("Unhandled server error", exc_info=(type(exc), exc, exc.__traceback__))
    body = ErrorResponse(code=50000, message="Internal server error")
    return JSONResponse(status_code=500, content=body.model_dump(mode="json"))


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(BusinessError, handle_business_error)
    # 注册 Starlette 基类，同时覆盖 FastAPI 的 HTTPException 和未知路由。
    app.add_exception_handler(HTTPException, handle_http_error)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(Exception, handle_server_error)
