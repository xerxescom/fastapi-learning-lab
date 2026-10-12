from collections.abc import Generator
from http.cookies import SimpleCookie

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import Settings
from app.security import DEMO_PASSWORD, DEMO_USERNAME
from app.sessions import SessionStore
from main import SESSION_COOKIE, THEME_COOKIE, create_app


@pytest.fixture
def clock() -> list[float]:
    return [1000.0]


@pytest.fixture
def store(clock: list[float]) -> SessionStore:
    return SessionStore(60, clock=lambda: clock[0])


@pytest.fixture
def client(store: SessionStore) -> Generator[TestClient, None, None]:
    settings = Settings(_env_file=None, cookie_secure=False, session_ttl_seconds=60)
    with TestClient(create_app(settings, store=store)) as test_client:
        yield test_client


def csrf_headers(client: TestClient) -> dict[str, str]:
    response = client.get("/auth/csrf")
    assert response.status_code == 200
    return {"X-CSRF-Token": response.json()["csrf_token"]}


def log_in(client: TestClient):
    response = client.post("/auth/login", data={"username": DEMO_USERNAME, "password": DEMO_PASSWORD}, headers=csrf_headers(client))
    assert response.status_code == 200
    return response


def test_anonymous_csrf_cookie(client: TestClient, store: SessionStore):
    response = client.get("/auth/csrf")
    cookie = SimpleCookie(response.headers["set-cookie"])[SESSION_COOKIE]
    assert cookie["httponly"] and cookie["samesite"] == "lax"
    assert cookie["path"] == "/" and cookie["max-age"] == "60" and not cookie["secure"]
    session = store.get(cookie.value)
    assert session is not None and session.username is None
    assert response.json() == {"csrf_token": session.csrf_token}
    assert response.headers["cache-control"] == "no-store"
    assert DEMO_PASSWORD not in cookie.value and DEMO_USERNAME not in cookie.value
    assert client.get("/auth/me").status_code == 401


def test_csrf_reuses_session_without_sliding_expiry(client: TestClient, clock: list[float], store: SessionStore):
    first = client.get("/auth/csrf")
    old_cookie = client.cookies.get(SESSION_COOKIE)
    expiry = store.get(old_cookie).expires_at
    clock[0] += 30
    second = client.get("/auth/csrf")
    assert second.json() == first.json()
    assert "set-cookie" not in second.headers
    assert store.get(old_cookie).expires_at == expiry


def test_login_rotates_cookie_and_csrf(client: TestClient, store: SessionStore):
    headers = csrf_headers(client)
    old_cookie = client.cookies.get(SESSION_COOKIE)
    response = client.post("/auth/login", data={"username": DEMO_USERNAME, "password": DEMO_PASSWORD}, headers=headers)
    assert response.status_code == 200
    assert response.json()["username"] == DEMO_USERNAME
    assert response.json()["csrf_token"] != headers["X-CSRF-Token"]
    assert client.cookies.get(SESSION_COOKIE) != old_cookie
    assert store.get(old_cookie) is None
    assert client.get("/auth/me").json() == {"username": DEMO_USERNAME}
    assert DEMO_PASSWORD not in response.text and "password_hash" not in response.text
    assert client.get("/auth/me", headers={"Cookie": f"{SESSION_COOKIE}={old_cookie}"}).status_code == 401


@pytest.mark.parametrize("username,password", [(DEMO_USERNAME, "wrong"), ("unknown", DEMO_PASSWORD)])
def test_login_wrong_credentials(client: TestClient, username, password):
    headers = csrf_headers(client)
    old_cookie = client.cookies.get(SESSION_COOKIE)
    response = client.post("/auth/login", data={"username": username, "password": password}, headers=headers)
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid username or password"}
    assert "set-cookie" not in response.headers
    assert client.cookies.get(SESSION_COOKIE) == old_cookie
    assert client.get("/auth/me").status_code == 401


@pytest.mark.parametrize("payload", [{}, {"username": DEMO_USERNAME}, {"username": "x" * 51, "password": DEMO_PASSWORD}, {"username": DEMO_USERNAME, "password": "private-secret-" * 20}])
def test_invalid_form_is_redacted(client: TestClient, payload):
    response = client.post("/auth/login", data=payload, headers=csrf_headers(client))
    assert response.status_code == 422
    for error in response.json()["detail"]:
        assert set(error) == {"loc", "msg", "type"}
    assert DEMO_PASSWORD not in response.text and "private-secret" not in response.text


def test_json_is_not_form(client: TestClient):
    response = client.post("/auth/login", json={"username": DEMO_USERNAME, "password": DEMO_PASSWORD}, headers=csrf_headers(client))
    assert response.status_code == 422


@pytest.mark.parametrize("token", [None, "wrong", ""])
def test_login_requires_csrf(client: TestClient, token):
    csrf_headers(client)
    response = client.post("/auth/login", data={"username": DEMO_USERNAME, "password": DEMO_PASSWORD}, headers={} if token is None else {"X-CSRF-Token": token})
    assert response.status_code == 403
    assert client.get("/auth/me").status_code == 401


def test_login_requires_session_cookie(client: TestClient):
    response = client.post("/auth/login", data={"username": DEMO_USERNAME, "password": DEMO_PASSWORD}, headers={"X-CSRF-Token": "forged"})
    assert response.status_code == 401


def test_csrf_bound_to_each_session(client: TestClient, store: SessionStore):
    token = csrf_headers(client)["X-CSRF-Token"]
    with TestClient(create_app(Settings(_env_file=None), store=store)) as other:
        csrf_headers(other)
        response = other.post("/auth/login", data={"username": DEMO_USERNAME, "password": DEMO_PASSWORD}, headers={"X-CSRF-Token": token})
        assert response.status_code == 403


