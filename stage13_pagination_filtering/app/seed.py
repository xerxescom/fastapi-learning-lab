"""固定示例数据，便于比较排序和分页结果。"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Item

SAMPLE_ITEMS = (
    {"name": "Keyboard", "price": 99.0, "category": "office", "in_stock": True},
    {"name": "Mouse", "price": 49.0, "category": "accessories", "in_stock": True},
    {"name": "Monitor", "price": 199.0, "category": "office", "in_stock": False},
    {"name": "USB Cable", "price": 19.0, "category": "accessories", "in_stock": True},
    {"name": "Desk Lamp", "price": 49.0, "category": "office", "in_stock": True},
    {"name": "Laptop Stand", "price": 49.0, "category": "office", "in_stock": False},
    {"name": "100% Cotton Case", "price": 29.0, "category": "accessories", "in_stock": True},
    {"name": "Under_score Pad", "price": 19.0, "category": "accessories", "in_stock": False},
)


def seed_items(db: Session) -> bool:
    # 仅向空表写入；重复初始化不重复插入，也不重置已有商品。
    if db.scalar(select(Item.id).limit(1)) is not None:
        return False
    db.add_all(Item(**item) for item in SAMPLE_ITEMS)
    db.commit()
    return True
