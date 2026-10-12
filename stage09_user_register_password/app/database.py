"""数据库配置与请求级会话。"""

from collections.abc import Generator
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

STAGE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="LAB_", env_file=STAGE_DIR / ".env", env_file_encoding="utf-8", extra="ignore"
    )
    database_url: str = f"sqlite:///{(STAGE_DIR / 'users.db').as_posix()}"


class Base(DeclarativeBase):
    pass


database_url = Settings().database_url
engine = create_engine(
    database_url,
    connect_args={"check_same_thread": False} if database_url.startswith("sqlite:") else {},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False)


def get_db() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session
