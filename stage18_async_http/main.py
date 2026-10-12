"""Stage 18：复用 AsyncClient，等待外部 I/O 时让出事件循环。"""

from contextlib import asynccontextmanager
from typing import Annotated

import httpx
from fastapi import Depends, FastAPI, Path, Request
from fastapi.responses import JSONResponse

from app.catalog import CatalogClient, Product, UpstreamError
from app.config import Settings


def get_catalog(request: Request) -> CatalogClient:
    return request.app.state.catalog


def create_app(settings: Settings | None = None, *, transport: httpx.AsyncBaseTransport | None = None) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        async with httpx.AsyncClient(
            base_url=str(settings.upstream_base_url),
            timeout=httpx.Timeout(settings.http_timeout_seconds),
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
            follow_redirects=False, trust_env=False, transport=transport,
            headers={"Accept": "application/json"},
        ) as client:
            application.state.http_client = client
            application.state.catalog = CatalogClient(client, settings.request_deadline_seconds)
            try:
                yield
            finally:
                del application.state.catalog

    application = FastAPI(title="Stage 18：异步接口与外部 HTTP 调用", lifespan=lifespan)

    @application.exception_handler(UpstreamError)
    async def upstream_error(request: Request, exc: UpstreamError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @application.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @application.get("/products/{product_id}", response_model=Product)
    async def product(
        product_id: Annotated[int, Path(ge=1, le=1_000_000)],
        catalog: Annotated[CatalogClient, Depends(get_catalog)],
    ) -> Product:
        return await catalog.get_product(product_id)

    return application


app = create_app()
