from collections.abc import Generator

from fastapi import Request
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session


class Base(DeclarativeBase):
    pass


def build_engine(url: str):
    return create_engine(url, connect_args={"check_same_thread": False} if url.startswith("sqlite:") else {})


def get_db(request: Request) -> Generator[Session, None, None]:
    with Session(request.app.state.engine) as session:
        yield session
