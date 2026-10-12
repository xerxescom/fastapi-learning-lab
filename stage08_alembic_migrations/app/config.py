"""应用与迁移共用数据库配置。"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

STAGE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="LAB_",
        env_file=STAGE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    database_url: str = f"sqlite:///{(STAGE_DIR / 'items.db').as_posix()}"
