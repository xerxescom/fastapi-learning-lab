"""商品 CRUD 接口。"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Item
from app.schemas import ItemCreate, ItemRead

router = APIRouter(prefix="/items", tags=["items"])
DbSession = Annotated[Session, Depends(get_db)]


def find_item(db: Session, item_id: int) -> Item:
    item = db.get(Item, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@router.post("", response_model=ItemRead, status_code=status.HTTP_201_CREATED)
def create_item(body: ItemCreate, db: DbSession) -> Item:
    item = Item(**body.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("", response_model=list[ItemRead])
def list_items(db: DbSession) -> list[Item]:
    return list(db.scalars(select(Item).order_by(Item.id)))


@router.get("/{item_id}", response_model=ItemRead)
def get_item(item_id: int, db: DbSession) -> Item:
    return find_item(db, item_id)


@router.put("/{item_id}", response_model=ItemRead)
def update_item(item_id: int, body: ItemCreate, db: DbSession) -> Item:
    item = find_item(db, item_id)
    for field, value in body.model_dump().items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(item_id: int, db: DbSession) -> Response:
    db.delete(find_item(db, item_id))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
