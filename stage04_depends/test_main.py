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


def test_list_items_with_invalid_limit_returns_422() -> None:
    response = client.get(
        "/items",
        params={"limit": 0},
        headers={"x-token": "learning-token"},
    )
    assert response.status_code == 422
