"""只用于本地演示的上游服务，无外部网络调用。"""

import asyncio

from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI(title="Stage 18 本地模拟上游")


@app.get("/products/{product_id}")
async def product(product_id: int):
    if product_id == 1:
        return {"id": 1, "name": "Keyboard", "price": 99.0, "internal_note": "not exposed"}
    if product_id == 2:
        return {"id": 2, "name": "Broken response", "price": "not-a-number"}
    if product_id == 3:
        return JSONResponse(status_code=503, content={"internal_error": "demo upstream failure"})
    if product_id == 4:
        await asyncio.sleep(3)
        return {"id": 4, "name": "Slow product", "price": 10.0}
    return JSONResponse(status_code=404, content={"detail": "missing"})
