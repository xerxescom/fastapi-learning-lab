"""显式响应模型，而不是用中间件强行包装所有响应。"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from app.schemas import ErrorResponse, ItemRead, QuoteRead, QuoteRequest, SuccessResponse
from app.services import ItemService

router = APIRouter(
    responses={
        404: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    }
)


def get_item_service(request: Request) -> ItemService:
    return request.app.state.item_service


Service = Annotated[ItemService, Depends(get_item_service)]


@router.get("/items", response_model=SuccessResponse[list[ItemRead]], tags=["items"])
def list_items(service: Service) -> SuccessResponse[list[ItemRead]]:
    return SuccessResponse(data=service.list_all())


@router.get("/items/{item_id}", response_model=SuccessResponse[ItemRead], tags=["items"])
def get_item(item_id: int, service: Service) -> SuccessResponse[ItemRead]:
    return SuccessResponse(data=service.get(item_id))


@router.post(
    "/items/{item_id}/quote",
    response_model=SuccessResponse[QuoteRead],
    responses={409: {"model": ErrorResponse}},
    tags=["items"],
)
def quote_item(item_id: int, body: QuoteRequest, service: Service) -> SuccessResponse[QuoteRead]:
    return SuccessResponse(message="Quote calculated", data=service.quote(item_id, body.quantity))


@router.get("/examples/unauthorized", responses={401: {"model": ErrorResponse}}, tags=["examples"])
def unauthorized_example() -> None:
    raise HTTPException(
        status_code=401, detail="Authentication required", headers={"WWW-Authenticate": "Bearer"}
    )


@router.get("/examples/server-error", tags=["examples"])
def server_error_example() -> None:
    # 仅为学习触发未知异常；实际业务项目不应提供此演示接口。
    raise RuntimeError("simulated internal failure: demo-private-detail")
