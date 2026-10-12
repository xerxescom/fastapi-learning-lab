"""用两种 HTTP 接口展示相同查询的分页表达。"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import OffsetParams, OffsetResponse, PageParams, PageResponse
from app.services import query_items

router = APIRouter(prefix="/items", tags=["items"])
DbSession = Annotated[Session, Depends(get_db)]


@router.get("", response_model=OffsetResponse)
def list_items(params: Annotated[OffsetParams, Query()], db: DbSession) -> OffsetResponse:
    items, total = query_items(db, params, params.limit, params.offset)
    return OffsetResponse(items=items, total=total, limit=params.limit, offset=params.offset)


@router.get("/pages", response_model=PageResponse)
def list_item_pages(params: Annotated[PageParams, Query()], db: DbSession) -> PageResponse:
    offset = (params.page - 1) * params.page_size
    items, total = query_items(db, params, params.page_size, offset)
    return PageResponse(
        items=items,
        total=total,
        page=params.page,
        page_size=params.page_size,
        pages=(total + params.page_size - 1) // params.page_size,
    )
