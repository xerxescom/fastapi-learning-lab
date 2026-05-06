from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_list_reports_with_valid_token_and_query() -> None:
    response = client.get(
        "/reports?limit=2&offset=1",
        headers={"X-Token": "learning-lab-token"},
    )
    assert response.status_code == 200
    assert response.json() == {
        "items": ["report-a", "report-b", "report-c"],
        "limit": 2,
        "offset": 1,
        "count": 3,
    }


def test_list_reports_without_token_returns_401() -> None:
    response = client.get("/reports")
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid X-Token"}


def test_list_reports_with_invalid_token_returns_401() -> None:
    response = client.get("/reports", headers={"X-Token": "bad-token"})
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid X-Token"}


def test_list_reports_with_invalid_query_returns_422() -> None:
    response = client.get(
        "/reports?limit=0",
        headers={"X-Token": "learning-lab-token"},
    )
    assert response.status_code == 422
