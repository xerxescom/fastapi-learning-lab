"""应用配置与服务器参数分开管理，不自动读取工作目录里的 .env。"""

import re
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LAB_", extra="ignore", frozen=True)

    app_name: str = Field(default="FastAPI Deployment Lab", min_length=1, max_length=80)
    environment: Literal["development", "testing", "production"] = "development"
    release_version: str = Field(default="1.0.0", pattern=r"^[A-Za-z0-9][A-Za-z0-9._+\-]{0,49}$")
    debug: bool = False
    docs_enabled: bool = False
    allowed_hosts: list[str] = Field(default_factory=lambda: ["127.0.0.1", "localhost"], min_length=1)

    @field_validator("allowed_hosts")
    @classmethod
    def validate_hosts(cls, hosts: list[str]) -> list[str]:
        for host in hosts:
            if host == "*":
                continue
            domain = host[2:] if host.startswith("*.") else host
            labels = domain.split(".")
            if len(domain) > 253 or not all(re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?", label) for label in labels):
                raise ValueError("Hosts must be DNS names or IPv4 addresses without scheme, port or path")
        return hosts

    @model_validator(mode="after")
    def validate_production(self):
        if self.environment == "production":
            if self.debug:
                raise ValueError("Production must disable debug")
            if "*" in self.allowed_hosts:
                raise ValueError("Production must use explicit allowed hosts")
        return self
