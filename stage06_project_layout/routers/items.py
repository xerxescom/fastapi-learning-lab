"""商品相关路由。"""

from fastapi import APIRouter, status

from schemas.item import ItemCreate, ItemListResponse, ItemRead, ItemResponse
from services.item_service import item_service

router = APIRouter(prefix="/items", tags=["items"])


@router.post("", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
def create_item(item: ItemCreate) -> ItemResponse:
    created = item_service.create(item)
    return ItemResponse(message="Item created", data=created)


@router.get("", response_model=ItemListResponse)
def list_items() -> ItemListResponse:
    return ItemListResponse(data=item_service.list_all())


@router.get("/{item_id}", response_model=ItemResponse)
def get_item(item_id: int) -> ItemResponse:
    return ItemResponse(data=item_service.get(item_id))


@router.put("/{item_id}", response_model=ItemResponse)
def update_item(item_id: int, item: ItemCreate) -> ItemResponse:
    updated = item_service.update(item_id, item)
    return ItemResponse(message="Item updated", data=updated)


@router.delete("/{item_id}", status_code=status.HTTP_200_OK)
def delete_item(item_id: int) -> dict[str, int | str | None]:
    item_service.delete(item_id)
    return {"code": 0, "message": "Item deleted", "data": None}
