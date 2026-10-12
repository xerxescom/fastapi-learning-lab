"""将 ORM 元数据和数据库连接接入 Alembic。"""

from alembic import context
from sqlalchemy import create_engine, pool

from app.config import Settings
from app.database import Base
from app import models  # noqa: F401

config = context.config
target_metadata = Base.metadata


def database_url() -> str:
    return config.get_main_option("sqlalchemy.url") or Settings().database_url


def migrate(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=True,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    context.configure(
        url=database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    # 测试可提供临时数据库连接，迁移不会访问开发数据库。
    supplied_connection = config.attributes.get("connection")
    if supplied_connection is not None:
        migrate(supplied_connection)
    else:
        migration_engine = create_engine(database_url(), poolclass=pool.NullPool)
        try:
            with migration_engine.connect() as connection:
                migrate(connection)
        finally:
            migration_engine.dispose()
