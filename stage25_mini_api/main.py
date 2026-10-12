"""Stage 25 综合项目入口；导入不连接数据库，启动时校验配置。"""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from typing import Annotated

from app.config import Settings
from app.database import build_engine, get_db
from app.errors import error_response, register_handlers
from app.models import Task, User
from app.routers import router
from app.schemas import ErrorResponse


def create_app(settings: Settings | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(application: FastAPI):
        configuration = settings if settings is not None else Settings()
        engine = build_engine(configuration.database_url)
        application.state.settings = configuration
        application.state.engine = engine
        try:
            yield
        finally:
            del application.state.engine
            del application.state.settings
            engine.dispose()

    errors = {status: {"model": ErrorResponse} for status in (401, 403, 404, 409, 422, 500, 503)}
    application = FastAPI(
        title="Mini Task API", version="1.0.0", debug=False, lifespan=lifespan,
        description="Stage 25 综合示例：注册、JWT 鉴权与用户隔离的任务管理。", responses=errors,
        openapi_tags=[{"name": name} for name in ("auth", "users", "tasks", "admin", "health")],
    )
    register_handlers(application)
    application.include_router(router)

    @application.get("/health/live", tags=["health"])
    def live():
        return {"status": "alive"}

    @application.get("/health/ready", tags=["health"])
    def ready(db: Annotated[Session, Depends(get_db)]):
        try:
            # 不只检查连接，还确认两个业务表已由 init_db.py 创建。
            db.execute(select(User.id).limit(1))
            db.execute(select(Task.id).limit(1))
        except SQLAlchemyError:
            db.rollback()
            return error_response(503, "DATABASE_NOT_READY", "Database schema unavailable")
        return {"status": "ready"}

    return application


app = create_app()
