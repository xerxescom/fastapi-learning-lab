import asyncio
from contextlib import asynccontextmanager

import httpx
import pytest
from pydantic import ValidationError

from app.catalog import MAX_RESPONSE_BYTES
from app.config import Settings
from main import create_app


@pytest.fixture
def anyio_backend():
    return "asyncio"


def settings(**overrides):
    values = {"upstream_base_url": "https://catalog.test/api/", "http_timeout_seconds": 0.5, "request_deadline_seconds": 1}
    values.update(overrides)
    return Settings(_env_file=None, **values)


@asynccontextmanager
async def mock_client(handler, **overrides):
    application = create_app(settings(**overrides), transport=httpx.MockTransport(handler))
    # ASGITransport 不会自动启动 lifespan，测试显式进入同一事件循环。
    async with application.router.lifespan_context(application):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=application), base_url="http://testserver") as client:
            yield client, application


@pytest.mark.anyio
async def test_success_request_parameters_and_response_filtering():
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json={"id": 1, "name": "Keyboard", "price": 99.0, "secret": "upstream-private"})

    async with mock_client(handler) as (client, application):
        response = await client.get("/products/1")
        assert response.status_code == 200
        assert response.json() == {"id": 1, "name": "Keyboard", "price": 99.0}
        assert seen[0].method == "GET" and str(seen[0].url) == "https://catalog.test/api/products/1"
        assert seen[0].headers["accept"] == "application/json"
        assert seen[0].extensions["timeout"] == {"connect": 0.5, "read": 0.5, "write": 0.5, "pool": 0.5}


@pytest.mark.anyio
async def test_client_reused_and_closed_after_lifespan():
    async with mock_client(lambda request: httpx.Response(200, json={"id": 1, "name": "A", "price": 1})) as (client, application):
        outbound = application.state.http_client
        assert not outbound.is_closed
        assert (await client.get("/products/1")).status_code == 200
        assert (await client.get("/products/1")).status_code == 200
        assert application.state.http_client is outbound
    assert outbound.is_closed
    assert not hasattr(application.state, "catalog")


@pytest.mark.anyio
@pytest.mark.parametrize("status,expected", [(404, 404), (401, 502), (403, 502), (429, 502), (500, 502), (503, 502), (204, 502)])
async def test_upstream_status_mapping_is_sanitized(status, expected):
    async with mock_client(lambda request: httpx.Response(status, json={"secret": "private-token"})) as (client, _):
        response = await client.get("/products/1")
        assert response.status_code == expected
        assert "private-token" not in response.text


@pytest.mark.anyio
async def test_redirect_not_followed():
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(302, headers={"Location": "http://private-host/secret"})

    async with mock_client(handler) as (client, _):
        assert (await client.get("/products/1")).status_code == 502
    assert len(seen) == 1


@pytest.mark.anyio
@pytest.mark.parametrize("exception,expected", [(httpx.ConnectTimeout, 504), (httpx.ReadTimeout, 504), (httpx.WriteTimeout, 504), (httpx.PoolTimeout, 503), (httpx.ConnectError, 502), (httpx.ReadError, 502), (httpx.RemoteProtocolError, 502)])
async def test_transport_error_mapping(exception, expected):
    def handler(request):
        raise exception("sensitive upstream connection details", request=request)

    async with mock_client(handler) as (client, _):
        response = await client.get("/products/1")
        assert response.status_code == expected
        assert "sensitive" not in response.text


@pytest.mark.anyio
async def test_total_deadline_and_cancellation():
    cancelled = asyncio.Event()

    async def handler(request):
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.set()

    async with mock_client(handler, request_deadline_seconds=0.05) as (client, _):
        response = await client.get("/products/1")
        assert response.status_code == 504
        assert cancelled.is_set()


@pytest.mark.anyio
@pytest.mark.parametrize("payload", [
    {}, {"id": 2, "name": "Wrong ID", "price": 1},
    {"id": "1", "name": "String ID", "price": 1},
    {"id": 1, "name": "", "price": 1},
    {"id": 1, "name": "A", "price": -1},
    {"id": 1, "name": "A", "price": "99"},
    [1, 2, 3],
])
async def test_invalid_upstream_schema(payload):
    async with mock_client(lambda request: httpx.Response(200, json=payload)) as (client, _):
        response = await client.get("/products/1")
        assert response.status_code == 502
        assert response.json() == {"detail": "Invalid upstream response"}


@pytest.mark.anyio
@pytest.mark.parametrize("content,content_type", [(b"not-json", "application/json"), (b"<html>secret</html>", "text/html"), (b'{"id":1,"name":"A","price":NaN}', "application/json"), (b'{"id":1,"name":"A","price":Infinity}', "application/json")])
async def test_invalid_upstream_content(content, content_type):
    async with mock_client(lambda request: httpx.Response(200, content=content, headers={"Content-Type": content_type})) as (client, _):
        response = await client.get("/products/1")
        assert response.status_code == 502
        assert "secret" not in response.text


@pytest.mark.anyio
async def test_response_size_limit():
    async with mock_client(lambda request: httpx.Response(200, content=b" " * (MAX_RESPONSE_BYTES + 1), headers={"Content-Type": "application/json"})) as (client, _):
        response = await client.get("/products/1")
        assert response.status_code == 502
        assert response.json() == {"detail": "Upstream response is too large"}


@pytest.mark.anyio
@pytest.mark.parametrize("path", ["/products/0", "/products/-1", "/products/1000001", "/products/not-int"])
async def test_invalid_input_does_not_call_upstream(path):
    def handler(request):
        pytest.fail("Invalid input must not call upstream")

    async with mock_client(handler) as (client, _):
        assert (await client.get(path)).status_code == 422


@pytest.mark.anyio
async def test_async_requests_can_overlap_without_timing_assumptions():
    both_started = asyncio.Event()
    release = asyncio.Event()
    requests = []

    async def handler(request):
        requests.append(request)
        if len(requests) == 2:
            both_started.set()
        await release.wait()
        product_id = int(request.url.path.rsplit("/", 1)[1])
        return httpx.Response(200, json={"id": product_id, "name": "A", "price": 1})

    async with mock_client(handler, request_deadline_seconds=5) as (client, _):
        calls = [asyncio.create_task(client.get(f"/products/{value}")) for value in (1, 2)]
        try:
            await asyncio.wait_for(both_started.wait(), timeout=2)
            assert all(not call.done() for call in calls)
            assert (await client.get("/health")).status_code == 200
        finally:
            release.set()
            responses = await asyncio.gather(*calls)
        assert [response.json()["id"] for response in responses] == [1, 2]


@pytest.mark.parametrize("values", [
    {"http_timeout_seconds": 0}, {"http_timeout_seconds": float("inf")},
    {"request_deadline_seconds": 61}, {"upstream_base_url": "ftp://example.com"},
    {"upstream_base_url": "https://user:password@example.com"},
    {"upstream_base_url": "https://example.com/?token=secret"},
    {"upstream_base_url": "https://example.com/#fragment"},
])
def test_settings_validation(values):
    with pytest.raises(ValidationError):
        settings(**values)


@pytest.mark.anyio
async def test_docs_and_health_do_not_require_upstream():
    def handler(request):
        pytest.fail("Health and docs must not call upstream")

    async with mock_client(handler) as (client, _):
        assert (await client.get("/health")).json() == {"status": "ok"}
        assert (await client.get("/docs")).status_code == 200
        assert "/products/{product_id}" in (await client.get("/openapi.json")).json()["paths"]
