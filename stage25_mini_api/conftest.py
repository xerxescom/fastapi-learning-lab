"""临时数据库与依赖覆盖，应用自身的数据库路径不得被测试访问。"""

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import Settings
from app.database import Base, build_engine, get_db
from app.dependencies import get_settings
from main import create_app


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch):
    for name in os.environ:
        if name.startswith("LAB_"):
            monkeypatch.delenv(name)


@pytest.fixture
def db_engine(tmp_path):
    engine = build_engine(f"sqlite:///{(tmp_path / 'test.db').as_posix()}")
    Base.metadata.create_all(engine)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def configuration(tmp_path):
    return Settings(
        _env_file=None, environment="testing", jwt_secret_key="stage25-test-key-not-for-real-deployment-" * 2,
        database_url=f"sqlite:///{(tmp_path / 'must-not-use.db').as_posix()}",
    )


@pytest.fixture
def application(db_engine, configuration, tmp_path):
    application = create_app(configuration)

    def override_db():
        with Session(db_engine, autoflush=False) as db:
            yield db

    previous = application.dependency_overrides.copy()
    application.dependency_overrides[get_db] = override_db
    application.dependency_overrides[get_settings] = lambda: configuration
    try:
        yield application
    finally:
        application.dependency_overrides.clear()
        application.dependency_overrides.update(previous)
        assert not (tmp_path / "must-not-use.db").exists()


@pytest.fixture
def client(application):
    with TestClient(application, raise_server_exceptions=False) as client:
        yield client


@pytest.fixture
def db_session(db_engine):
    with Session(db_engine) as db:
        yield db


def register(client, username="alice", email="alice@example.com"):
    response = client.post("/auth/register", json={"username": username, "email": email, "password": "correct-password-123"})
    assert response.status_code == 201, response.text
    return response.json()["data"]


def login(client, username="alice"):
    response = client.post("/auth/token", data={"grant_type": "password", "username": username, "password": "correct-password-123"})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def account(client):
    return register(client)


@pytest.fixture
def auth(client, account):
    return login(client)
