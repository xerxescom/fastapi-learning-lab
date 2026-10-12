import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_list_items_with_valid_token_and_params() -> None:
    response = client.get(
        "/items",
        params={"q": "keyboard", "limit": 5, "offset": 2},
        headers={"x-token": "learning-token"},
    )
    assert response.status_code == 200
    assert response.json() == {
        "message": "ok",
        "q": "keyboard",
        "limit": 5,
        "offset": 2,
    }


def test_list_items_without_token_returns_401() -> None:
    response = client.get("/items")
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or missing token"


@pytest.mark.parametrize("params, field", [
    ({"limit": 0}, "limit"),
    ({"limit": 101}, "limit"),
    ({"limit": "invalid"}, "limit"),
    ({"offset": -1}, "offset"),
])
def test_list_items_with_invalid_query_returns_422(params, field) -> None:
    response = client.get(
        "/items",
        params=params,
        headers={"x-token": "learning-token"},
    )
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["query", field]


@pytest.mark.parametrize("limit", [1, 100])
def test_list_items_accepts_limit_boundaries(limit: int) -> None:
    response = client.get("/items", params={"limit": limit}, headers={"x-token": "learning-token"})
    assert response.status_code == 200
    assert response.json()["limit"] == limit
