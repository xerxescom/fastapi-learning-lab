import logging

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.schemas import ItemRead, SuccessResponse
from main import create_app


@pytest.fixture
def client():
    # 未处理异常仍会被测试客户端重新抛出，关闭此行为才能检查真实的 500 响应。
    with TestClient(create_app(), raise_server_exceptions=False) as test_client:
        yield test_client


def assert_error(response, status: int, code: int, message: str) -> None:
    assert response.status_code == status
    assert response.headers["content-type"] == "application/json"
    assert response.json() == {"code": code, "message": message, "data": None}


def test_successful_list_and_item(client: TestClient) -> None:
    response = client.get("/items")
    assert response.status_code == 200
    assert response.json() == {
        "code": 0,
        "message": "ok",
        "data": [
            {"id": 1, "name": "Keyboard", "price": 99.0, "stock": 5},
            {"id": 2, "name": "Mouse", "price": 49.0, "stock": 0},
        ],
    }
    item = client.get("/items/1")
    assert item.status_code == 200
    assert item.json() == {"code": 0, "message": "ok", "data": response.json()["data"][0]}


def test_quote_does_not_change_inventory(client: TestClient) -> None:
    for _ in range(2):
        response = client.post("/items/1/quote", json={"quantity": 5})
        assert response.status_code == 200
        assert response.json() == {
            "code": 0, "message": "Quote calculated", "data": {"item_id": 1, "quantity": 5, "total": 495.0}
        }
    assert client.get("/items/1").json()["data"]["stock"] == 5


@pytest.mark.parametrize("method,path,kwargs", [
    ("GET", "/items/999", {}),
    ("POST", "/items/999/quote", {"json": {"quantity": 1}}),
])
def test_business_not_found(client: TestClient, method: str, path: str, kwargs: dict) -> None:
    assert_error(client.request(method, path, **kwargs), 404, 40401, "Item not found")


@pytest.mark.parametrize("item_id,quantity", [(1, 6), (2, 1)])
def test_out_of_stock(client: TestClient, item_id: int, quantity: int) -> None:
    response = client.post(f"/items/{item_id}/quote", json={"quantity": quantity})
    assert_error(response, 409, 40901, "Not enough stock")


def test_framework_404(client: TestClient) -> None:
    assert_error(client.get("/missing-route"), 404, 40400, "Not Found")


def test_method_not_allowed_preserves_allow_header(client: TestClient) -> None:
    response = client.delete("/items")
    assert_error(response, 405, 40500, "Method Not Allowed")
    assert response.headers["allow"] == "GET"


def test_401_preserves_authentication_challenge(client: TestClient) -> None:
    response = client.get("/examples/unauthorized")
    assert_error(response, 401, 40100, "Authentication required")
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize("path,body,location", [
    ("/items/1/quote", {"quantity": 0}, ["body", "quantity"]),
    ("/items/1/quote", {"quantity": 11}, ["body", "quantity"]),
    ("/items/1/quote", {"quantity": "invalid"}, ["body", "quantity"]),
    ("/items/1/quote", {}, ["body", "quantity"]),
    ("/items/not-an-id/quote", {"quantity": 1}, ["path", "item_id"]),
])
def test_validation_errors(client: TestClient, path: str, body: dict, location: list) -> None:
    response = client.post(path, json=body)
    assert response.status_code == 422
    result = response.json()
    assert set(result) == {"code", "message", "data"}
    assert result["code"] == 42200
    assert result["message"] == "Request validation failed"
    issue = result["data"]["errors"][0]
    assert issue["loc"] == location
    assert set(issue) == {"loc", "message", "type"}


def test_validation_does_not_echo_private_input(client: TestClient) -> None:
    secret = "private-password-12345"
    response = client.post("/items/1/quote", json={"quantity": 1, "password": secret})
    assert response.status_code == 422
    assert secret not in response.text
    assert response.json()["data"]["errors"][0]["loc"] == ["body", "password"]


def test_malformed_json(client: TestClient) -> None:
    response = client.post(
        "/items/1/quote", content='{"quantity":', headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 422
    assert response.json()["code"] == 42200
    assert response.json()["data"]["errors"][0]["type"] == "json_invalid"


def test_multiple_validation_errors(client: TestClient) -> None:
    response = client.post("/items/no-id/quote", json={"quantity": 0})
    assert response.status_code == 422
    locations = [issue["loc"] for issue in response.json()["data"]["errors"]]
    assert ["path", "item_id"] in locations
    assert ["body", "quantity"] in locations


def test_unhandled_error_is_redacted_and_logged(client: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.ERROR, logger="app.handlers"):
        response = client.get("/examples/server-error")
    assert_error(response, 500, 50000, "Internal server error")
    assert "demo-private-detail" not in response.text
    assert "RuntimeError" not in response.text
    assert "Traceback" not in response.text
    record = next(record for record in caplog.records if record.message == "Unhandled server error")
    assert record.exc_info[0] is RuntimeError


def test_response_validation_is_server_error() -> None:
    app = create_app()

    @app.get("/broken-response", response_model=SuccessResponse[ItemRead])
    def broken_response():
        return {"data": {"name": "missing required fields"}}

    with TestClient(app, raise_server_exceptions=False) as client:
        assert_error(client.get("/broken-response"), 500, 50000, "Internal server error")


@pytest.mark.parametrize("exception_class", [HTTPException, StarletteHTTPException])
def test_http_exception_types_use_same_handler(exception_class) -> None:
    app = create_app()

    @app.get("/denied")
    def denied():
        raise exception_class(status_code=403, detail="Access denied")

    with TestClient(app) as client:
        assert_error(client.get("/denied"), 403, 40300, "Access denied")


def test_http_5xx_redacts_details_and_preserves_headers() -> None:
    app = create_app()

    @app.get("/unavailable")
    def unavailable():
        raise HTTPException(status_code=503, detail="private database address", headers={"Retry-After": "60"})

    with TestClient(app) as client:
        response = client.get("/unavailable")
    assert_error(response, 503, 50300, "Internal server error")
    assert response.headers["retry-after"] == "60"


def test_structured_http_detail_uses_safe_message() -> None:
    app = create_app()

    @app.get("/bad-request")
    def bad_request():
        raise HTTPException(status_code=400, detail={"private": "not part of the public contract"})

    with TestClient(app) as client:
        assert_error(client.get("/bad-request"), 400, 40000, "Bad Request")


def test_documentation_responses_are_not_wrapped(client: TestClient) -> None:
    assert client.get("/docs").headers["content-type"].startswith("text/html")
    schema = client.get("/openapi.json").json()
    assert "openapi" in schema and "code" not in schema
    quote_responses = schema["paths"]["/items/{item_id}/quote"]["post"]["responses"]
    assert quote_responses["422"]["content"]["application/json"]["schema"] == {"$ref": "#/components/schemas/ErrorResponse"}
    assert quote_responses["409"]["content"]["application/json"]["schema"] == {"$ref": "#/components/schemas/ErrorResponse"}


def test_redirect_keeps_http_semantics(client: TestClient) -> None:
    response = client.get("/items/", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"].endswith("/items")
