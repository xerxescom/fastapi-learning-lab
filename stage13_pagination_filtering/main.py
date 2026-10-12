"""阶段 13：分页、排序与过滤。"""

from fastapi import FastAPI

from app.routers import router

app = FastAPI(title="FastAPI 学习实验室 - 阶段 13", version="0.1.0")
app.include_router(router)
