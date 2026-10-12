import asyncio
import json
import time

import httpx
import jwt
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import event, select
from sqlalchemy.exc import IntegrityError

from app.config import Settings
from app.database import get_db
from app.models import Task, User
from app.schemas import ErrorResponse, UserCreate
from app.security import ALGORITHM, AUDIENCE, ISSUER, verify_password
from app.services import register_user
from app.errors import BusinessError
from conftest import login, register
from main import create_app


def test_complete_user_task_workflow(client, account, auth):
    assert client.get("/users/me", headers=auth).json()["data"] == account
    created = client.post("/tasks", headers=auth, json={"title": "  Learn FastAPI  ", "priority": 2})
    assert created.status_code == 201
    task = created.json()["data"]
    assert task["title"] == "Learn FastAPI" and task["owner_id"] == account["id"]
    path = created.headers["location"]
    assert client.get(path, headers=auth).json()["data"] == task
    updated = client.patch(path, headers=auth, json={"completed": True, "description": "Finished"})
    assert updated.status_code == 200
    assert updated.json()["data"]["completed"] is True
    assert updated.json()["data"]["title"] == "Learn FastAPI"
    listing = client.get("/tasks?completed=true&page_size=1", headers=auth).json()["data"]
    assert listing["total"] == 1 and listing["items"][0]["id"] == task["id"]
    deleted = client.delete(path, headers=auth)
    assert deleted.status_code == 204 and deleted.content == b""
    assert client.get(path, headers=auth).status_code == 404
    assert client.get("/tasks", headers=auth).json()["data"]["total"] == 0


def test_password_hash_and_response_whitelist(client, account, db_session):
    user = db_session.get(User, account["id"])
    assert user.password_hash.startswith("$argon2")
    assert verify_password("correct-password-123", user.password_hash)
    assert not verify_password("incorrect-password", user.password_hash)
    assert set(account) == {"id", "username", "email", "role", "is_active"}
    assert account["role"] == "user" and account["is_active"] is True


def test_normalization_and_duplicates(client):
    response = client.post("/auth/register", json={"username": " Alice ", "email": "ALICE@example.com", "password": "correct-password-123"})
    assert response.status_code == 201
    assert response.json()["data"]["username"] == "alice"
    for username, email in [("ALICE", "other@example.com"), ("other", "alice@EXAMPLE.COM")]:
        conflict = client.post("/auth/register", json={"username": username, "email": email, "password": "correct-password-123"})
        assert conflict.status_code == 409
        assert conflict.json()["error"]["code"] == "USER_EXISTS"
        assert "correct-password" not in conflict.text
    assert login(client, "ALICE")


@pytest.mark.parametrize("change", [
    {"username": "a"}, {"email": "invalid"}, {"password": "short"}, {"password": "x" * 129},
    {"role": "admin"}, {"is_active": False}, {"password_hash": "injected"},
])
def test_invalid_registration_does_not_echo_input(client, change):
    body = {"username": "alice", "email": "alice@example.com", "password": "correct-password-123", **change}
    response = client.post("/auth/register", json=body)
    assert response.status_code == 422
    assert json.dumps(body["password"]) not in response.text
    assert all("input" not in issue and "ctx" not in issue for issue in response.json()["error"]["details"])


@pytest.mark.parametrize("username,password", [("alice", "wrong-password"), ("unknown", "correct-password-123"), ("alice", "x" * 129)])
def test_login_failure(client, account, username, password):
    response = client.post("/auth/token", data={"grant_type": "password", "username": username, "password": password})
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json()["error"]["message"] == "Could not validate credentials"
    assert password not in response.text


def test_login_requires_form_and_grant_type(client, account):
    for kwargs in [
        {"json": {"username": "alice", "password": "correct-password-123"}},
        {"data": {"username": "alice", "password": "correct-password-123"}},
        {"data": {"grant_type": "client_credentials", "username": "alice", "password": "correct-password-123"}},
    ]:
        response = client.post("/auth/token", **kwargs)
        assert response.status_code == 422
        assert "correct-password-123" not in response.text


