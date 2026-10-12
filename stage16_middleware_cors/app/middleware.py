"""纯 ASGI 中间件：不读取请求体，不缓冲响应体。"""

import logging
from time import perf_counter
from uuid import uuid4

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger("stage16.requests")
logger.setLevel(logging.INFO)


class RequestLogMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        started = perf_counter()
        request_id = uuid4().hex
        status = 500
        failed = False
        # 每次请求各自持有状态，不能把 trace 存在共享中间件实例上。
        state = scope.setdefault("state", {})
        state["request_id"] = request_id
        state["middleware_trace"] = []

        async def send_with_headers(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                headers = MutableHeaders(scope=message)
                headers["X-Request-ID"] = request_id
                headers["X-Process-Time-Ms"] = f"{(perf_counter() - started) * 1000:.3f}"
            await send(message)

        try:
            await self.app(scope, receive, send_with_headers)
        except Exception:
            failed = True
            # 已发送的响应不能再替换；保持异常向服务器传播，不重复发送 500。
            raise
        finally:
            duration = (perf_counter() - started) * 1000
            # 只记路由模板，不记录查询串、请求体、Cookie 或 Authorization。
            route = getattr(scope.get("route"), "path", "<unmatched>")
            logger.log(
                logging.ERROR if failed or status >= 500 else logging.INFO,
                "request method=%s route=%s status=%s duration_ms=%.3f request_id=%s",
                scope["method"], route, status, duration, request_id,
                extra={"request_id": request_id, "method": scope["method"], "route": route,
                       "status_code": status, "duration_ms": duration, "failed": failed},
            )


class OrderMiddleware:
    def __init__(self, app: ASGIApp, name: str):
        self.app = app
        self.name = name

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        trace = scope["state"]["middleware_trace"]
        trace.append(f"{self.name}:before")

        async def send_with_order(message: Message) -> None:
            if message["type"] == "http.response.start":
                trace.append(f"{self.name}:after")
                MutableHeaders(scope=message)["X-Middleware-Order"] = ",".join(trace)
            await send(message)

        await self.app(scope, receive, send_with_order)
