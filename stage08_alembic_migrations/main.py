"""阶段 08：应用入口，表结构由 Alembic 管理。"""

from fastapi import FastAPI

from app.routers import router

app = FastAPI(title="FastAPI 学习实验室 - 阶段 08", version="0.1.0")
app.include_router(router)
