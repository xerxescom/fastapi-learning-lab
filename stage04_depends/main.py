"""阶段 04：依赖注入（Depends）示例。"""

from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Query

app = FastAPI(
    title="FastAPI 学习实验室 - 阶段 04",
    version="0.1.0",
    description="演示公共查询参数依赖与简单 Header Token 鉴权依赖。",
)


def common_pagination(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> dict[str, int]:
    """公共查询参数依赖：集中管理分页参数。"""
    return {"limit": limit, "offset": offset}


def verify_token(x_token: Annotated[str | None, Header()] = None) -> str:
    """简单鉴权依赖：检查 Header Token。"""
    if x_token != "learning-lab-token":
        raise HTTPException(status_code=401, detail="Invalid X-Token")
    return x_token


@app.get("/reports")
def list_reports(
    pagination: Annotated[dict[str, int], Depends(common_pagination)],
    _: Annotated[str, Depends(verify_token)],
) -> dict[str, int | list[str]]:
    """需要通过 token 鉴权后才能访问，并复用公共分页参数。"""
    data = ["report-a", "report-b", "report-c"]
    return {
        "items": data,
        "limit": pagination["limit"],
        "offset": pagination["offset"],
        "count": len(data),
    }
