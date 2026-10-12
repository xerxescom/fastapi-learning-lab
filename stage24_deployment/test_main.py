import asyncio
import io
import json
from pathlib import Path
from urllib.error import URLError

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app import healthcheck
from app.config import Settings
from main import app, create_app


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch):
    import os

    for name in os.environ:
        if name.startswith("LAB_"):
            monkeypatch.delenv(name)


def settings(**overrides):
    return Settings(environment="testing", allowed_hosts=["testserver", "127.0.0.1"], **overrides)


def test_default_settings():
    config = Settings()
    assert config.debug is False and config.docs_enabled is False
    assert config.allowed_hosts == ["127.0.0.1", "localhost"]
    assert Settings.model_config["env_file"] is None


def test_example_env_file_can_be_loaded_explicitly():
    config = Settings(_env_file=Path(__file__).with_name(".env.example"))
    assert config.environment == "production"
    assert config.debug is False and config.docs_enabled is False
    assert "127.0.0.1" in config.allowed_hosts


def test_module_entrypoint():
    with TestClient(app, base_url="http://127.0.0.1") as client:
        assert client.get("/health/live").json() == {"status": "alive"}
        assert client.get("/health/ready").json() == {"status": "ready"}


def test_public_info_whitelist():
    with TestClient(create_app(settings(release_version="2.0.0"))) as client:
        assert client.get("/info").json() == {
            "app_name": "FastAPI Deployment Lab", "environment": "testing", "release_version": "2.0.0",
        }


def test_environment_configuration(monkeypatch):
    monkeypatch.setenv("LAB_ENVIRONMENT", "production")
    monkeypatch.setenv("LAB_RELEASE_VERSION", "2.3.0")
    monkeypatch.setenv("LAB_ALLOWED_HOSTS", '["api.example.com","127.0.0.1"]')
    with TestClient(create_app(), base_url="https://api.example.com") as client:
        assert client.get("/info").json()["environment"] == "production"
        assert client.get("/info").json()["release_version"] == "2.3.0"
        assert client.get("/docs").status_code == 404


@pytest.mark.parametrize("values", [
    {"environment": "invalid"}, {"environment": "production", "debug": True},
    {"environment": "production", "allowed_hosts": ["*"]},
    {"allowed_hosts": []}, {"allowed_hosts": ["http://example.com"]},
    {"allowed_hosts": ["localhost:8000"]}, {"allowed_hosts": ["example.com/path"]},
    {"allowed_hosts": ["bad..example.com"]}, {"release_version": ""},
])
def test_invalid_configuration(values):
    with pytest.raises(ValidationError):
        Settings(**values)


def test_configuration_error_prevents_factory(monkeypatch):
    monkeypatch.setenv("LAB_ENVIRONMENT", "production")
    monkeypatch.setenv("LAB_DEBUG", "true")
    with pytest.raises(ValidationError):
        create_app()


@pytest.mark.parametrize("enabled", [True, False])
def test_documentation_switch(enabled):
    with TestClient(create_app(settings(docs_enabled=enabled))) as client:
        for path in ["/docs", "/redoc", "/openapi.json"]:
            assert client.get(path).status_code == (200 if enabled else 404)


@pytest.mark.parametrize("host,expected", [("api.example.com", 200), ("127.0.0.1", 200), ("evil.example", 400)])
def test_host_allowlist(host, expected):
    config = Settings(environment="production", allowed_hosts=["api.example.com", "127.0.0.1"])
    with TestClient(create_app(config)) as client:
        assert client.get("/health/live", headers={"Host": host}).status_code == expected


def test_forwarded_host_does_not_bypass_allowlist():
    with TestClient(create_app(settings())) as client:
        response = client.get("/info", headers={"Host": "evil.example", "X-Forwarded-Host": "testserver"})
        assert response.status_code == 400


def test_readiness_requires_lifespan():
    application = create_app(settings())

    async def scenario():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=application), base_url="http://testserver") as client:
            assert (await client.get("/health/live")).status_code == 200
            response = await client.get("/health/ready")
            assert response.status_code == 503 and response.json() == {"status": "not_ready"}

    asyncio.run(scenario())
    with TestClient(application) as client:
        assert client.get("/health/ready").status_code == 200
    assert application.state.ready is False


@pytest.mark.parametrize("status,payload,expected", [
    (200, b'{"status":"ready"}', True), (200, b'{"status":"alive"}', False),
    (503, b'{"status":"not_ready"}', False), (200, b'not-json', False),
])
def test_container_healthcheck(monkeypatch, status, payload, expected):
    class Opener:
        def open(self, url, timeout):
            assert url == "http://127.0.0.1:8000/health/ready" and timeout == 2
            response = io.BytesIO(payload)
            response.status = status
            return response

    monkeypatch.setattr(healthcheck, "build_opener", lambda *args: Opener())
    assert healthcheck.check_health() is expected


@pytest.mark.parametrize("error", [URLError("unavailable"), TimeoutError("timeout")])
def test_healthcheck_connection_errors(monkeypatch, error):
    class Opener:
        def open(self, url, timeout):
            raise error

    monkeypatch.setattr(healthcheck, "build_opener", lambda *args: Opener())
    assert healthcheck.check_health() is False


def test_docker_exec_form_and_runtime_only():
    # 静态检查不是容器构建测试，只防止关键教学约定被意外改掉。
    root = Path(__file__).parent
    lines = (root / "Dockerfile").read_text(encoding="utf-8").splitlines()
    command = json.loads(next(line[4:] for line in lines if line.startswith("CMD [")))
    assert command[:4] == ["python", "-m", "uvicorn", "main:app"]
    assert "--reload" not in command and "--no-proxy-headers" in command
    assert "USER appuser" in lines
    assert "COPY requirements-runtime.txt ./" in lines
    assert "COPY . ." not in lines
    assert "pytest" not in (root / "requirements-runtime.txt").read_text(encoding="utf-8")
