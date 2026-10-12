"""Stage 21：自动文档与实际 HTTP 行为保持一致。"""

from threading import Lock
from typing import Annotated

from fastapi import Body, FastAPI, Path, Query, Request, Response
from fastapi.responses import JSONResponse

from app.openapi import install_openapi
from app.schemas import CREATE_EXAMPLE, PRODUCT_EXAMPLE, ErrorResponse, HealthResponse, ProductCreate, ProductList, ProductRead

NOT_FOUND = {"detail": {"code": "PRODUCT_NOT_FOUND", "message": "Product not found"}}
CONFLICT = {"detail": {"code": "SKU_CONFLICT", "message": "SKU already exists"}}


class ProductError(Exception):
    def __init__(self, status_code: int, body: dict):
        self.status_code = status_code
        self.body = ErrorResponse.model_validate(body)


def create_app() -> FastAPI:
    application = FastAPI(
        title="FastAPI 商品目录文档示例", version="1.0.0",
        summary="Stage 21：OpenAPI 文档与接口元数据",
        description="教学用内存商品目录。价格单位为分；重启后恢复初始数据。",
        openapi_tags=[
            {"name": "products", "description": "商品创建与查询，使用公开响应模型。"},
            {"name": "legacy", "description": "兼容旧客户端的弃用入口。"},
            {"name": "system", "description": "基础健康检查。"},
        ],
        servers=[{"url": "/", "description": "当前服务地址"}],
        swagger_ui_parameters={"displayRequestDuration": True, "defaultModelsExpandDepth": 1},
    )
    products = {1: {**PRODUCT_EXAMPLE, "internal_cost_cents": 5000}}
    lock = Lock()

    @application.exception_handler(ProductError)
    async def product_error(request: Request, exc: ProductError) -> JSONResponse:
        # responses 只声明文档；错误返回仍需显式构造并校验。
        return JSONResponse(status_code=exc.status_code, content=exc.body.model_dump())

    @application.get(
        "/products", tags=["products"], operation_id="listProducts", response_model=ProductList,
        summary="查询商品列表", description="按 ID 升序返回最多 limit 条，total 表示目录总数。",
    )
    def list_products(limit: Annotated[int, Query(ge=1, le=100, description="最多返回条数", examples=[10])] = 10):
        with lock:
            return {"items": list(products.values())[:limit], "total": len(products)}

    @application.post(
        "/products", tags=["products"], operation_id="createProduct", status_code=201,
        response_model=ProductRead, summary="创建商品", description="SKU 必须唯一；内部成本不会出现在公开响应。",
        responses={
            201: {"description": "商品创建成功", "headers": {"Location": {"description": "新商品的相对路径", "schema": {"type": "string"}}}, "content": {"application/json": {"example": {"id": 2, **CREATE_EXAMPLE}}}},
            409: {"model": ErrorResponse, "description": "SKU 已存在", "content": {"application/json": {"example": CONFLICT}}},
        },
        openapi_extra={"x-learning-topic": "response-contract"},
    )
    def create_product(
        body: Annotated[ProductCreate, Body(openapi_examples={
            "mouse": {"summary": "鼠标", "value": CREATE_EXAMPLE},
            "headphones": {"summary": "耳机", "value": {"sku": "HDP-003", "name": "Headphones", "price_cents": 12900}},
        })],
        response: Response,
    ):
        with lock:
            if any(product["sku"] == body.sku for product in products.values()):
                raise ProductError(409, CONFLICT)
            product_id = max(products) + 1
            product = {"id": product_id, **body.model_dump(), "internal_cost_cents": 0}
            products[product_id] = product
        response.headers["Location"] = f"/products/{product_id}"
        return product

    def find_product(product_id: int):
        with lock:
            if product_id not in products:
                raise ProductError(404, NOT_FOUND)
            return products[product_id].copy()

    missing_response = {404: {"model": ErrorResponse, "description": "商品不存在", "content": {"application/json": {"example": NOT_FOUND}}}}

    @application.get(
        "/products/{product_id}", tags=["products"], operation_id="getProduct", response_model=ProductRead,
        summary="查询单个商品", description="返回公开字段；不存在时返回 PRODUCT_NOT_FOUND。", responses=missing_response,
    )
    def read_product(product_id: Annotated[int, Path(ge=1, description="商品 ID", examples=[1])]):
        return find_product(product_id)

    @application.get(
        "/legacy/products/{product_id}", tags=["legacy"], operation_id="getLegacyProduct",
        response_model=ProductRead, responses=missing_response, deprecated=True,
        summary="旧版商品查询", description="仍可访问，但新客户端应改用 /products/{product_id}。",
    )
    def legacy_product(product_id: Annotated[int, Path(ge=1)]):
        return find_product(product_id)

    @application.get("/health", tags=["system"], operation_id="healthCheck", response_model=HealthResponse, summary="健康检查")
    def health():
        return {"status": "ok"}

    @application.get("/internal/ping", include_in_schema=False)
    def internal_ping():
        # 隐藏文档不是访问控制；此路径依然可以直接请求。
        return {"status": "ok"}

    install_openapi(application)
    return application


app = create_app()
