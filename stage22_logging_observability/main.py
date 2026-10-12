"""Stage 22：标准 logging、请求关联和健康探针。"""

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.types import ASGIApp

from app.logging_config import configure_logging
from app.middleware import ObservabilityMiddleware

configure_logging()


def create_app(*, readiness_probe: Callable[[], bool] | None = None) -> ASGIApp:
    api = FastAPI(title="Stage 22：日志与可观测性基础", debug=False)
    # 默认仅模拟健康的本地依赖；没有数据库时不宣称已检查数据库。
    probe = readiness_probe if readiness_probe is not None else lambda: True

    def get_readiness_probe() -> Callable[[], bool]:
        return probe

    @api.get("/health/live", tags=["health"], summary="进程存活检查")
    def live():
        return {"status": "alive"}

    @api.get("/health/ready", tags=["health"], summary="服务就绪检查")
    def ready(check: Annotated[Callable[[], bool], Depends(get_readiness_probe)]):
        try:
            available = check()
        except Exception:
            # 对外仅暴露就绪状态；不返回依赖地址、凭据或异常消息。
            available = False
        if not available:
            return JSONResponse(status_code=503, content={"status": "not_ready"})
        return {"status": "ready"}

    @api.get("/items/{item_id}", tags=["demo"])
    def read_item(item_id: int, request: Request):
        return {"item_id": item_id, "request_id": request.state.request_id}

    @api.get("/errors/http", tags=["demo"])
    def http_error():
        raise HTTPException(status_code=409, detail="Demonstration conflict")

    @api.get("/errors/unhandled", tags=["demo"])
    def unhandled_error():
        raise RuntimeError("private-demo-secret")

    @api.exception_handler(Exception)
    async def server_error(request: Request, exc: Exception):
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

    return ObservabilityMiddleware(api)


app = create_app()