@pytest.mark.parametrize("method,path,body", [
    ("GET", "/users/me", None), ("GET", "/tasks", None), ("GET", "/tasks/1", None),
    ("POST", "/tasks", {"title": "Task"}), ("PATCH", "/tasks/1", {"completed": True}),
    ("DELETE", "/tasks/1", None), ("GET", "/admin/users", None),
])
def test_protected_routes_require_auth(client, method, path, body):
    response = client.request(method, path, json=body)
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_token_claims(client, auth, configuration, account):
    token = auth["Authorization"].split()[1]
    claims = jwt.decode(token, configuration.jwt_secret_key.get_secret_value(), algorithms=[ALGORITHM], issuer=ISSUER, audience=AUDIENCE)
    assert claims["sub"] == str(account["id"]) and claims["token_type"] == "access"
    assert claims["exp"] - claims["iat"] == configuration.access_token_expire_minutes * 60
    assert "role" not in claims and "password" not in claims


@pytest.mark.parametrize("changes", [
    {"exp": 1}, {"iat": 4102444800, "exp": 4102444900}, {"iss": "wrong"}, {"aud": "wrong"},
    {"token_type": "refresh"}, {"sub": "0"}, {"sub": "01"}, {"sub": "-1"},
    {"sub": "abc"}, {"sub": str(2**63)}, {"sub": 1}, {"exp": True}, {"iat": 1.5},
])
def test_invalid_token_claims(client, account, configuration, changes):
    now = int(time.time())
    claims = {"sub": str(account["id"]), "iat": now, "exp": now + 1800, "iss": ISSUER, "aud": AUDIENCE, "token_type": "access", **changes}
    token = jwt.encode(claims, configuration.jwt_secret_key.get_secret_value(), algorithm=ALGORITHM)
    response = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_tampered_and_wrong_algorithm_tokens(client, auth, configuration, account):
    now = int(time.time())
    claims = {"sub": str(account["id"]), "iat": now, "exp": now + 1800, "iss": ISSUER, "aud": AUDIENCE, "token_type": "access"}
    tokens = [
        "not-a-token", jwt.encode(claims, "different-signing-key-that-is-long-enough", algorithm=ALGORITHM),
        jwt.encode(claims, configuration.jwt_secret_key.get_secret_value(), algorithm="HS384"),
        jwt.encode({key: value for key, value in claims.items() if key != "exp"}, configuration.jwt_secret_key.get_secret_value(), algorithm=ALGORITHM),
    ]
    for token in tokens:
        assert client.get("/users/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_disabled_user_token_and_login(client, account, auth, db_session):
    user = db_session.get(User, account["id"])
    user.is_active = False
    db_session.commit()
    assert client.get("/users/me", headers=auth).status_code == 403
    response = client.post("/auth/token", data={"grant_type": "password", "username": "alice", "password": "correct-password-123"})
    assert response.status_code == 403


def test_deleted_user_token_not_reassigned(client, account, auth, db_session):
    db_session.delete(db_session.get(User, account["id"]))
    db_session.commit()
    new = register(client, "bob", "bob@example.com")
    assert new["id"] > account["id"]
    assert client.get("/users/me", headers=auth).status_code == 401


@pytest.mark.parametrize("method,body", [("GET", None), ("PATCH", {"title": "Stolen"}), ("DELETE", None)])
def test_task_ownership_hides_other_users_tasks(client, auth, method, body):
    task = client.post("/tasks", headers=auth, json={"title": "Private task"}).json()["data"]
    register(client, "bob", "bob@example.com")
    bob = login(client, "bob")
    response = client.request(method, f"/tasks/{task['id']}", headers=bob, json=body)
    assert response.status_code == 404 and response.json()["error"]["code"] == "TASK_NOT_FOUND"
    assert client.get("/tasks", headers=bob).json()["data"]["total"] == 0
    assert client.get(f"/tasks/{task['id']}", headers=auth).json()["data"]["title"] == "Private task"


def test_role_changes_take_effect_with_existing_token(client, account, auth, db_session):
    assert client.get("/admin/users", headers=auth).status_code == 403
    user = db_session.get(User, account["id"])
    user.role = "admin"
    db_session.commit()
    response = client.get("/admin/users?page_size=1", headers=auth)
    assert response.status_code == 200 and response.json()["data"]["total"] == 1
    assert "password_hash" not in response.text
    user.role = "user"
    db_session.commit()
    assert client.get("/admin/users", headers=auth).status_code == 403


@pytest.mark.parametrize("body", [
    {}, {"title": " "}, {"title": "x" * 121}, {"title": "Task", "description": "x" * 2001},
    {"title": "Task", "priority": 0}, {"title": "Task", "priority": 6}, {"title": "Task", "priority": True},
    {"title": "Task", "priority": 1.5}, {"title": "Task", "completed": "true"},
    {"title": "Task", "owner_id": 999},
])
def test_invalid_task_create(client, auth, body):
    assert client.post("/tasks", headers=auth, json=body).status_code == 422
    assert client.get("/tasks", headers=auth).json()["data"]["total"] == 0


@pytest.mark.parametrize("body", [{}, {"title": None}, {"description": None}, {"completed": None}, {"priority": None}, {"title": " "}, {"owner_id": 2}, {"priority": 6}])
def test_invalid_patch_leaves_task_unchanged(client, auth, body):
    response = client.post("/tasks", headers=auth, json={"title": "Original"})
    path = response.headers["location"]
    assert client.patch(path, headers=auth, json=body).status_code == 422
    assert client.get(path, headers=auth).json() == response.json()


def test_partial_patch_supports_false_and_empty_description(client, auth):
    response = client.post("/tasks", headers=auth, json={"title": "Task", "completed": True, "description": "text"})
    updated = client.patch(response.headers["location"], headers=auth, json={"completed": False, "description": ""})
    assert updated.status_code == 200
    assert updated.json()["data"]["completed"] is False and updated.json()["data"]["description"] == ""


def test_filter_sort_pagination_and_literal_wildcards(client, auth):
    for title in ["Beta", "A%", "Alpha", "A_", "Beta"]:
        assert client.post("/tasks", headers=auth, json={"title": title, "priority": 2}).status_code == 201
    first = client.get("/tasks?sort=priority&page_size=2", headers=auth).json()["data"]
    second = client.get("/tasks?sort=priority&page_size=2&page=2", headers=auth).json()["data"]
    assert first["total"] == second["total"] == 5
    assert [task["id"] for task in first["items"]] == [1, 2]
    assert [task["id"] for task in second["items"]] == [3, 4]
    assert client.get("/tasks?page=10", headers=auth).json()["data"]["items"] == []
    titles = client.get("/tasks?sort=title&order=desc", headers=auth).json()["data"]["items"]
    assert [task["title"] for task in titles][:2] == ["Beta", "Beta"]
    assert titles[0]["id"] < titles[1]["id"]
    for q, expected in [("%", "A%"), ("_", "A_")]:
        page = client.get("/tasks", params={"q": q}, headers=auth).json()["data"]
        assert page["total"] == 1 and page["items"][0]["title"] == expected
    assert client.get("/tasks?completed=true", headers=auth).json()["data"]["total"] == 0
    assert client.get("/tasks", params={"q": "' OR 1=1 --"}, headers=auth).json()["data"]["total"] == 0


@pytest.mark.parametrize("query", ["page=0", "page=10001", "page_size=0", "page_size=101", "sort=password_hash", "order=bad", "completed=bad", "q="])
def test_query_boundaries(client, auth, query):
    assert client.get(f"/tasks?{query}", headers=auth).status_code == 422


def test_health_and_openapi(client):
    assert client.get("/health/live").json() == {"status": "alive"}
    assert client.get("/health/ready").json() == {"status": "ready"}
    schema = client.get("/openapi.json").json()
    assert schema["components"]["securitySchemes"]["OAuth2PasswordBearer"]["flows"]["password"]["tokenUrl"] == "auth/token"
    assert schema["paths"]["/tasks"]["post"]["responses"]["422"]["content"]["application/json"]["schema"]["$ref"].endswith("/ErrorResponse")
    assert client.get("/docs").status_code == 200


def test_framework_errors_share_format(client):
    for method, path, status in [("GET", "/missing", 404), ("PUT", "/health/live", 405)]:
        response = client.request(method, path)
        assert response.status_code == status
        ErrorResponse.model_validate(response.json())
    assert "GET" in client.put("/health/live").headers["allow"]


def test_internal_error_is_redacted(client, application):
    def broken_db():
        raise RuntimeError("private-database-password")

    previous = application.dependency_overrides[get_db]
    application.dependency_overrides[get_db] = broken_db
    try:
        response = client.get("/health/ready")
        assert response.status_code == 500
        assert response.json()["error"]["code"] == "INTERNAL_ERROR"
        assert "private-database-password" not in response.text
    finally:
        application.dependency_overrides[get_db] = previous


def test_service_conflict_rolls_back_session(db_session):
    first = UserCreate(username="alice", email="alice@example.com", password="correct-password-123")
    register_user(db_session, first)
    with pytest.raises(BusinessError):
        register_user(db_session, first)
    second = register_user(db_session, UserCreate(username="bob", email="bob@example.com", password="correct-password-123"))
    assert second.id > 1


def test_database_enforces_foreign_keys(db_session):
    db_session.add(Task(owner_id=999, title="Orphan", priority=3))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
    assert db_session.scalar(select(Task)) is None


def test_factory_lifespan_and_disposal(configuration):
    application = create_app(configuration)
    assert not hasattr(application.state, "engine")
    disposed = []
    with TestClient(application):
        event.listen(application.state.engine, "engine_disposed", lambda engine: disposed.append(True))
        assert application.state.settings is configuration
    assert disposed == [True]
    assert not hasattr(application.state, "engine") and not hasattr(application.state, "settings")


def test_missing_schema_is_not_ready(configuration):
    with TestClient(create_app(configuration)) as client:
        response = client.get("/health/ready")
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "DATABASE_NOT_READY"
        assert client.get("/health/live").status_code == 200


def test_no_lifespan_rejects_resource_dependent_requests():
    application = create_app()

    async def scenario():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=application), base_url="http://test") as client:
            assert (await client.get("/health/live")).status_code == 200
            assert (await client.get("/health/ready")).status_code == 503

    asyncio.run(scenario())


