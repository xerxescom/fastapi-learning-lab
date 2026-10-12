"""在 SQL 中完成过滤、计数、稳定排序和分页。"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Item
from app.schemas import FilterParams


def query_items(db: Session, params: FilterParams, limit: int, offset: int) -> tuple[list[Item], int]:
    conditions = []
    if params.q is not None:
        # 按字面子串搜索，转义用户输入中的 % 和 _，不当作 LIKE 通配符。
        conditions.append(Item.name.icontains(params.q, autoescape=True))
    if params.category is not None:
        conditions.append(Item.category == params.category)
    if params.in_stock is not None:
        conditions.append(Item.in_stock == params.in_stock)
    if params.min_price is not None:
        conditions.append(Item.price >= params.min_price)
    if params.max_price is not None:
        conditions.append(Item.price <= params.max_price)

    total = db.execute(select(func.count()).select_from(Item).where(*conditions)).scalar_one()
    columns = {"id": Item.id, "name": Item.name, "price": Item.price}
    column = columns[params.sort_by]
    ordering = [column.desc() if params.order == "desc" else column.asc()]
    if params.sort_by != "id":
        # 非唯一字段排序时用 ID 升序打破平局，避免跨页结果顺序不确定。
        ordering.append(Item.id.asc())
    statement = select(Item).where(*conditions).order_by(*ordering).limit(limit).offset(offset)
    return list(db.scalars(statement)), total
