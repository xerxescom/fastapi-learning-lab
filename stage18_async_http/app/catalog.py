"""隔离外部协议与错误，不把上游错误正文透传给客户端。"""

import asyncio

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

MAX_RESPONSE_BYTES = 64 * 1024


class Product(BaseModel):
    model_config = ConfigDict(strict=True)

    id: int = Field(ge=1)
    name: str = Field(min_length=1, max_length=100)
    price: float = Field(ge=0, allow_inf_nan=False)


class UpstreamError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


class CatalogClient:
    def __init__(self, client: httpx.AsyncClient, deadline: float):
        self.client = client
        self.deadline = deadline

    async def get_product(self, product_id: int) -> Product:
        try:
            # HTTPX 分阶段超时之外，再限制整个异步调用的等待预算。
            async with asyncio.timeout(self.deadline):
                async with self.client.stream("GET", f"products/{product_id}") as response:
                    if response.status_code == 404:
                        raise UpstreamError(404, "Product not found")
                    if response.status_code != 200:
                        raise UpstreamError(502, "Upstream service returned an unexpected status")
                    content_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
                    if content_type != "application/json":
                        raise UpstreamError(502, "Invalid upstream response")
                    data = bytearray()
                    async for chunk in response.aiter_bytes(chunk_size=8192):
                        data.extend(chunk)
                        if len(data) > MAX_RESPONSE_BYTES:
                            raise UpstreamError(502, "Upstream response is too large")
                product = Product.model_validate_json(data)
                if product.id != product_id:
                    raise UpstreamError(502, "Invalid upstream response")
                return product
        except httpx.PoolTimeout:
            raise UpstreamError(503, "Upstream connection pool is busy") from None
        except (httpx.TimeoutException, TimeoutError):
            raise UpstreamError(504, "Upstream request timed out") from None
        except httpx.RequestError:
            raise UpstreamError(502, "Unable to reach upstream service") from None
        except ValidationError:
            raise UpstreamError(502, "Invalid upstream response") from None
