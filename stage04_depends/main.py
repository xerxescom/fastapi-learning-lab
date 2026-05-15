"""阶段 04：依赖注入（Depends）示例。"""

from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(
    title="FastAPI 学习实验室 - 阶段 04",
    version="0.1.0",
    description="演示公共查询参数依赖与基于 Header Token 的简单鉴权。",
)


class CommonQueryParams(BaseModel):
    """公共查询参数依赖模型。"""

    q: str | None = Field(default=None, description="关键词，可选")
    limit: int = Field(default=10, ge=1, le=100, description="返回数量")
    offset: int = Field(default=0, ge=0, description="偏移量")


def get_common_query_params(
    q: str | None = None,
    limit: int = 10,
    offset: int = 0,
) -> CommonQueryParams:
    """提取并复用查询参数。"""
    return CommonQueryParams(q=q, limit=limit, offset=offset)


def verify_token(x_token: Annotated[str | None, Header()] = None) -> str:
    """通过 Header 中的 x-token 做最小化鉴权。"""
    if x_token != "learning-token":
        raise HTTPException(status_code=401, detail="Invalid or missing token")
    return x_token


@app.get("/items")
def list_items(
    params: Annotated[CommonQueryParams, Depends(get_common_query_params)],
    _: Annotated[str, Depends(verify_token)],
) -> dict[str, int | str | None]:
    """示例接口：复用公共查询参数 + 鉴权依赖。"""
    return {
        "message": "ok",
        "q": params.q,
        "limit": params.limit,
        "offset": params.offset,
    }
