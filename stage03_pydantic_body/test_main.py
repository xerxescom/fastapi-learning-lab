from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_create_item_with_valid_body() -> None:
    payload = {
        "name": "机械键盘",
        "price": 399.0,
        "in_stock": False,
        "description": "87键，红轴",
    }
    response = client.post("/items", json=payload)
    assert response.status_code == 200
    assert response.json() == {
        "id": 1,
        "name": "机械键盘",
        "price": 399.0,
        "in_stock": False,
        "description": "87键，红轴",
    }


def test_create_item_with_defaults() -> None:
    payload = {"name": "鼠标", "price": 99.9}
    response = client.post("/items", json=payload)
    assert response.status_code == 200
    assert response.json() == {
        "id": 1,
        "name": "鼠标",
        "price": 99.9,
        "in_stock": True,
        "description": None,
    }


def test_create_item_with_invalid_body_returns_422() -> None:
    payload = {"name": "", "price": -1}
    response = client.post("/items", json=payload)
    assert response.status_code == 422


def test_response_model_filters_internal_fields() -> None:
    payload = {"name": "显示器", "price": 1299}
    response = client.post("/items", json=payload)
    assert response.status_code == 200
    assert "internal_note" not in response.json()
