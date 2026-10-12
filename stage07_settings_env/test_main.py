from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from main import app
from settings import Settings, get_settings


@pytest.fixture(autouse=True)
def isolate_settings(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    for name in ("APP_NAME", "ENVIRONMENT", "DEBUG", "ITEMS_PER_PAGE"):
        monkeypatch.delenv(f"LAB_{name}", raising=False)
    # 不读取开发者本机的 .env，避免测试依赖本地状态。
    monkeypatch.setitem(Settings.model_config, "env_file", None)
    get_settings.cache_clear()
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()
    get_settings.cache_clear()


def test_default_configuration() -> None:
    with TestClient(app) as client:
        response = client.get("/info")
    assert response.status_code == 200
    assert response.json() == {
        "app_name": "FastAPI Learning Lab",
        "environment": "development",
        "debug": False,
        "items_per_page": 10,
    }


def test_environment_variables_override_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LAB_ENVIRONMENT", "production")
    monkeypatch.setenv("LAB_DEBUG", "true")
    monkeypatch.setenv("LAB_ITEMS_PER_PAGE", "25")
    with TestClient(app) as client:
        response = client.get("/info")
    assert response.json()["environment"] == "production"
    assert response.json()["debug"] is True
    assert response.json()["items_per_page"] == 25


def test_dotenv_and_environment_precedence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "LAB_APP_NAME=中文学习实验室\nLAB_ITEMS_PER_PAGE=20\n", encoding="utf-8"
    )
    from_file = Settings(_env_file=env_file)
    assert from_file.app_name == "中文学习实验室"
    assert from_file.items_per_page == 20
    monkeypatch.setenv("LAB_ITEMS_PER_PAGE", "30")
    assert Settings(_env_file=env_file).items_per_page == 30
    assert Settings(_env_file=env_file, items_per_page=40).items_per_page == 40


@pytest.mark.parametrize(
    ("name", "value", "field"),
    [
        ("LAB_ITEMS_PER_PAGE", "0", "items_per_page"),
        ("LAB_ITEMS_PER_PAGE", "101", "items_per_page"),
        ("LAB_ITEMS_PER_PAGE", "abc", "items_per_page"),
        ("LAB_DEBUG", "perhaps", "debug"),
        ("LAB_ENVIRONMENT", "unknown", "environment"),
        ("LAB_APP_NAME", "", "app_name"),
    ],
)
def test_invalid_configuration(
    monkeypatch: pytest.MonkeyPatch, name: str, value: str, field: str
) -> None:
    monkeypatch.setenv(name, value)
    with pytest.raises(ValidationError) as exc_info:
        Settings()
    assert exc_info.value.errors()[0]["loc"] == (field,)


def test_dependency_override_isolates_test_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LAB_ENVIRONMENT", "production")
    test_settings = Settings(environment="testing", items_per_page=5)
    app.dependency_overrides[get_settings] = lambda: test_settings
    with TestClient(app) as client:
        assert client.get("/info").json()["environment"] == "testing"
        assert client.get("/info").json()["items_per_page"] == 5
        app.dependency_overrides.clear()
        assert client.get("/info").json()["environment"] == "production"


def test_settings_cache_requires_explicit_reset(monkeypatch: pytest.MonkeyPatch) -> None:
    original = get_settings()
    monkeypatch.setenv("LAB_ITEMS_PER_PAGE", "50")
    assert get_settings() is original
    assert get_settings().items_per_page == 10
    get_settings.cache_clear()
    assert get_settings().items_per_page == 50