@pytest.mark.parametrize("values", [{}, {"jwt_secret_key": "short"}, {"jwt_secret_key": " " * 40}, {"jwt_secret_key": "x" * 40, "access_token_expire_minutes": 0}, {"jwt_secret_key": "x" * 40, "database_url": "postgresql://localhost/db"}, {"jwt_secret_key": "x" * 40, "database_url": "invalid-url"}])
def test_invalid_settings(values):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **values)


def test_missing_secret_prevents_startup(monkeypatch):
    monkeypatch.setattr("main.Settings", lambda: Settings(_env_file=None))
    with pytest.raises(ValidationError):
        with TestClient(create_app()):
            pytest.fail("Missing key must prevent startup")


def test_administrator_cannot_access_another_users_task(client, auth, db_session):
    task = client.post("/tasks", headers=auth, json={"title": "Private"}).json()["data"]
    bob = register(client, "bob", "bob@example.com")
    admin = db_session.get(User, bob["id"])
    admin.role = "admin"
    db_session.commit()
    bob_auth = login(client, "bob")
    assert client.get("/admin/users", headers=bob_auth).status_code == 200
    assert client.get(f"/tasks/{task['id']}", headers=bob_auth).status_code == 404
    assert client.get("/tasks", headers=bob_auth).json()["data"]["total"] == 0
