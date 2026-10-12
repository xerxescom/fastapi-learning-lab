from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator

from app.schemas import CREATE_EXAMPLE, PRODUCT_EXAMPLE
from main import CONFLICT, NOT_FOUND, create_app


@pytest.fixture
def application():
    return create_app()


@pytest.fixture
def client(application) -> Generator[TestClient, None, None]:
    with TestClient(application) as test_client:
        yield test_client


@pytest.fixture
def schema(client):
    return client.get("/openapi.json").json()


def validate_response(schema, path, method, response):
    declared = schema["paths"][path][method]["responses"][str(response.status_code)]
    payload_schema = declared["content"]["application/json"]["schema"]
    # 把 components 放在同一根文档，支持 #/components/schemas/... 的本地引用。
    validation_schema = {**payload_schema, "components": schema["components"]}
    Draft202012Validator.check_schema(validation_schema)
    Draft202012Validator(validation_schema).validate(response.json())


def test_application_metadata(schema):
    assert schema["openapi"].startswith("3.1.")
    assert schema["info"]["title"] == "FastAPI 商品目录文档示例"
    assert schema["info"]["version"] == "1.0.0"
    assert schema["info"]["x-learning-stage"] == 21
    assert "Stage 21" in schema["info"]["summary"]
    assert schema["servers"] == [{"url": "/", "description": "当前服务地址"}]
    assert [tag["name"] for tag in schema["tags"]] == ["products", "legacy", "system"]
    assert all(tag["description"] for tag in schema["tags"])


def test_operation_metadata_and_unique_ids(schema):
    operations = [operation for path in schema["paths"].values() for method, operation in path.items() if method in {"get", "post"}]
    ids = [operation["operationId"] for operation in operations]
    assert set(ids) == {"listProducts", "createProduct", "getProduct", "getLegacyProduct", "healthCheck"}
    assert len(ids) == len(set(ids))
    assert all(operation["summary"] and operation["tags"] for operation in operations)
    assert schema["paths"]["/products"]["post"]["x-learning-topic"] == "response-contract"


def test_query_and_path_documented(schema):
    limit = schema["paths"]["/products"]["get"]["parameters"][0]
    assert limit["name"] == "limit" and limit["in"] == "query"
    assert limit["schema"]["minimum"] == 1 and limit["schema"]["maximum"] == 100
    assert limit["schema"]["default"] == 10
    product_id = schema["paths"]["/products/{product_id}"]["get"]["parameters"][0]
    assert product_id["in"] == "path" and product_id["required"] is True
    assert product_id["schema"]["minimum"] == 1


def test_model_and_request_examples(schema):
    model = schema["components"]["schemas"]["ProductCreate"]
    assert model["examples"] == [CREATE_EXAMPLE]
    assert model["additionalProperties"] is False
    assert model["properties"]["price_cents"]["minimum"] == 0
    assert model["properties"]["price_cents"]["maximum"] == 1_000_000
    assert "分" in model["properties"]["price_cents"]["description"]
    examples = schema["paths"]["/products"]["post"]["requestBody"]["content"]["application/json"]["examples"]
    assert set(examples) == {"mouse", "headphones"}
    assert examples["mouse"]["value"] == CREATE_EXAMPLE


def test_success_and_error_response_models(schema):
    create = schema["paths"]["/products"]["post"]["responses"]
    assert set(create) == {"201", "409", "422"}
    assert create["201"]["content"]["application/json"]["schema"]["$ref"].endswith("/ProductRead")
    assert "Location" in create["201"]["headers"]
    assert create["409"]["content"]["application/json"]["schema"]["$ref"].endswith("/ErrorResponse")
    assert create["422"]["content"]["application/json"]["schema"]["$ref"].endswith("/HTTPValidationError")
    missing = schema["paths"]["/products/{product_id}"]["get"]["responses"]["404"]
    assert missing["content"]["application/json"]["example"] == NOT_FOUND
    assert create["409"]["content"]["application/json"]["example"] == CONFLICT
    assert "internal_cost_cents" not in schema["components"]["schemas"]["ProductRead"]["properties"]


