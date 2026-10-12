from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

STAGE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="LAB_", env_file=STAGE_DIR / ".env", env_file_encoding="utf-8", extra="ignore", frozen=True,
    )

    environment: Literal["development", "testing", "production"] = "development"
    database_url: str = f"sqlite:///{(STAGE_DIR / 'mini_api.db').as_posix()}"
    jwt_secret_key: SecretStr = Field(min_length=32)
    access_token_expire_minutes: int = Field(default=30, ge=1, le=1440)

    @field_validator("database_url")
    @classmethod
    def sqlite_only(cls, value: str) -> str:
        try:
            driver = make_url(value).drivername
        except ArgumentError:
            raise ValueError("Invalid database URL") from None
        if driver != "sqlite":
            raise ValueError("This learning stage uses synchronous SQLite only")
        return value

    @field_validator("jwt_secret_key")
    @classmethod
    def nonblank_key(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value().strip()) < 32:
            raise ValueError("JWT key must contain at least 32 non-padding characters")
        return value
