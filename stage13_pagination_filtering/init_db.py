"""初始化本阶段独立数据库并向空表写入示例商品。"""

from app.database import Base, SessionLocal, engine
from app.seed import seed_items


if __name__ == "__main__":
    try:
        Base.metadata.create_all(engine)
        with SessionLocal() as session:
            inserted = seed_items(session)
        print("Database initialized; sample data inserted." if inserted else "Database initialized; existing data kept.")
    finally:
        engine.dispose()
