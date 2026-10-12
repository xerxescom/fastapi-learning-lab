"""只读内存商品服务，报价不扣减库存或创建订单。"""

from app.exceptions import ItemNotFoundError, OutOfStockError
from app.schemas import ItemRead, QuoteRead


class ItemService:
    def __init__(self) -> None:
        self._items = {
            1: ItemRead(id=1, name="Keyboard", price=99.0, stock=5),
            2: ItemRead(id=2, name="Mouse", price=49.0, stock=0),
        }

    def list_all(self) -> list[ItemRead]:
        return list(self._items.values())

    def get(self, item_id: int) -> ItemRead:
        item = self._items.get(item_id)
        if item is None:
            raise ItemNotFoundError()
        return item

    def quote(self, item_id: int, quantity: int) -> QuoteRead:
        item = self.get(item_id)
        if quantity > item.stock:
            raise OutOfStockError()
        return QuoteRead(item_id=item_id, quantity=quantity, total=item.price * quantity)
