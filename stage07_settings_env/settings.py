"""集中定义配置及读取方式。"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="LAB_",
        env_file=Path(__file__).with_name(".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = Field(default="FastAPI Learning Lab", min_length=1)
    environment: Literal["development", "testing", "production"] = "development"
    debug: bool = False
    items_per_page: int = Field(default=10, ge=1, le=100)


@lru_cache
def get_settings() -> Settings:
    # 避免每个请求重复读取文件；修改配置后需重启进程。
    return Settings()
