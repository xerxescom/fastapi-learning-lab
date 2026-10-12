"""阶段 07：配置管理与环境变量。"""

from typing import Annotated

from fastapi import Depends, FastAPI
from pydantic import BaseModel

from settings import Settings, get_settings

app = FastAPI(title="FastAPI 学习实验室 - 阶段 07", version="0.1.0")


class AppInfo(BaseModel):
    app_name: str
    environment: str
    debug: bool
    items_per_page: int


@app.get("/info", response_model=AppInfo)
def read_info(settings: Annotated[Settings, Depends(get_settings)]) -> AppInfo:
    # 显式选择可公开字段，不直接返回整个配置对象。
    return AppInfo(
        app_name=settings.app_name,
        environment=settings.environment,
        debug=settings.debug,
        items_per_page=settings.items_per_page,
    )
