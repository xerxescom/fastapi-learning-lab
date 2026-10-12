from collections.abc import Generator
from pathlib import Path
from shutil import copytree

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.database import Base, get_db
from main import app

STAGE_DIR = Path(__file__).resolve().parent


def migration_config() -> Config:
    return Config(str(STAGE_DIR / "alembic.ini"))


def migrate(engine: Engine, direction: str, revision: str) -> None:
    with engine.begin() as connection:
        config = migration_config()
        config.attributes["connection"] = connection
        if direction == "upgrade":
            command.upgrade(config, revision)
        else:
            command.downgrade(config, revision)


@pytest.fixture
def db_engine(tmp_path: Path) -> Generator[Engine, None, None]:
    engine = create_engine(
        f"sqlite:///{(tmp_path / 'test.db').as_posix()}",
        connect_args={"check_same_thread": False},
    )
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def client(db_engine: Engine) -> Generator[TestClient, None, None]:
    migrate(db_engine, "upgrade", "head")

    def override_get_db() -> Generator[Session, None, None]:
        with Session(db_engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


def test_crud_flow(client: TestClient) -> None:
    assert client.get("/items").json() == []
    response = client.post("/items", json={"name": "键盘", "price": 399})
    assert response.status_code == 201
    item = response.json()
    assert item == {"id": 1, "name": "键盘", "price": 399.0, "in_stock": True}
    assert client.get("/items/1").json() == item
    assert client.get("/items").json() == [item]
    updated = client.put(
        "/items/1", json={"name": "鼠标", "price": 99, "in_stock": False}
    )
    assert updated.status_code == 200
    assert updated.json() == {"id": 1, "name": "鼠标", "price": 99.0, "in_stock": False}
    assert client.get("/items/1").json() == updated.json()
    deleted = client.delete("/items/1")
    assert deleted.status_code == 204
    assert deleted.content == b""
    assert client.get("/items/1").status_code == 404
    assert client.get("/items").json() == []


@pytest.mark.parametrize("method", ["get", "put", "delete"])
def test_missing_item(client: TestClient, method: str) -> None:
    kwargs = {"json": {"name": "键盘", "price": 1}} if method == "put" else {}
    response = client.request(method, "/items/999", **kwargs)
    assert response.status_code == 404
    assert response.json() == {"detail": "Item not found"}


@pytest.mark.parametrize("body", [{"name": "", "price": 1}, {"name": "键盘", "price": 0}])
def test_invalid_body(client: TestClient, body: dict) -> None:
    assert client.post("/items", json=body).status_code == 422
    assert client.get("/items").json() == []


def test_dependency_override_writes_to_test_database(client: TestClient, db_engine: Engine) -> None:
    assert get_db in app.dependency_overrides
    client.post("/items", json={"name": "Test item", "price": 10})
    with db_engine.connect() as connection:
        assert connection.scalar(text("SELECT name FROM items")) == "Test item"


def test_migration_upgrade_preserves_existing_rows(db_engine: Engine) -> None:
    migrate(db_engine, "upgrade", "0001")
    with db_engine.begin() as connection:
        connection.execute(text("INSERT INTO items (name, price) VALUES ('Keyboard', 10)"))
    migrate(db_engine, "upgrade", "head")
    migrate(db_engine, "upgrade", "head")
    with db_engine.connect() as connection:
        row = connection.execute(text("SELECT name, price, in_stock FROM items")).one()
        assert tuple(row) == ("Keyboard", 10.0, 1)
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "0002"


def test_migration_downgrade_and_reupgrade(db_engine: Engine) -> None:
    migrate(db_engine, "upgrade", "head")
    migrate(db_engine, "downgrade", "0001")
    assert "in_stock" not in {column["name"] for column in inspect(db_engine).get_columns("items")}
    migrate(db_engine, "upgrade", "head")
    assert "in_stock" in {column["name"] for column in inspect(db_engine).get_columns("items")}
    migrate(db_engine, "downgrade", "base")
    assert "items" not in inspect(db_engine).get_table_names()


def test_migrated_schema_matches_models(db_engine: Engine) -> None:
    migrate(db_engine, "upgrade", "head")
    with db_engine.connect() as connection:
        context = MigrationContext.configure(connection, opts={"compare_server_default": True})
        assert compare_metadata(context, Base.metadata) == []


def test_alembic_url_configuration(tmp_path: Path) -> None:
    config = migration_config()
    url = f"sqlite:///{(tmp_path / 'configured.db').as_posix()}"
    config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    command.upgrade(config, "head")
    engine = create_engine(url)
    try:
        assert "items" in inspect(engine).get_table_names()
    finally:
        engine.dispose()


def test_autogenerate_renders_revision_template(tmp_path: Path) -> None:
    scripts = tmp_path / "migrations"
    copytree(STAGE_DIR / "migrations", scripts, ignore=lambda _, names: [n for n in names if n == "__pycache__"])
    config = migration_config()
    config.set_main_option("script_location", str(scripts).replace("%", "%%"))
    config.set_main_option(
        "sqlalchemy.url", f"sqlite:///{(tmp_path / 'autogenerate.db').as_posix()}".replace("%", "%%")
    )
    command.upgrade(config, "head")
    revision = command.revision(config, message="schema check", autogenerate=True)
    assert revision.down_revision == "0002"
    generated = Path(revision.path).read_text(encoding="utf-8")
    compile(generated, revision.path, "exec")
