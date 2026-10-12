"""教学初始化入口：可重复执行，不删除已有数据；正式演进使用 Alembic。"""

from app.config import Settings
from app.database import Base, build_engine
from app import models  # 注册模型元数据。


def main():
    engine = build_engine(Settings().database_url)
    try:
        Base.metadata.create_all(engine)
    finally:
        engine.dispose()
    print("Database initialized; existing data preserved")


if __name__ == "__main__":
    main()
