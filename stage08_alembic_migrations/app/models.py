"""ORM 模型描述当前版本的目标表结构。"""

from sqlalchemy import Float, String, true
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Item(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), index=True)
    price: Mapped[float] = mapped_column(Float)
    in_stock: Mapped[bool] = mapped_column(default=True, server_default=true())
