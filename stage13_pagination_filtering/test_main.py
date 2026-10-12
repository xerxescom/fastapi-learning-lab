from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete, func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.database import Base, get_db
from app.models import Item
from app.seed import SAMPLE_ITEMS, seed_items
from main import app


@pytest.fixture
def db_engine(tmp_path: Path) -> Generator[Engine, None, None]:
    engine = create_engine(
        f"sqlite:///{(tmp_path / 'items.db').as_posix()}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        seed_items(session)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def client(db_engine: Engine) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        with Session(db_engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


def ids(body: dict) -> list[int]:
    return [item["id"] for item in body["items"]]


def test_default_offset_response(client: TestClient) -> None:
    response = client.get("/items")
    assert response.status_code == 200
    result = response.json()
    assert set(result) == {"items", "total", "limit", "offset"}
    assert result["total"] == 8 and result["limit"] == 10 and result["offset"] == 0
    assert ids(result) == list(range(1, 9))
    assert result["items"][0] == {"id": 1, **SAMPLE_ITEMS[0]}


def test_default_page_response(client: TestClient) -> None:
    response = client.get("/items/pages")
    assert response.status_code == 200
    result = response.json()
    assert set(result) == {"items", "total", "page", "page_size", "pages"}
    assert result["total"] == 8 and result["page"] == 1
    assert result["page_size"] == 10 and result["pages"] == 1
    assert ids(result) == list(range(1, 9))


def test_offset_slice_keeps_full_filtered_total(client: TestClient) -> None:
    response = client.get("/items", params={"limit": 2, "offset": 2})
    assert response.status_code == 200
    result = response.json()
    assert ids(result) == [3, 4]
    assert result["total"] == 8 and result["limit"] == 2 and result["offset"] == 2


@pytest.mark.parametrize("page,expected", [(1, [1, 2, 3]), (2, [4, 5, 6]), (3, [7, 8]), (4, [])])
def test_page_numbers(client: TestClient, page: int, expected: list[int]) -> None:
    response = client.get("/items/pages", params={"page": page, "page_size": 3})
    assert response.status_code == 200
    result = response.json()
    assert ids(result) == expected
    assert result["total"] == 8 and result["pages"] == 3
    assert result["page"] == page and result["page_size"] == 3


@pytest.mark.parametrize("order,expected", [
    ("asc", [4, 8, 7, 2, 5, 6, 1, 3]),
    ("desc", [3, 1, 2, 5, 6, 7, 4, 8]),
])
def test_price_sorting(client: TestClient, order: str, expected: list[int]) -> None:
    response = client.get("/items", params={"sort_by": "price", "order": order})
    assert response.status_code == 200
    assert ids(response.json()) == expected


def test_name_sorting_and_id_descending(client: TestClient) -> None:
    names = client.get("/items", params={"sort_by": "name"}).json()["items"]
    assert [item["name"] for item in names] == sorted(item["name"] for item in SAMPLE_ITEMS)
    assert ids(client.get("/items", params={"order": "desc"}).json()) == list(range(8, 0, -1))


@pytest.mark.parametrize("order", ["asc", "desc"])
def test_tied_values_are_stable_across_pages(client: TestClient, order: str) -> None:
    params = {"min_price": 49, "max_price": 49, "sort_by": "price", "order": order, "limit": 2}
    first = client.get("/items", params=params).json()
    second = client.get("/items", params={**params, "offset": 2}).json()
    assert first["total"] == second["total"] == 3
    assert ids(first) == [2, 5] and ids(second) == [6]


@pytest.mark.parametrize("params,expected", [
    ({"category": "office"}, [1, 3, 5, 6]),
    ({"in_stock": "false"}, [3, 6, 8]),
    ({"in_stock": "true"}, [1, 2, 4, 5, 7]),
    ({"q": "  KEY  "}, [1]),
    ({"q": "%"}, [7]),
    ({"q": "_"}, [8]),
    ({"min_price": 49, "max_price": 49}, [2, 5, 6]),
    ({"max_price": 0}, []),
    ({"category": "office", "in_stock": "false", "min_price": 0, "max_price": 100}, [6]),
])
def test_filters(client: TestClient, params: dict, expected: list[int]) -> None:
    response = client.get("/items", params=params)
    assert response.status_code == 200
    assert ids(response.json()) == expected
    assert response.json()["total"] == len(expected)


def test_pagination_modes_use_identical_filters_and_order(client: TestClient) -> None:
    params = {"in_stock": "true", "sort_by": "price", "order": "desc"}
    offset = client.get("/items", params={**params, "offset": 2, "limit": 2}).json()
    page = client.get("/items/pages", params={**params, "page": 2, "page_size": 2}).json()
    assert offset["items"] == page["items"]
    assert ids(page) == [5, 7]
    assert offset["total"] == page["total"] == 5
    assert page["pages"] == 3


@pytest.mark.parametrize("params", [{"q": "not-found"}, {"min_price": 500}])
def test_empty_filtered_pages(client: TestClient, params: dict) -> None:
    result = client.get("/items/pages", params={**params, "page": 5}).json()
    assert result["items"] == [] and result["total"] == 0 and result["pages"] == 0
    assert result["page"] == 5


def test_empty_database(client: TestClient, db_engine: Engine) -> None:
    with Session(db_engine) as session:
        session.execute(delete(Item))
        session.commit()
    offset = client.get("/items").json()
    page = client.get("/items/pages").json()
    assert offset["items"] == page["items"] == []
    assert offset["total"] == page["total"] == page["pages"] == 0


@pytest.mark.parametrize("path,params", [
    ("/items", {"limit": 1}),
    ("/items", {"limit": 100}),
    ("/items", {"offset": 8}),
    ("/items", {"offset": 1_000_000}),
    ("/items/pages", {"page_size": 1}),
    ("/items/pages", {"page_size": 100}),
    ("/items/pages", {"page": 10_000}),
])
def test_valid_pagination_boundaries(client: TestClient, path: str, params: dict) -> None:
    response = client.get(path, params=params)
    assert response.status_code == 200
    assert response.json()["total"] == 8
    if params.get("offset", 0) >= 8 or params.get("page", 0) == 10_000:
        assert response.json()["items"] == []


@pytest.mark.parametrize("path,params", [
    ("/items", {"limit": 0}),
    ("/items", {"limit": 101}),
    ("/items", {"offset": -1}),
    ("/items", {"offset": 1_000_001}),
    ("/items", {"limit": "abc"}),
    ("/items/pages", {"page": 0}),
    ("/items/pages", {"page": 10_001}),
    ("/items/pages", {"page_size": 0}),
    ("/items/pages", {"page_size": 101}),
    ("/items", {"q": ""}),
    ("/items", {"q": "   "}),
    ("/items", {"q": "a" * 51}),
    ("/items", {"category": "unknown"}),
    ("/items", {"sort_by": "price; DROP TABLE items"}),
    ("/items", {"order": "random"}),
    ("/items", {"in_stock": "maybe"}),
    ("/items", {"min_price": -1}),
    ("/items", {"max_price": "nan"}),
    ("/items", {"max_price": "inf"}),
    ("/items", {"min_price": 100, "max_price": 10}),
    ("/items/pages", {"min_price": 100, "max_price": 10}),
    ("/items", {"page": 1}),
    ("/items/pages", {"limit": 10}),
])
def test_invalid_parameters_return_422(client: TestClient, path: str, params: dict) -> None:
    response = client.get(path, params=params)
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"][0] == "query"


def test_seed_is_idempotent_and_preserves_existing_data(db_engine: Engine) -> None:
    with Session(db_engine) as session:
        session.get(Item, 1).name = "Custom keyboard"
        session.commit()
        assert seed_items(session) is False
        assert session.scalar(select(func.count()).select_from(Item)) == 8
        assert session.get(Item, 1).name == "Custom keyboard"


def test_query_models_are_documented_as_query_parameters(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    operation = schema["paths"]["/items/pages"]["get"]
    assert "requestBody" not in operation
    assert all(parameter["in"] == "query" for parameter in operation["parameters"])
    assert {parameter["name"] for parameter in operation["parameters"]} == {
        "q", "category", "in_stock", "min_price", "max_price", "sort_by", "order", "page", "page_size"
    }
