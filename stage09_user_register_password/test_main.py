from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app import services
from app.database import Base, get_db
from app.models import User
from app.schemas import UserCreate
from app.security import hash_password, verify_password
from main import app

PASSWORD = "Learning-pass-123"
USER_BODY = {"username": "alice", "email": "alice@example.com", "password": PASSWORD}


@pytest.fixture
def db_engine(tmp_path: Path) -> Generator[Engine, None, None]:
    engine = create_engine(
        f"sqlite:///{(tmp_path / 'users.db').as_posix()}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def client(db_engine: Engine) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        with Session(db_engine, autoflush=False) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


def test_registration_stores_hash_and_returns_public_fields(
    client: TestClient, db_engine: Engine
) -> None:
    response = client.post("/users", json=USER_BODY)
    assert response.status_code == 201
    assert response.json() == {"id": 1, "username": "alice", "email": "alice@example.com"}
    assert PASSWORD not in response.text
    with Session(db_engine) as session:
        user = session.scalar(select(User))
        assert user.password_hash != PASSWORD
        assert user.password_hash.startswith("$argon2id$")
        assert verify_password(PASSWORD, user.password_hash)
        assert not verify_password("wrong-password", user.password_hash)
        assert user.password_hash not in response.text


def test_normalization(client: TestClient) -> None:
    response = client.post(
        "/users", json={**USER_BODY, "username": "  Alice  ", "email": "ALICE@EXAMPLE.COM"}
    )
    assert response.status_code == 201
    assert response.json()["username"] == "alice"
    assert response.json()["email"] == "alice@example.com"


@pytest.mark.parametrize(
    "duplicate",
    [
        {"username": "alice", "email": "bob@example.com"},
        {"username": "bob", "email": "alice@example.com"},
        {"username": " ALICE ", "email": "bob@example.com"},
        {"username": "bob", "email": "ALICE@EXAMPLE.COM"},
    ],
)
def test_duplicate_user(client: TestClient, db_engine: Engine, duplicate: dict) -> None:
    assert client.post("/users", json=USER_BODY).status_code == 201
    response = client.post("/users", json={**duplicate, "password": PASSWORD})
    assert response.status_code == 409
    assert response.json() == {"detail": "Username or email already registered"}
    with Session(db_engine) as session:
        assert session.scalar(select(func.count()).select_from(User)) == 1


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("username", "ab"),
        ("username", "a" * 31),
        ("username", "invalid-name"),
        ("username", "123alice"),
        ("username", "   "),
        ("email", "invalid-email"),
        ("password", "p@ss!"),
        ("password", "p" * 129),
        ("password", 12345678),
    ],
)
def test_invalid_input_does_not_create_user(
    client: TestClient, db_engine: Engine, field: str, value: object
) -> None:
    response = client.post("/users", json={**USER_BODY, field: value})
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", field]
    assert all("input" not in error and "ctx" not in error for error in response.json()["detail"])
    assert PASSWORD not in response.text
    if field == "password" and isinstance(value, str):
        assert value not in response.text
    with Session(db_engine) as session:
        assert session.scalar(select(func.count()).select_from(User)) == 0


def test_missing_field_does_not_echo_password(client: TestClient) -> None:
    response = client.post("/users", json={"email": "alice@example.com", "password": PASSWORD})
    assert response.status_code == 422
    assert PASSWORD not in response.text
    assert "input" not in response.json()["detail"][0]


def test_malformed_json_does_not_echo_password(client: TestClient) -> None:
    response = client.post(
        "/users", content='{"password":"' + PASSWORD + '",}', headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 422
    assert PASSWORD not in response.text


def test_hashes_use_random_salts_and_preserve_password() -> None:
    password = "  学习-password-123  "
    first = hash_password(password)
    second = hash_password(password)
    assert first != second
    assert verify_password(password, first)
    assert verify_password(password, second)
    assert not verify_password(password.strip(), first)


def test_unique_constraint_handles_stale_precheck(
    db_engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    with Session(db_engine, autoflush=False) as session:
        services.register_user(session, UserCreate(**USER_BODY))
        original_check = services.user_exists
        calls = 0

        def stale_check(db: Session, username: str, email: str) -> bool:
            nonlocal calls
            calls += 1
            return False if calls == 1 else original_check(db, username, email)

        # 模拟并发注册导致预检查结果过期，实际触发数据库唯一约束。
        monkeypatch.setattr(services, "user_exists", stale_check)
        with pytest.raises(services.DuplicateUserError):
            services.register_user(session, UserCreate(**USER_BODY))
        assert calls == 2
        assert session.scalar(select(func.count()).select_from(User)) == 1
        created = services.register_user(
            session,
            UserCreate(username="bob", email="bob@example.com", password=PASSWORD),
        )
        assert created.username == "bob"


def test_password_is_masked_in_model_representation() -> None:
    body = UserCreate(**USER_BODY)
    assert PASSWORD not in repr(body)


@pytest.mark.parametrize("password", ["a1b2c3d4", "p" * 128])
def test_valid_password_length_boundaries(client: TestClient, password: str) -> None:
    response = client.post("/users", json={**USER_BODY, "password": password})
    assert response.status_code == 201
    assert set(response.json()) == {"id", "username", "email"}
