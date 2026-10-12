"""连接的创建与关闭属于生命周期，查询借用连接而不关闭它。"""

import sqlite3
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from threading import Lock

from pydantic import BaseModel, ConfigDict, Field


class Product(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: int = Field(ge=1)
    name: str
    price_cents: int = Field(ge=0)


class CatalogStore:
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection
        self.lock = Lock()
        self.closed = False

    def initialize(self) -> None:
        with self.lock:
            self.connection.execute(
                "CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT NOT NULL, price_cents INTEGER NOT NULL)"
            )
            self.connection.executemany(
                "INSERT INTO products VALUES (?, ?, ?)",
                [(1, "Keyboard", 9900), (2, "Mouse", 4900)],
            )
            self.connection.commit()

    def list_products(self) -> tuple[Product, ...]:
        with self.lock:
            rows = self.connection.execute("SELECT id, name, price_cents FROM products ORDER BY id").fetchall()
        return tuple(Product(id=row[0], name=row[1], price_cents=row[2]) for row in rows)

    def get_product(self, product_id: int) -> Product | None:
        with self.lock:
            row = self.connection.execute(
                "SELECT id, name, price_cents FROM products WHERE id = ?", (product_id,)
            ).fetchone()
        return Product(id=row[0], name=row[1], price_cents=row[2]) if row else None

    def close(self) -> None:
        with self.lock:
            if not self.closed:
                self.connection.close()
                self.closed = True


@asynccontextmanager
async def open_catalog() -> AsyncIterator[CatalogStore]:
    # 同步路由在线程池中运行，允许跨线程使用，并用 Lock 串行化本例的共享连接。
    store = CatalogStore(sqlite3.connect(":memory:", check_same_thread=False))
    try:
        store.initialize()
        yield store
    finally:
        # 初始化失败（尚未 yield）时也会进入 finally。
        store.close()


def load_snapshot(store: CatalogStore) -> tuple[Product, ...]:
    return store.list_products()


@dataclass(frozen=True)
class Resources:
    store: CatalogStore
    snapshot: tuple[Product, ...]
    instance_id: str
