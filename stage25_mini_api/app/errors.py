import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.schemas import ErrorDetail, ErrorResponse

logger = logging.getLogger(__name__)


class BusinessError(Exception):
    def __init__(self, status_code: int, code: str, message: str):
        self.status_code, self.code, self.message = status_code, code, message


def error_response(status: int, code: str, message: str, *, details=None, headers=None):
    body = ErrorResponse(error=ErrorDetail(code=code, message=message, details=details or []))
    return JSONResponse(status_code=status, content=body.model_dump(), headers=headers)


def register_handlers(application: FastAPI):
    @application.exception_handler(BusinessError)
    async def business_error(request: Request, exc: BusinessError):
        return error_response(exc.status_code, exc.code, exc.message)

    @application.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        message = exc.detail if isinstance(exc.detail, str) and exc.status_code < 500 else "Internal server error"
        return error_response(exc.status_code, f"HTTP_{exc.status_code}", message, headers=exc.headers)

    @application.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        # 不回显 input 或 ctx，避免注册/登录的原始密码进入错误正文。
        details = [{"loc": list(issue["loc"]), "message": issue["msg"], "type": issue["type"]} for issue in exc.errors()]
        return error_response(422, "VALIDATION_ERROR", "Request validation failed", details=details)

    @application.exception_handler(Exception)
    async def server_error(request: Request, exc: Exception):
        logger.error("Unhandled application error", extra={"error_type": type(exc).__name__})
        return error_response(500, "INTERNAL_ERROR", "Internal server error")
