import asyncio
import json
import logging
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from app.logging_config import JsonFormatter, configure_logging
from app.middleware import ObservabilityMiddleware
from main import create_app


@pytest.fixture
def records():
    captured = []

    class RecordHandler(logging.Handler):
        def emit(self, record):
            captured.append(record)

    handler = RecordHandler()
    logger = configure_logging()
    logger.addHandler(handler)
    try:
        yield captured
    finally:
        logger.removeHandler(handler)
        handler.close()


@pytest.fixture
def client():
    with TestClient(create_app(), raise_server_exceptions=False) as test_client:
        yield test_client


def completed(records):
    return [record for record in records if record.getMessage() == "request.completed"]


@pytest.mark.parametrize("path,status,level,route", [
    ("/health/live", 200, logging.INFO, "/health/live"),
    ("/health/ready", 200, logging.INFO, "/health/ready"),
    ("/items/12", 200, logging.INFO, "/items/{item_id}"),
    ("/items/bad", 422, logging.WARNING, "/items/{item_id}"),
    ("/missing-secret", 404, logging.WARNING, "<unmatched>"),
    ("/errors/http", 409, logging.WARNING, "/errors/http"),
    ("/errors/unhandled", 500, logging.ERROR, "/errors/unhandled"),
])
def test_request_logs(client, records, path, status, level, route):
    response = client.get(path)
    assert response.status_code == status
    record, = completed(records)
    assert record.levelno == level
    assert record.status_code == status and record.route == route
    assert record.request_id == response.headers["x-request-id"]
    assert len(record.request_id) == 32
    assert record.duration_ms >= 0
    assert record.failed is (status == 500)


def test_error_correlated_without_sensitive_details(client, records):
    response = client.get("/errors/unhandled")
    error, = [record for record in records if record.getMessage() == "request.exception"]
    request, = completed(records)
    assert error.request_id == request.request_id == response.headers["x-request-id"]
    assert error.error_type == "RuntimeError" and error.levelno == logging.ERROR
    assert response.json() == {"detail": "Internal server error"}
    formatted = "\n".join(JsonFormatter().format(record) for record in records)
    assert "private-demo-secret" not in formatted + response.text


def test_private_inputs_not_logged(client, records):
    response = client.get(
        "/items/123456?token=query-secret",
        headers={"Authorization": "Bearer auth-secret", "Cookie": "sid=cookie-secret", "X-Request-ID": "untrusted-id"},
    )
    assert response.json()["request_id"] == response.headers["x-request-id"]
    text = "\n".join(JsonFormatter().format(record) for record in records)
    for secret in ["123456", "query-secret", "auth-secret", "cookie-secret", "untrusted-id"]:
        assert secret not in text


@pytest.mark.parametrize("value,status,body", [(True, 200, "ready"), (False, 503, "not_ready")])
def test_readiness_dependency(value, status, body, records):
    with TestClient(create_app(readiness_probe=lambda: value)) as client:
        response = client.get("/health/ready")
        assert response.status_code == status
        assert response.json() == {"status": body}
        assert client.get("/health/live").json() == {"status": "alive"}
    assert completed(records)[0].status_code == status


def test_readiness_exception_is_503_not_500(records):
    def unavailable():
        raise OSError("database-password-secret")

    with TestClient(create_app(readiness_probe=unavailable)) as client:
        response = client.get("/health/ready")
        assert response.status_code == 503 and response.json() == {"status": "not_ready"}
        assert client.get("/health/live").status_code == 200
    assert "database-password-secret" not in "\n".join(JsonFormatter().format(record) for record in records)


def test_readiness_recovers_without_restart():
    state = {"ready": False}
    with TestClient(create_app(readiness_probe=lambda: state["ready"])) as client:
        assert client.get("/health/ready").status_code == 503
        state["ready"] = True
        assert client.get("/health/ready").status_code == 200


def test_application_probes_are_independent():
    with TestClient(create_app(readiness_probe=lambda: False)) as first, TestClient(create_app()) as second:
        assert first.get("/health/ready").status_code == 503
        assert second.get("/health/ready").status_code == 200


def test_concurrent_request_ids(client, records):
    with ThreadPoolExecutor(max_workers=4) as pool:
        responses = list(pool.map(lambda number: client.get(f"/items/{number}"), range(12)))
    ids = {response.headers["x-request-id"] for response in responses}
    assert len(ids) == 12
    assert {record.request_id for record in completed(records)} == ids
    assert all(response.json()["request_id"] == response.headers["x-request-id"] for response in responses)


def test_configure_logging_idempotent_and_local():
    root_handlers = list(logging.getLogger().handlers)
    logger = configure_logging()
    before = list(logger.handlers)
    assert configure_logging() is logger
    assert logger.handlers == before
    assert logging.getLogger().handlers == root_handlers
    assert logger.propagate is False
    assert sum(bool(getattr(handler, "stage22_handler", False)) for handler in logger.handlers) == 1


def test_json_formatter_allowlist_and_single_line():
    record = logging.LogRecord("stage22", logging.ERROR, __file__, 1, "request.exception", (), None)
    record.request_id = "safe-id"
    record.error_type = "RuntimeError"
    record.password = "do-not-log"
    record.exc_info = (RuntimeError, RuntimeError("hidden-secret"), None)
    text = JsonFormatter().format(record)
    payload = json.loads(text)
    assert payload["event"] == "request.exception" and payload["level"] == "ERROR"
    assert payload["timestamp"].endswith("+00:00")
    assert payload["request_id"] == "safe-id"
    assert "do-not-log" not in text and "hidden-secret" not in text
    assert "\n" not in text


def test_non_http_scope_is_forwarded_without_logs(records):
    received = []

    async def downstream(scope, receive, send):
        received.append(scope["type"])

    async def receive():
        return {}

    async def send(message):
        pass

    asyncio.run(ObservabilityMiddleware(downstream)({"type": "lifespan"}, receive, send))
    assert received == ["lifespan"] and not completed(records)


def test_failure_after_response_start_keeps_wire_status(records):
    messages = []

    async def downstream(scope, receive, send):
        await send({"type": "http.response.start", "status": 200, "headers": []})
        raise RuntimeError("stream-private-secret")

    async def receive():
        return {}

    async def send(message):
        messages.append(message)

    with pytest.raises(RuntimeError):
        asyncio.run(ObservabilityMiddleware(downstream)({"type": "http", "method": "GET"}, receive, send))
    assert len(messages) == 1 and messages[0]["status"] == 200
    record, = completed(records)
    assert record.status_code == 200 and record.failed is True and record.levelno == logging.ERROR
