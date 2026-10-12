"""为本阶段的独立新数据库建表。"""

from app.database import Base, engine
from app import models  # noqa: F401


if __name__ == "__main__":
    Base.metadata.create_all(engine)
    engine.dispose()
    print("Database initialized.")