def test_logout_revokes_cookie_and_old_session(client: TestClient, store: SessionStore):
    login = log_in(client)
    old_cookie = client.cookies.get(SESSION_COOKIE)
    response = client.post("/auth/logout", headers={"X-CSRF-Token": login.json()["csrf_token"]})
    assert response.status_code == 200
    assert response.json() == {"message": "Logged out"}
    assert client.cookies.get(SESSION_COOKIE) is None
    assert SimpleCookie(response.headers["set-cookie"])[SESSION_COOKIE]["max-age"] == "0"
    assert store.get(old_cookie) is None
    assert client.get("/auth/me").status_code == 401
    assert client.get("/auth/me", headers={"Cookie": f"{SESSION_COOKIE}={old_cookie}"}).status_code == 401


def test_old_csrf_rejected_after_login(client: TestClient):
    headers = csrf_headers(client)
    assert client.post("/auth/login", data={"username": DEMO_USERNAME, "password": DEMO_PASSWORD}, headers=headers).status_code == 200
    assert client.post("/auth/logout", headers=headers).status_code == 403
    assert client.get("/auth/me").status_code == 200


@pytest.mark.parametrize("elapsed,expected", [(59, 200), (60, 401), (61, 401)])
def test_session_expiration(client: TestClient, clock: list[float], elapsed, expected):
    log_in(client)
    clock[0] += elapsed
    assert client.get("/auth/me").status_code == expected


def test_expired_csrf_creates_new_anonymous_session(client: TestClient, clock: list[float]):
    old = log_in(client).json()["csrf_token"]
    old_cookie = client.cookies.get(SESSION_COOKIE)
    clock[0] += 60
    response = client.get("/auth/csrf")
    assert response.json()["csrf_token"] != old
    assert client.cookies.get(SESSION_COOKIE) != old_cookie
    assert client.get("/auth/me").status_code == 401


@pytest.mark.parametrize("value", ["forged", DEMO_USERNAME, "eyJhbGciOiJIUzI1NiJ9.fake.signature"])
def test_forged_session_cookie(client: TestClient, value):
    assert client.get("/auth/me", headers={"Cookie": f"{SESSION_COOKIE}={value}"}).status_code == 401


def test_theme_cookie_lifecycle(client: TestClient):
    assert client.get("/cookies/theme").json() == {"theme": "light"}
    headers = csrf_headers(client)
    response = client.post("/cookies/theme", data={"theme": "dark"}, headers=headers)
    assert response.json() == {"theme": "dark"}
    cookie = SimpleCookie(response.headers["set-cookie"])[THEME_COOKIE]
    assert cookie["max-age"] == "86400" and not cookie["httponly"]
    assert client.get("/cookies/theme").json() == {"theme": "dark"}
    assert client.get("/auth/me").status_code == 401
    assert client.delete("/cookies/theme", headers=headers).status_code == 200
    assert client.cookies.get(THEME_COOKIE) is None
    assert client.get("/cookies/theme").json() == {"theme": "light"}


def test_tampered_theme_cookie_is_validated(client: TestClient):
    response = client.get("/cookies/theme", headers={"Cookie": f"{THEME_COOKIE}=admin"})
    assert response.status_code == 422


@pytest.mark.parametrize("method,path,data", [("post", "/auth/logout", None), ("post", "/cookies/theme", {"theme": "dark"}), ("delete", "/cookies/theme", None)])
def test_state_changes_require_csrf(client: TestClient, method, path, data):
    log_in(client)
    kwargs = {"data": data} if data is not None else {}
    assert client.request(method, path, **kwargs).status_code == 403


def test_invalid_theme_form(client: TestClient):
    response = client.post("/cookies/theme", data={"theme": "admin"}, headers=csrf_headers(client))
    assert response.status_code == 422
    assert client.cookies.get(THEME_COOKIE) is None


def test_secure_cookie_on_https(store: SessionStore):
    settings = Settings(_env_file=None, cookie_secure=True, session_ttl_seconds=60)
    with TestClient(create_app(settings, store=store), base_url="https://testserver") as client:
        response = client.get("/auth/csrf")
        assert SimpleCookie(response.headers["set-cookie"])[SESSION_COOKIE]["secure"]
        log_in(client)
        assert client.get("/auth/me").status_code == 200


def test_store_capacity_and_expired_cleanup(clock: list[float]):
    store = SessionStore(60, clock=lambda: clock[0], capacity=1)
    first = store.create()
    with pytest.raises(HTTPException) as error:
        store.create()
    assert error.value.status_code == 503
    rotated = store.create(username=DEMO_USERNAME, previous_id=first.session_id)
    assert store.get(first.session_id) is None
    clock[0] += 60
    fresh = store.create()
    assert store.get(rotated.session_id) is None
    assert store.get(fresh.session_id) == fresh


@pytest.mark.parametrize("ttl", [0, -1, 86401])
def test_settings_ttl_boundaries(ttl):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, session_ttl_seconds=ttl)


def test_openapi_declares_form_cookie_and_header(client: TestClient):
    schema = client.get("/openapi.json").json()
    operation = schema["paths"]["/auth/login"]["post"]
    assert "application/x-www-form-urlencoded" in operation["requestBody"]["content"]
    params = {(param["name"], param["in"]) for param in operation["parameters"]}
    assert (SESSION_COOKIE, "cookie") in params and ("X-CSRF-Token", "header") in params


def test_restart_does_not_share_sessions(client: TestClient):
    log_in(client)
    token = client.cookies.get(SESSION_COOKIE)
    with TestClient(create_app(Settings(_env_file=None))) as other:
        assert other.get("/auth/me", headers={"Cookie": f"{SESSION_COOKIE}={token}"}).status_code == 401
