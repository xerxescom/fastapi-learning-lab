"""阶段 12：请求响应规范与全局异常处理。"""

from fastapi import FastAPI

from app.handlers import register_exception_handlers
from app.routers import router
from app.services import ItemService


def create_app() -> FastAPI:
    app = FastAPI(title="FastAPI 学习实验室 - 阶段 12", version="0.1.0", debug=False)
    app.state.item_service = ItemService()
    register_exception_handlers(app)
    app.include_router(router)
    return app


app = create_app()
