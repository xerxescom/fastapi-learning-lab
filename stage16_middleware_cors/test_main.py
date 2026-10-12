import asyncio
import logging
from collections.abc import Generator
from uuid import UUID

import httpx
import pytest
from fastapi.testclient import TestClient

from app.middleware import RequestLogMiddleware
from main import DEFAULT_ORIGINS, EXPOSE_HEADERS, create_app

ORIGIN = DEFAULT_ORIGINS[0]


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(create_app(), raise_server_exceptions=False) as test_client:
        yield test_client


def assert_observation_headers(response):
    assert UUID(response.headers["x-request-id"]).version == 4
    assert float(response.headers["x-process-time-ms"]) >= 0


def request_logs(caplog):
    return [record for record in caplog.records if record.name == "stage16.requests"]


def test_response_headers_and_log(client: TestClient, caplog):
    response = client.get("/items/12")
    assert response.status_code == 200 and response.json() == {"item_id": 12}
    assert_observation_headers(response)
    records = request_logs(caplog)
    assert len(records) == 1
    record = records[0]
    assert record.request_id == response.headers["x-request-id"]
    assert record.method == "GET" and record.route == "/items/{item_id}"
    assert record.status_code == 200 and record.duration_ms >= 0
    assert record.failed is False


def test_complete_middleware_order(client: TestClient):
    response = client.get("/middleware-order")
    assert response.json() == {"trace": ["outer:before", "inner:before", "handler"]}
    assert response.headers["x-middleware-order"] == "outer:before,inner:before,handler,inner:after,outer:after"


@pytest.mark.parametrize("origin", DEFAULT_ORIGINS)
def test_allowed_origin(client: TestClient, origin):
    response = client.get("/health", headers={"Origin": origin})
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
    assert response.headers["access-control-allow-credentials"] == "true"
    assert "Origin" in response.headers["vary"]
    assert set(response.headers["access-control-expose-headers"].split(", ")) == set(EXPOSE_HEADERS)


@pytest.mark.parametrize("origin", ["https://localhost:5173", "http://localhost:5174", "http://localhost:5173/", "https://evil.example", "null"])
def test_disallowed_simple_origin_is_not_api_authorization(client: TestClient, origin):
    response = client.post("/items", json={"name": "demo", "quantity": 1}, headers={"Origin": origin})
    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers
    assert_observation_headers(response)


def test_request_without_origin(client: TestClient):
    response = client.get("/health")
    assert "access-control-allow-origin" not in response.headers
    assert "access-control-expose-headers" not in response.headers


def test_preflight_success_is_logged_without_route(client: TestClient, caplog):
    response = client.options("/items", headers={"Origin": ORIGIN, "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "content-type, x-csrf-token"})
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ORIGIN
    assert response.headers["access-control-allow-methods"] == "GET, POST"
    assert "x-csrf-token" in response.headers["access-control-allow-headers"].lower()
    assert response.headers["access-control-max-age"] == "600"
    assert_observation_headers(response)
    assert "x-middleware-order" not in response.headers
    records = request_logs(caplog)
    assert len(records) == 1 and records[0].method == "OPTIONS"
    assert records[0].route == "<unmatched>" and records[0].status_code == 200


@pytest.mark.parametrize("headers", [
    {"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"},
    {"Origin": ORIGIN, "Access-Control-Request-Method": "DELETE"},
    {"Origin": ORIGIN, "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "X-Forbidden"},
])
def test_preflight_rejected(client: TestClient, headers, caplog):
    response = client.options("/items", headers=headers)
    assert response.status_code == 400
    assert_observation_headers(response)
    assert "x-middleware-order" not in response.headers
    assert request_logs(caplog)[0].status_code == 400


def test_options_without_preflight_headers_reaches_router(client: TestClient):
    response = client.options("/health", headers={"Origin": ORIGIN})
    assert response.status_code == 405
    assert response.headers["access-control-allow-origin"] == ORIGIN
    assert "x-middleware-order" in response.headers


@pytest.mark.parametrize("path,status", [("/missing", 404), ("/items/not-an-int", 422), ("/errors/http", 409), ("/errors/unhandled", 500)])
def test_error_responses_keep_headers_and_single_log(client: TestClient, path, status, caplog):
    response = client.get(path, headers={"Origin": ORIGIN})
    assert response.status_code == status
    assert_observation_headers(response)
    assert response.headers["access-control-allow-origin"] == ORIGIN
    assert response.headers["x-middleware-order"].endswith("inner:after,outer:after")
    records = request_logs(caplog)
    assert len(records) == 1 and records[0].status_code == status
    if status == 500:
        assert response.json() == {"detail": "Internal server error"}
        assert "internal demo error" not in response.text
        assert records[0].levelno == logging.ERROR and records[0].failed is True


def test_unhandled_error_still_propagates_to_server(caplog):
    with TestClient(create_app()) as client:
        with pytest.raises(RuntimeError, match="internal demo error"):
            client.get("/errors/unhandled")
    assert len(request_logs(caplog)) == 1


def test_logs_do_not_include_sensitive_values(client: TestClient, caplog):
    client.post("/items?token=secret-query", json={"name": "secret-body", "quantity": 2}, headers={"Cookie": "session=secret-cookie", "Authorization": "Bearer secret-auth"})
    messages = " ".join(record.getMessage() for record in request_logs(caplog))
    assert "secret" not in messages
    assert len(request_logs(caplog)) == 1


def test_request_id_is_generated_not_trusted(client: TestClient):
    first = client.get("/health", headers={"X-Request-ID": "untrusted"})
    second = client.get("/health")
    assert first.headers["x-request-id"] != "untrusted"
    assert first.headers["x-request-id"] != second.headers["x-request-id"]


def test_per_request_state_isolated_under_concurrency():
    async def run():
        transport = httpx.ASGITransport(app=create_app())
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await asyncio.gather(*(client.get("/middleware-order") for _ in range(10)))

    responses = asyncio.run(run())
    assert len({response.headers["x-request-id"] for response in responses}) == 10
    for response in responses:
        assert response.headers["x-middleware-order"] == "outer:before,inner:before,handler,inner:after,outer:after"


def test_no_origins_configuration():
    with TestClient(create_app(allow_origins=[])) as client:
        response = client.get("/health", headers={"Origin": ORIGIN})
        assert "access-control-allow-origin" not in response.headers


def test_reject_wildcard_with_credentials():
    with pytest.raises(ValueError, match="explicit origins"):
        create_app(allow_origins=["*"])


def test_non_http_scope_passes_through():
    seen = []

    async def downstream(scope, receive, send):
        seen.append(scope["type"])

    async def unused():
        raise AssertionError("Should not receive or send")

    asyncio.run(RequestLogMiddleware(downstream)({"type": "websocket"}, unused, unused))
    assert seen == ["websocket"]


def test_docs_and_openapi_still_available(client: TestClient):
    assert client.get("/docs").status_code == 200
    assert "/middleware-order" in client.get("/openapi.json").json()["paths"]
