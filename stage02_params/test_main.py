from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_get_user_success() -> None:
    response = client.get("/users/123")
    assert response.status_code == 200
    assert response.json() == {"user_id": 123}


def test_get_user_invalid_type() -> None:
    response = client.get("/users/not-int")
    assert response.status_code == 422


def test_list_items_default_params() -> None:
    response = client.get("/items")
    assert response.status_code == 200
    assert response.json() == {"limit": 10, "offset": 0, "is_active": True}


def test_list_items_with_query_params() -> None:
    response = client.get("/items?limit=20&offset=5&is_active=false")
    assert response.status_code == 200
    assert response.json() == {"limit": 20, "offset": 5, "is_active": False}


def test_list_items_invalid_limit() -> None:
    response = client.get("/items?limit=0")
    assert response.status_code == 422
