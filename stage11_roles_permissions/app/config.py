"""JWT 配置：密钥必须显式提供，不使用内置生产密钥。"""

from functools import lru_cache

from pydantic import Field, SecretStr

from app.database import Settings as DatabaseSettings


class Settings(DatabaseSettings):
    jwt_secret_key: SecretStr = Field(min_length=32)
    access_token_expire_minutes: int = Field(default=30, ge=1, le=1440)


@lru_cache
def get_settings() -> Settings:
    return Settings()