def test_response_filtering_and_contract(client, schema):
    response = client.get("/products/1")
    assert response.json() == PRODUCT_EXAMPLE
    assert "internal_cost_cents" not in response.text
    validate_response(schema, "/products/{product_id}", "get", response)
    listing = client.get("/products")
    assert listing.json() == {"items": [PRODUCT_EXAMPLE], "total": 1}
    validate_response(schema, "/products", "get", listing)


def test_create_location_header_and_contract(client, schema):
    response = client.post("/products", json=CREATE_EXAMPLE)
    assert response.status_code == 201
    assert response.headers["location"] == "/products/2"
    assert client.get(response.headers["location"]).json() == response.json()
    validate_response(schema, "/products", "post", response)


@pytest.mark.parametrize("path", ["/products/999", "/legacy/products/999"])
def test_missing_error_matches_documentation(client, schema, path):
    response = client.get(path)
    assert response.status_code == 404 and response.json() == NOT_FOUND
    template = "/legacy/products/{product_id}" if path.startswith("/legacy") else "/products/{product_id}"
    validate_response(schema, template, "get", response)


def test_conflict_matches_documentation(client, schema):
    response = client.post("/products", json={key: value for key, value in PRODUCT_EXAMPLE.items() if key != "id"})
    assert response.status_code == 409 and response.json() == CONFLICT
    validate_response(schema, "/products", "post", response)


@pytest.mark.parametrize("body", [
    {}, {**CREATE_EXAMPLE, "sku": "invalid"}, {**CREATE_EXAMPLE, "name": " "},
    {**CREATE_EXAMPLE, "price_cents": -1}, {**CREATE_EXAMPLE, "price_cents": 1_000_001},
    {**CREATE_EXAMPLE, "price_cents": 1.5}, {**CREATE_EXAMPLE, "price_cents": True},
    {**CREATE_EXAMPLE, "internal_cost_cents": 0},
])
def test_validation_error_matches_documentation(client, schema, body):
    response = client.post("/products", json=body)
    assert response.status_code == 422
    validate_response(schema, "/products", "post", response)
    assert client.get("/products").json()["total"] == 1


@pytest.mark.parametrize("path,template", [("/products/0", "/products/{product_id}"), ("/products/not-int", "/products/{product_id}"), ("/products?limit=0", "/products"), ("/products?limit=101", "/products")])
def test_parameter_validation_matches_documentation(client, schema, path, template):
    response = client.get(path)
    assert response.status_code == 422
    validate_response(schema, template, "get", response)


def test_deprecated_endpoint_remains_callable(client, schema):
    assert schema["paths"]["/legacy/products/{product_id}"]["get"]["deprecated"] is True
    assert client.get("/legacy/products/1").json() == PRODUCT_EXAMPLE


def test_hidden_route_is_not_access_control(client, schema):
    assert "/internal/ping" not in schema["paths"]
    assert client.get("/internal/ping").json() == {"status": "ok"}


@pytest.mark.parametrize("path", ["/docs", "/redoc"])
def test_documentation_pages(client, path):
    response = client.get(path)
    assert response.status_code == 200
    assert "/openapi.json" in response.text


def test_swagger_options(client):
    response = client.get("/docs")
    assert '"displayRequestDuration": true' in response.text
    assert '"defaultModelsExpandDepth": 1' in response.text


def test_openapi_cached_per_application(application):
    assert application.openapi_schema is None
    first = application.openapi()
    assert application.openapi() is first
    other = create_app()
    assert other.openapi() is not first
    first["info"]["x-test"] = True
    assert "x-test" not in other.openapi()["info"]


def test_schema_cache_can_be_rebuilt(application):
    first = application.openapi()
    application.openapi_schema = None
    second = application.openapi()
    assert second is not first and second == first


def test_documented_request_examples_work_on_fresh_apps(schema):
    examples = schema["paths"]["/products"]["post"]["requestBody"]["content"]["application/json"]["examples"]
    for example in examples.values():
        with TestClient(create_app()) as client:
            response = client.post("/products", json=example["value"])
            assert response.status_code == 201
            validate_response(schema, "/products", "post", response)


def test_health_response_matches_schema(client, schema):
    response = client.get("/health")
    assert response.json() == {"status": "ok"}
    validate_response(schema, "/health", "get", response)
