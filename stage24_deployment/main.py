"""Stage 24：环境配置驱动的最小部署入口。"""

from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, Request
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.config import Settings


class AppInfo(BaseModel):
    app_name: str
    environment: Literal["development", "testing", "production"]
    release_version: str


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings if settings is not None else Settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        application.state.ready = True
        try:
            yield
        finally:
            application.state.ready = False

    application = FastAPI(
        title=settings.app_name, version=settings.release_version, debug=settings.debug,
        lifespan=lifespan,
        docs_url="/docs" if settings.docs_enabled else None,
        redoc_url="/redoc" if settings.docs_enabled else None,
        openapi_url="/openapi.json" if settings.docs_enabled else None,
    )
    application.state.ready = False
    application.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts, www_redirect=False)

    @application.get("/health/live", tags=["health"])
    def live():
        return {"status": "alive"}

    @application.get("/health/ready", tags=["health"], responses={503: {"description": "应用尚未就绪"}})
    def ready(request: Request):
        if not request.app.state.ready:
            return JSONResponse(status_code=503, content={"status": "not_ready"})
        return {"status": "ready"}

    @application.get("/info", response_model=AppInfo, tags=["application"])
    def info():
        # 明确列出公开字段，避免今后新增密钥配置时被意外返回。
        return AppInfo(app_name=settings.app_name, environment=settings.environment, release_version=settings.release_version)

    return application


app = create_app()
