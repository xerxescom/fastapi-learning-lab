"""分层夹具：临时库 -> 应用覆盖 -> 客户端；会话和数据工厂按需创建。"""

from contextlib import contextmanager
from itertools import count

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database import Base, build_engine, get_db
from app.models import Task
from app.services import TaskPolicy, get_policy
from main import create_app


@pytest.fixture
def db_engine(tmp_path):
    engine = build_engine(f"sqlite:///{(tmp_path / 'test.db').as_posix()}")
    try:
        Base.metadata.create_all(engine)
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def db_session(db_engine):
    with Session(db_engine) as session:
        yield session


@pytest.fixture
def application(db_engine, tmp_path):
    forbidden_path = tmp_path / "must-not-use.db"
    application = create_app(f"sqlite:///{forbidden_path.as_posix()}")

    def override_db():
        # 每个请求新建 Session，不跨线程/并发请求共享同一个会话对象。
        with Session(db_engine) as session:
            yield session

    previous = application.dependency_overrides.copy()
    application.dependency_overrides[get_db] = override_db
    application.dependency_overrides[get_policy] = lambda: TaskPolicy(max_tasks=3)
    try:
        yield application
    finally:
        application.dependency_overrides.clear()
        application.dependency_overrides.update(previous)
        application.state.engine.dispose()
        assert not forbidden_path.exists(), "A test accessed the application database"


@pytest.fixture
def client(application):
    with TestClient(application) as client:
        yield client


@pytest.fixture
def task_factory(db_session):
    sequence = count(1)

    def create(*, title=None, completed=False):
        task = Task(title=title if title is not None else f"Task {next(sequence)}", completed=completed)
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)
        return task

    return create


@pytest.fixture
def override_dependency(application):
    @contextmanager
    def override(original, replacement):
        missing = object()
        previous = application.dependency_overrides.get(original, missing)
        application.dependency_overrides[original] = replacement
        try:
            yield
        finally:
            if previous is missing:
                application.dependency_overrides.pop(original, None)
            else:
                application.dependency_overrides[original] = previous

    return override
