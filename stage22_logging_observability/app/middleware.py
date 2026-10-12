"""外层 ASGI 日志包装：包括 FastAPI 生成的 500 响应。"""

import logging
from time import perf_counter
from uuid import uuid4

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger("stage22")


class ObservabilityMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        started = perf_counter()
        request_id = uuid4().hex
        scope.setdefault("state", {})["request_id"] = request_id
        status = 500
        failed = False

        def context():
            return {
                "request_id": request_id,
                "method": scope["method"],
                "route": getattr(scope.get("route"), "path", "<unmatched>"),
                "status_code": status,
            }

        async def send_with_id(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                MutableHeaders(scope=message)["X-Request-ID"] = request_id
            await send(message)

        try:
            await self.app(scope, receive, send_with_id)
        except Exception as exc:
            failed = True
            logger.error("request.exception", extra={**context(), "error_type": type(exc).__name__})
            # 响应可能已经发送；不能重复发送 500，也不吞掉服务器需要处理的异常。
            raise
        finally:
            logger.log(
                logging.ERROR if failed or status >= 500 else logging.WARNING if status >= 400 else logging.INFO,
                "request.completed",
                extra={**context(), "duration_ms": round((perf_counter() - started) * 1000, 3), "failed": failed},
            )
