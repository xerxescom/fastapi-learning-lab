import pytest
from fastapi.testclient import TestClient

from main import app
from services.item_service import item_service

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_items() -> None:
    item_service.reset()


def test_root() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {
        "code": 0,
        "message": "Stage 06 project layout",
        "data": None,
    }


def test_create_list_get_update_delete_item() -> None:
    create_resp = client.post(
        "/items",
        json={"name": "机械键盘", "price": 399.0, "in_stock": True},
    )
    assert create_resp.status_code == 201
    created = create_resp.json()
    assert created["code"] == 0
    assert created["message"] == "Item created"
    assert created["data"]["id"] == 1

    list_resp = client.get("/items")
    assert list_resp.status_code == 200
    assert list_resp.json()["data"] == [created["data"]]

    get_resp = client.get("/items/1")
    assert get_resp.status_code == 200
    assert get_resp.json()["data"]["name"] == "机械键盘"

    update_resp = client.put(
        "/items/1",
        json={"name": "办公键盘", "price": 299.0, "in_stock": False},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["message"] == "Item updated"
    assert update_resp.json()["data"]["name"] == "办公键盘"

    delete_resp = client.delete("/items/1")
    assert delete_resp.status_code == 200
    assert delete_resp.json() == {"code": 0, "message": "Item deleted", "data": None}


def test_get_missing_item_uses_unified_error_response() -> None:
    response = client.get("/items/999")
    assert response.status_code == 404
    assert response.json() == {"code": 404, "message": "Item not found", "data": None}


def test_invalid_request_body_returns_422() -> None:
    response = client.post("/items", json={"name": "", "price": -1})
    assert response.status_code == 422
