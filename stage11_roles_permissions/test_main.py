from collections.abc import Generator
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import Base, get_db
from app.models import User
from app.permissions import Role
from app.security import ALGORITHM, create_access_token, verify_password
from main import app

SECRET = "test-only-key-" + "x" * 40
PASSWORD = "Learning-pass-123"
USER_BODY = {"username": "alice", "email": "alice@example.com", "password": PASSWORD}


@pytest.fixture(autouse=True)
def isolate_configuration(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    monkeypatch.setenv("LAB_JWT_SECRET_KEY", SECRET)
    monkeypatch.delenv("LAB_ACCESS_TOKEN_EXPIRE_MINUTES", raising=False)
    monkeypatch.setitem(Settings.model_config, "env_file", None)
    get_settings.cache_clear()
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()
    get_settings.cache_clear()


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
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def registered_user(client: TestClient) -> dict:
    response = client.post("/users", json=USER_BODY)
    assert response.status_code == 201
    return response.json()


def login(client: TestClient, **overrides) -> object:
    return client.post("/token", data={"username": "alice", "password": PASSWORD, **overrides})


def sign_claims(**changes) -> str:
    now = datetime.now(timezone.utc)
    claims = {
        "sub": "1", "iat": now, "exp": now + timedelta(minutes=30), "token_type": "access"
    }
    claims.update(changes)
    return jwt.encode(claims, SECRET, algorithm=ALGORITHM)


def assert_unauthorized(response) -> None:
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json() == {"detail": "Could not validate credentials"}


def test_register_login_and_protected_routes(client: TestClient, registered_user: dict, db_engine: Engine) -> None:
    response = login(client)
    assert response.status_code == 200
    result = response.json()
    assert set(result) == {"access_token", "token_type"}
    assert result["token_type"] == "bearer"
    claims = jwt.decode(result["access_token"], SECRET, algorithms=[ALGORITHM])
    assert claims["sub"] == str(registered_user["id"])
    assert claims["token_type"] == "access"
    assert claims["exp"] - claims["iat"] == 30 * 60
    assert set(claims) == {"sub", "iat", "exp", "token_type"}
    headers = {"Authorization": f"Bearer {result['access_token']}"}
    current = client.get("/users/me", headers=headers)
    assert current.status_code == 200
    assert current.json() == registered_user
    assert client.get("/items", headers=headers).json()["owner"] == "alice"
    with Session(db_engine) as session:
        user = session.get(User, registered_user["id"])
        assert verify_password(PASSWORD, user.password_hash)
        assert user.password_hash not in current.text
        assert user.password_hash not in response.text
    assert PASSWORD not in current.text and PASSWORD not in response.text


@pytest.mark.parametrize(
    "credentials",
    [{"password": "wrong-password"}, {"username": "unknown"}, {"username": "unknown", "password": "wrong"}],
)
def test_login_failure(client: TestClient, registered_user: dict, credentials: dict) -> None:
    response = login(client, **credentials)
    assert_unauthorized(response)
    assert "access_token" not in response.json()
    assert PASSWORD not in response.text


def test_login_normalizes_username(client: TestClient, registered_user: dict) -> None:
    assert login(client, username=" ALICE ").status_code == 200


@pytest.mark.parametrize("path", ["/users/me", "/items"])
@pytest.mark.parametrize("authorization", [None, "Basic abc", "Bearer", "Bearer not-a-jwt"])
def test_invalid_authorization(client: TestClient, path: str, authorization: str | None) -> None:
    headers = {"Authorization": authorization} if authorization is not None else {}
    assert_unauthorized(client.get(path, headers=headers))


@pytest.mark.parametrize(
    "changes",
    [
        {"exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
        {"iat": datetime.now(timezone.utc) + timedelta(hours=1)},
        {"token_type": "refresh"},
        {"sub": "missing-user"},
        {"sub": "999"},
        {"sub": "0"},
        {"sub": "9999999999999999999"},
        {"sub": 1},
        {"exp": "not-a-date"},
        {"exp": []},
    ],
)
def test_invalid_claims(client: TestClient, registered_user: dict, changes: dict) -> None:
    assert_unauthorized(client.get("/users/me", headers={"Authorization": f"Bearer {sign_claims(**changes)}"}))


@pytest.mark.parametrize("missing_claim", ["sub", "iat", "exp", "token_type"])
def test_required_claims(client: TestClient, registered_user: dict, missing_claim: str) -> None:
    claims = jwt.decode(sign_claims(), SECRET, algorithms=[ALGORITHM])
    claims.pop(missing_claim)
    token = jwt.encode(claims, SECRET, algorithm=ALGORITHM)
    assert_unauthorized(client.get("/users/me", headers={"Authorization": f"Bearer {token}"}))


@pytest.mark.parametrize("algorithm", ["HS256", "HS384"])
def test_wrong_signature_or_algorithm(client: TestClient, registered_user: dict, algorithm: str) -> None:
    claims = jwt.decode(sign_claims(), SECRET, algorithms=[ALGORITHM])
    key = "wrong-key-" + "z" * 60 if algorithm == "HS256" else SECRET
    token = jwt.encode(claims, key, algorithm=algorithm)
    assert_unauthorized(client.get("/users/me", headers={"Authorization": f"Bearer {token}"}))


def test_disabled_user_returns_403(client: TestClient, registered_user: dict, db_engine: Engine) -> None:
    token = login(client).json()["access_token"]
    with Session(db_engine) as session:
        user = session.get(User, registered_user["id"])
        user.is_active = False
        session.commit()
    for path in ("/users/me", "/items"):
        response = client.get(path, headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 403
        assert response.json() == {"detail": "Inactive user"}
    assert login(client).status_code == 403
    assert_unauthorized(login(client, password="wrong-password"))


def test_deleted_user_token_is_rejected(client: TestClient, registered_user: dict, db_engine: Engine) -> None:
    token = login(client).json()["access_token"]
    with Session(db_engine) as session:
        session.delete(session.get(User, registered_user["id"]))
        session.commit()
    created = client.post(
        "/users", json={"username": "bob", "email": "bob@example.com", "password": PASSWORD}
    )
    assert created.status_code == 201
    assert created.json()["id"] != registered_user["id"]
    assert_unauthorized(client.get("/users/me", headers={"Authorization": f"Bearer {token}"}))


def test_duplicate_registration_and_validation_redaction(client: TestClient, registered_user: dict) -> None:
    assert client.post("/users", json=USER_BODY).status_code == 409
    response = client.post("/users", json={"password": PASSWORD})
    assert response.status_code == 422
    assert PASSWORD not in response.text
    assert all("input" not in error for error in response.json()["detail"])
    response = client.post("/token", data={"password": PASSWORD})
    assert response.status_code == 422
    assert PASSWORD not in response.text


def test_lifetime_configuration() -> None:
    settings = Settings(access_token_expire_minutes=5)
    claims = jwt.decode(create_access_token(1, settings), SECRET, algorithms=[ALGORITHM])
    assert claims["exp"] - claims["iat"] == 300


def test_missing_or_short_key_fails_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LAB_JWT_SECRET_KEY")
    with pytest.raises(ValidationError):
        Settings()
    with pytest.raises(ValidationError):
        Settings(jwt_secret_key="short")


def test_openapi_oauth2_flow(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    flow = schema["components"]["securitySchemes"]["OAuth2PasswordBearer"]["flows"]["password"]
    assert flow["tokenUrl"] == "token"
    assert schema["paths"]["/users/me"]["get"]["security"] == [{"OAuth2PasswordBearer": []}]


@pytest.mark.parametrize("role", [Role.USER, Role.ADMIN])
@pytest.mark.parametrize("path", ["/users/me", "/items", "/admin/users", "/admin/stats"])
def test_role_permission_matrix(
    client: TestClient, registered_user: dict, db_engine: Engine, role: Role, path: str
) -> None:
    with Session(db_engine) as session:
        session.get(User, registered_user["id"]).role = role
        session.commit()
    token = login(client).json()["access_token"]
    response = client.get(path, headers={"Authorization": f"Bearer {token}"})
    expected = 403 if role == Role.USER and path.startswith("/admin/") else 200
    assert response.status_code == expected
    if expected == 403:
        assert response.json() == {"detail": "Not enough permissions"}


@pytest.mark.parametrize("path", ["/admin/users", "/admin/stats"])
def test_admin_routes_require_authentication(client: TestClient, path: str) -> None:
    assert_unauthorized(client.get(path))
    assert_unauthorized(client.get(path, headers={"Authorization": "Bearer invalid"}))


@pytest.mark.parametrize("extra", [{"role": "admin"}, {"is_active": False}])
def test_registration_rejects_privileged_fields(client: TestClient, db_engine: Engine, extra: dict) -> None:
    response = client.post("/users", json={**USER_BODY, **extra})
    assert response.status_code == 422
    assert PASSWORD not in response.text
    with Session(db_engine) as session:
        assert session.scalar(select(func.count()).select_from(User)) == 0


def test_registration_defaults_to_user(client: TestClient, registered_user: dict, db_engine: Engine) -> None:
    assert registered_user["role"] == "user"
    with Session(db_engine) as session:
        user = session.get(User, registered_user["id"])
        assert user.role == Role.USER
        assert user.is_active


def test_role_changes_apply_to_existing_token(client: TestClient, registered_user: dict, db_engine: Engine) -> None:
    token = login(client).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert client.get("/admin/users", headers=headers).status_code == 403
    for role, expected in [(Role.ADMIN, 200), (Role.USER, 403)]:
        with Session(db_engine) as session:
            session.get(User, registered_user["id"]).role = role
            session.commit()
        assert client.get("/admin/users", headers=headers).status_code == expected
        assert client.get("/admin/stats", headers=headers).status_code == expected
        assert client.get("/users/me", headers=headers).json()["role"] == role.value


def test_client_claims_and_scopes_cannot_grant_permissions(client: TestClient, registered_user: dict) -> None:
    response = login(client, scope="users:read")
    assert response.status_code == 200
    for token in (response.json()["access_token"], sign_claims(role="admin", scope="users:read")):
        response = client.get("/admin/users", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 403


def test_admin_responses_and_disabled_account(
    client: TestClient, registered_user: dict, db_engine: Engine
) -> None:
    other = client.post(
        "/users", json={"username": "bob", "email": "bob@example.com", "password": PASSWORD}
    ).json()
    with Session(db_engine) as session:
        session.get(User, registered_user["id"]).role = Role.ADMIN
        session.get(User, other["id"]).is_active = False
        session.commit()
    token = login(client).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/admin/users", headers=headers)
    assert response.status_code == 200
    assert [user["username"] for user in response.json()] == ["alice", "bob"]
    assert all(set(user) == {"id", "username", "email", "role", "is_active"} for user in response.json())
    assert PASSWORD not in response.text
    with Session(db_engine) as session:
        for user in session.scalars(select(User)):
            assert user.password_hash not in response.text
    assert client.get("/admin/stats", headers=headers).json() == {"total_users": 2, "active_users": 1}
    with Session(db_engine) as session:
        session.get(User, registered_user["id"]).is_active = False
        session.commit()
    for path in ("/admin/users", "/admin/stats"):
        denied = client.get(path, headers=headers)
        assert denied.status_code == 403
        assert denied.json() == {"detail": "Inactive user"}


def test_admin_expired_token_returns_401(client: TestClient, registered_user: dict, db_engine: Engine) -> None:
    with Session(db_engine) as session:
        session.get(User, registered_user["id"]).role = Role.ADMIN
        session.commit()
    token = sign_claims(exp=datetime.now(timezone.utc) - timedelta(minutes=1))
    assert_unauthorized(client.get("/admin/users", headers={"Authorization": f"Bearer {token}"}))


def test_role_constraint_rejects_unknown_roles(db_engine: Engine, registered_user: dict) -> None:
    with Session(db_engine) as session:
        with pytest.raises(IntegrityError):
            session.execute(text("UPDATE users SET role = 'superuser'"))
            session.commit()
        session.rollback()
        assert session.get(User, registered_user["id"]).role == Role.USER


def test_local_admin_command(client: TestClient, registered_user: dict, db_engine: Engine, monkeypatch: pytest.MonkeyPatch) -> None:
    import promote_user

    token = login(client).json()["access_token"]
    monkeypatch.setattr(promote_user, "SessionLocal", lambda: Session(db_engine))
    assert promote_user.main([" ALICE "]) == 0
    assert promote_user.main(["alice"]) == 0
    assert promote_user.main(["missing"]) == 1
    with Session(db_engine) as session:
        assert session.scalar(select(func.count()).select_from(User)) == 1
        assert session.get(User, registered_user["id"]).role == Role.ADMIN
    assert client.get("/admin/users", headers={"Authorization": f"Bearer {token}"}).status_code == 200
