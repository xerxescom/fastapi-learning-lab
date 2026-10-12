"""Stage 23：yield 前启动，yield 后关闭；不在模块导入时创建连接。"""

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import Annotated
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Path, Request
from fastapi.responses import JSONResponse

from app.resources import CatalogStore, Product, Resources, load_snapshot, open_catalog


def get_resources(request: Request) -> Resources:
    resources = getattr(request.app.state, "resources", None)
    if resources is None or resources.store.closed:
        raise HTTPException(status_code=503, detail="Application resources unavailable")
    return resources


def create_app(
    *,
    store_factory: Callable[[], AbstractAsyncContextManager[CatalogStore]] = open_catalog,
    snapshot_loader: Callable[[CatalogStore], tuple[Product, ...]] = load_snapshot,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(application: FastAPI):
        # 每个生命周期创建自己的资源；快照加载失败时上下文管理器仍会关闭连接。
        async with store_factory() as store:
            snapshot = snapshot_loader(store)
            application.state.resources = Resources(store, snapshot, uuid4().hex)
            try:
                yield
            finally:
                # 先撤销对共享资源的引用，再由上下文管理器关闭底层连接。
                del application.state.resources

    application = FastAPI(title="Stage 23：应用生命周期与资源管理", lifespan=lifespan)

    @application.get("/health/live", tags=["health"])
    def live():
        return {"status": "alive"}

    @application.get("/health/ready", tags=["health"], responses={503: {"description": "共享资源未就绪"}})
    def ready(request: Request):
        resources = getattr(request.app.state, "resources", None)
        if resources is None or resources.store.closed:
            return JSONResponse(status_code=503, content={"status": "not_ready"})
        return {"status": "ready"}

    @application.get("/runtime", tags=["demo"])
    def runtime(resources: Annotated[Resources, Depends(get_resources)]):
        return {
            "instance_id": resources.instance_id,
            "cached_products": len(resources.snapshot),
            "store_closed": resources.store.closed,
        }

    @application.get("/products", response_model=list[Product], tags=["products"])
    def list_products(resources: Annotated[Resources, Depends(get_resources)]):
        return resources.snapshot

    @application.get("/products/{product_id}", response_model=Product, tags=["products"])
    def read_product(
        product_id: Annotated[int, Path(ge=1)],
        resources: Annotated[Resources, Depends(get_resources)],
    ):
        product = resources.store.get_product(product_id)
        if product is None:
            raise HTTPException(status_code=404, detail="Product not found")
        return product

    return application


app = create_app()
