from collections.abc import Generator

from fastapi import HTTPException, Request
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session
from sqlalchemy.pool import StaticPool


class Base(DeclarativeBase):
    pass


def build_engine(url: str) -> Engine:
    kwargs = {"poolclass": StaticPool} if url in {"sqlite://", "sqlite:///:memory:"} else {}
    engine = create_engine(url, connect_args={"check_same_thread": False}, **kwargs)

    @event.listens_for(engine, "connect")
    def configure_sqlite(connection, record):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()

    return engine


def get_db(request: Request) -> Generator[Session, None, None]:
    engine = getattr(request.app.state, "engine", None)
    if engine is None:
        raise HTTPException(status_code=503, detail="Application not ready")
    # Session 属于一次请求；关闭时也会回滚尚未提交的事务。
    with Session(engine, autoflush=False) as session:
        yield session
