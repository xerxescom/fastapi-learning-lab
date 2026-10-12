import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
import sqlite3

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.resources import CatalogStore, open_catalog
from main import create_app


@pytest.fixture
def tracked_store():
    stores = []

    @asynccontextmanager
    async def factory():
        async with open_catalog() as store:
            stores.append(store)
            yield store

    return factory, stores


def test_factory_does_not_open_resources(tracked_store):
    factory, stores = tracked_store
    application = create_app(store_factory=factory)
    assert stores == []
    assert not hasattr(application.state, "resources")


def test_startup_and_shutdown(tracked_store):
    factory, stores = tracked_store
    application = create_app(store_factory=factory)
    with TestClient(application) as client:
        resources = application.state.resources
        assert len(stores) == 1 and resources.store is stores[0]
        assert not resources.store.closed
        assert len(resources.snapshot) == 2
        assert client.get("/health/ready").json() == {"status": "ready"}
    assert resources.store.closed
    assert not hasattr(application.state, "resources")
    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        resources.store.get_product(1)


def test_shared_resources_reused(tracked_store):
    factory, stores = tracked_store
    application = create_app(store_factory=factory)
    with TestClient(application) as client:
        first = application.state.resources
        responses = [client.get("/runtime").json() for _ in range(3)]
        assert all(response == {"instance_id": first.instance_id, "cached_products": 2, "store_closed": False} for response in responses)
        assert application.state.resources is first
        assert len(stores) == 1


def test_product_routes():
    with TestClient(create_app()) as client:
        assert client.get("/products").json() == [
            {"id": 1, "name": "Keyboard", "price_cents": 9900},
            {"id": 2, "name": "Mouse", "price_cents": 4900},
        ]
        assert client.get("/products/1").json()["name"] == "Keyboard"
        assert client.get("/products/999").status_code == 404


@pytest.mark.parametrize("product_id", ["0", "-1", "invalid"])
def test_parameter_errors_do_not_close_resources(product_id):
    application = create_app()
    with TestClient(application) as client:
        assert client.get(f"/products/{product_id}").status_code == 422
        assert application.state.resources.store.closed is False
        assert client.get("/products/1").status_code == 200


def test_initialization_failure_closes_connection(monkeypatch):
    stores = []

    def broken_initialize(store):
        stores.append(store)
        raise RuntimeError("Initialization failed")

    monkeypatch.setattr(CatalogStore, "initialize", broken_initialize)
    application = create_app()
    with pytest.raises(RuntimeError, match="Initialization failed"):
        with TestClient(application):
            pytest.fail("Startup failure must prevent serving")
    assert len(stores) == 1 and stores[0].closed
    assert not hasattr(application.state, "resources")


def test_snapshot_failure_closes_acquired_resource(tracked_store):
    factory, stores = tracked_store

    def broken_loader(store):
        assert not store.closed
        raise ValueError("Snapshot failed")

    application = create_app(store_factory=factory, snapshot_loader=broken_loader)
    with pytest.raises(ValueError, match="Snapshot failed"):
        with TestClient(application):
            pytest.fail("Startup failure must propagate")
    assert len(stores) == 1 and stores[0].closed
    assert not hasattr(application.state, "resources")


def test_cleanup_when_with_body_raises(tracked_store):
    factory, stores = tracked_store
    application = create_app(store_factory=factory)
    with pytest.raises(RuntimeError, match="Test body failed"):
        with TestClient(application):
            raise RuntimeError("Test body failed")
    assert stores[0].closed
    assert not hasattr(application.state, "resources")


def test_lifespan_exception_releases_resource(tracked_store):
    factory, stores = tracked_store
    application = create_app(store_factory=factory)

    async def scenario():
        with pytest.raises(RuntimeError, match="Lifecycle failed"):
            async with application.router.lifespan_context(application):
                raise RuntimeError("Lifecycle failed")

    asyncio.run(scenario())
    assert stores[0].closed
    assert not hasattr(application.state, "resources")


