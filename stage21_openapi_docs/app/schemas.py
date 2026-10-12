from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

PRODUCT_EXAMPLE = {"id": 1, "sku": "KEY-001", "name": "Keyboard", "price_cents": 9900}
CREATE_EXAMPLE = {"sku": "MOU-002", "name": "Mouse", "price_cents": 4900}


class ProductCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", json_schema_extra={"examples": [CREATE_EXAMPLE]})

    sku: Annotated[str, StringConstraints(pattern=r"^[A-Z]{3}-[0-9]{3}$")] = Field(description="唯一商品编码，三位大写字母加三位数字，例如 MOU-002")
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)] = Field(description="商品名称，去除首尾空白")
    price_cents: int = Field(strict=True, ge=0, le=1_000_000, description="价格，单位为分；必须是整数")


class ProductRead(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [PRODUCT_EXAMPLE]})

    id: int = Field(ge=1, description="服务端生成的商品 ID")
    sku: str
    name: str
    price_cents: int = Field(ge=0, description="价格，单位为分")


class ProductList(BaseModel):
    items: list[ProductRead]
    total: int = Field(ge=0, description="目录总条数，不是当前返回条数")


class ErrorDetail(BaseModel):
    code: str = Field(description="可供客户端判断的业务错误码")
    message: str = Field(description="错误的可读说明")


class ErrorResponse(BaseModel):
    detail: ErrorDetail


class HealthResponse(BaseModel):
    status: str
