"""商品业务逻辑。

本阶段先使用内存字典保存数据，重点放在项目分层，而不是数据库细节。
"""

from schemas.item import ItemCreate, ItemRead


class ItemNotFoundError(Exception):
    """商品不存在。"""


class ItemService:
    def __init__(self) -> None:
        self._items: dict[int, ItemRead] = {}
        self._next_id = 1

    def reset(self) -> None:
        """测试时重置内存数据。"""
        self._items.clear()
        self._next_id = 1

    def create(self, item: ItemCreate) -> ItemRead:
        created = ItemRead(id=self._next_id, **item.model_dump())
        self._items[created.id] = created
        self._next_id += 1
        return created

    def list_all(self) -> list[ItemRead]:
        return list(self._items.values())

    def get(self, item_id: int) -> ItemRead:
        item = self._items.get(item_id)
        if item is None:
            raise ItemNotFoundError("Item not found")
        return item

    def update(self, item_id: int, item: ItemCreate) -> ItemRead:
        self.get(item_id)
        updated = ItemRead(id=item_id, **item.model_dump())
        self._items[item_id] = updated
        return updated

    def delete(self, item_id: int) -> None:
        self.get(item_id)
        del self._items[item_id]


item_service = ItemService()