def test_repeated_lifespan_creates_fresh_resources(tracked_store):
    factory, stores = tracked_store
    application = create_app(store_factory=factory)
    ids = []
    for _ in range(2):
        with TestClient(application) as client:
            ids.append(client.get("/runtime").json()["instance_id"])
        assert stores[-1].closed
    assert len(stores) == 2 and stores[0] is not stores[1]
    assert ids[0] != ids[1]


def test_separate_applications_have_independent_resources():
    first, second = create_app(), create_app()
    with TestClient(first) as one, TestClient(second) as two:
        assert first.state.resources.store is not second.state.resources.store
        assert one.get("/runtime").json()["instance_id"] != two.get("/runtime").json()["instance_id"]


def test_concurrent_queries_reuse_connection(tracked_store):
    factory, stores = tracked_store
    application = create_app(store_factory=factory)
    with TestClient(application) as client:
        with ThreadPoolExecutor(max_workers=4) as pool:
            responses = list(pool.map(lambda _: client.get("/products/1"), range(12)))
        assert all(response.status_code == 200 and response.json()["id"] == 1 for response in responses)
        assert len(stores) == 1 and not stores[0].closed
    assert stores[0].closed


def test_snapshot_is_read_only():
    application = create_app()
    with TestClient(application):
        snapshot = application.state.resources.snapshot
        assert isinstance(snapshot, tuple)
        with pytest.raises(ValidationError):
            snapshot[0].name = "Changed"
        assert snapshot[0].name == "Keyboard"


def test_close_is_idempotent():
    async def scenario():
        async with open_catalog() as store:
            assert store.get_product(1) is not None
        store.close()
        assert store.closed

    asyncio.run(scenario())


def test_async_transport_does_not_start_lifespan_automatically():
    application = create_app()

    async def scenario():
        transport = httpx.ASGITransport(app=application)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            assert (await client.get("/health/live")).status_code == 200
            ready = await client.get("/health/ready")
            assert ready.status_code == 503 and ready.json() == {"status": "not_ready"}
            for path in ["/runtime", "/products", "/products/1"]:
                assert (await client.get(path)).status_code == 503

    asyncio.run(scenario())
    assert not hasattr(application.state, "resources")


def test_async_transport_with_explicit_lifespan(tracked_store):
    factory, stores = tracked_store
    application = create_app(store_factory=factory)

    async def scenario():
        async with application.router.lifespan_context(application):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=application), base_url="http://test") as client:
                assert (await client.get("/products/1")).status_code == 200
                assert (await client.get("/health/ready")).status_code == 200
            assert not stores[0].closed

    asyncio.run(scenario())
    assert stores[0].closed


def test_startup_can_retry_after_loader_failure(tracked_store):
    factory, stores = tracked_store
    attempts = []

    def loader(store):
        attempts.append(True)
        if len(attempts) == 1:
            raise RuntimeError("First attempt failed")
        return store.list_products()

    application = create_app(store_factory=factory, snapshot_loader=loader)
    with pytest.raises(RuntimeError, match="First attempt failed"):
        with TestClient(application):
            pass
    assert stores[0].closed
    with TestClient(application) as client:
        assert client.get("/products").status_code == 200
        assert not stores[1].closed
    assert stores[1].closed


def test_resources_unavailable_after_shutdown():
    application = create_app()
    with TestClient(application) as client:
        assert client.get("/health/ready").status_code == 200

    async def scenario():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=application), base_url="http://test") as client:
            assert (await client.get("/health/live")).status_code == 200
            assert (await client.get("/health/ready")).status_code == 503
            assert (await client.get("/products")).status_code == 503

    asyncio.run(scenario())


def test_cancellation_in_lifespan_body_releases_resource(tracked_store):
    factory, stores = tracked_store
    application = create_app(store_factory=factory)

    async def scenario():
        with pytest.raises(asyncio.CancelledError):
            async with application.router.lifespan_context(application):
                raise asyncio.CancelledError()

    asyncio.run(scenario())
    assert stores[0].closed
    assert not hasattr(application.state, "resources")
