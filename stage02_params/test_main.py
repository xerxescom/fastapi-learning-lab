from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_get_user_with_valid_params() -> None:
    response = client.get("/users/42?short=true")
    assert response.status_code == 200
    assert response.json() == {"user_id": 42, "username": "user-42", "short": True}


def test_get_user_with_invalid_user_id_returns_422() -> None:
    response = client.get("/users/not-an-int")
    assert response.status_code == 422


def test_list_items_with_valid_params() -> None:
    response = client.get("/items?limit=20&offset=5&q=notebook&active=false")
    assert response.status_code == 200
    assert response.json() == {
        "limit": 20,
        "offset": 5,
        "q": "notebook",
        "active": False,
    }


def test_list_items_with_invalid_limit_returns_422() -> None:
    response = client.get("/items?limit=0")
    assert response.status_code == 422
