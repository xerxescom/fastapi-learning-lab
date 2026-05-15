from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from main import Base, app, get_db

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base.metadata.create_all(bind=engine)


def override_get_db() -> Generator[Session, None, None]:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def test_crud_flow() -> None:
    create_resp = client.post(
        "/items",
        json={"name": "机械键盘", "price": 399.0, "in_stock": True},
    )
    assert create_resp.status_code == 201
    created = create_resp.json()
    assert created["id"] == 1

    list_resp = client.get("/items")
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

    item_id = created["id"]
    get_resp = client.get(f"/items/{item_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["name"] == "机械键盘"

    update_resp = client.put(
        f"/items/{item_id}",
        json={"name": "办公键盘", "price": 299.0, "in_stock": False},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["name"] == "办公键盘"

    delete_resp = client.delete(f"/items/{item_id}")
    assert delete_resp.status_code == 204

    get_after_delete_resp = client.get(f"/items/{item_id}")
    assert get_after_delete_resp.status_code == 404


def test_not_found_on_update_and_delete() -> None:
    update_resp = client.put(
        "/items/999",
        json={"name": "不存在", "price": 1.0, "in_stock": True},
    )
    assert update_resp.status_code == 404

    delete_resp = client.delete("/items/999")
    assert delete_resp.status_code == 404
