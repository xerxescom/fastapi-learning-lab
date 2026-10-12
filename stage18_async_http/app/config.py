from pathlib import Path

from pydantic import AnyHttpUrl, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="LAB_", env_file=Path(__file__).resolve().parents[1] / ".env",
        env_file_encoding="utf-8", extra="ignore",
    )

    upstream_base_url: AnyHttpUrl = AnyHttpUrl("http://127.0.0.1:9001/")
    http_timeout_seconds: float = Field(default=1, gt=0, le=30, allow_inf_nan=False)
    request_deadline_seconds: float = Field(default=2, gt=0, le=60, allow_inf_nan=False)

    @field_validator("upstream_base_url")
    @classmethod
    def validate_base_url(cls, value: AnyHttpUrl) -> AnyHttpUrl:
        if value.username or value.password or value.query or value.fragment:
            raise ValueError("Upstream URL must not contain credentials, query or fragment")
        return value
