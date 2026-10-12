"""数据库引擎、会话工厂与请求级依赖。"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import Settings


class Base(DeclarativeBase):
    pass


database_url = Settings().database_url
engine = create_engine(
    database_url,
    connect_args={"check_same_thread": False} if database_url.startswith("sqlite:") else {},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False)


def get_db() -> Generator[Session, None, None]:
    # 每个请求独立会话；关闭会话也会回滚未提交的事务。
    with SessionLocal() as session:
        yield session
