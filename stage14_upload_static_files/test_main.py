from collections.abc import Generator
from io import BytesIO
from pathlib import Path
from uuid import UUID

import pytest
from fastapi import HTTPException, UploadFile
from fastapi.testclient import TestClient
from starlette.datastructures import Headers

from app.storage import MAX_FILE_SIZE, FileStorage
from main import create_app


@pytest.fixture
def storage_dir(tmp_path: Path) -> Path:
    return tmp_path / "uploads"


@pytest.fixture
def client(storage_dir: Path) -> Generator[TestClient, None, None]:
    with TestClient(create_app(storage_dir)) as test_client:
        yield test_client


def assert_no_files(storage_dir: Path) -> None:
    assert list(storage_dir.rglob("*")) == [storage_dir / "public"]


@pytest.mark.parametrize(
    "filename,content,content_type",
    [
        ("notes.txt", b"hello FastAPI", "text/plain"),
        ("中文.txt", "你好，FastAPI".encode(), "text/plain; charset=utf-8"),
        ("REPORT.TXT", b"hello", "text/plain"),
        ("data.json", b'{"name": "FastAPI", "enabled": true}', "application/json"),
        ("list.json", b"[1, 2, 3]", "application/json"),
        ("null.json", b"null", "application/json"),
    ],
)
def test_upload_and_download(client: TestClient, storage_dir: Path, filename, content, content_type):
    response = client.post("/uploads", files={"file": (filename, content, content_type)})
    assert response.status_code == 201
    body = response.json()
    assert set(body) == {"filename", "stored_name", "content_type", "size", "url"}
    assert body["filename"] == filename
    assert body["size"] == len(content)
    assert body["content_type"] == content_type.split(";")[0]
    stored_name = body["stored_name"]
    assert UUID(Path(stored_name).stem).version == 4
    assert Path(stored_name).suffix == Path(filename).suffix.lower()
    assert body["url"] == f"http://testserver/files/{stored_name}"
    download = client.get(body["url"])
    assert download.status_code == 200 and download.content == content
    assert download.headers["content-type"].split(";")[0] == body["content_type"]
    assert download.headers["x-content-type-options"] == "nosniff"
    assert download.headers["content-disposition"] == "attachment"
    assert (storage_dir / "public" / stored_name).read_bytes() == content
    assert list(storage_dir.glob("*.part")) == []


def test_same_filename_never_overwrites(client: TestClient):
    first = client.post("/uploads", files={"file": ("same.txt", b"first", "text/plain")}).json()
    second = client.post("/uploads", files={"file": ("same.txt", b"second", "text/plain")}).json()
    assert first["stored_name"] != second["stored_name"]
    assert client.get(first["url"]).content == b"first"
    assert client.get(second["url"]).content == b"second"


@pytest.mark.parametrize(
    "filename,content_type",
    [("page.html", "text/html"), ("image.png", "image/png"), ("script.exe", "text/plain"),
     ("file", "text/plain"), ("data.json", "text/plain"), ("text.txt", "application/json"),
     ("text.txt", "application/octet-stream")],
)
def test_unsupported_type(client: TestClient, storage_dir: Path, filename, content_type):
    response = client.post("/uploads", files={"file": (filename, b"hello", content_type)})
    assert response.status_code == 415
    assert_no_files(storage_dir)


@pytest.mark.parametrize("filename", ["../escape.txt", "..\\escape.txt", "/tmp/x.txt", "a" * 201 + ".txt"])
def test_reject_unsafe_filename(client: TestClient, storage_dir: Path, filename):
    response = client.post("/uploads", files={"file": (filename, b"hello", "text/plain")})
    assert response.status_code == 400
    assert_no_files(storage_dir)


@pytest.mark.parametrize("filename", ["a\x00.txt", "a\n.txt", "a\x7f.txt", "   ", "C:\\escape.txt"])
def test_control_characters_in_filename(storage_dir: Path, filename):
    upload = UploadFile(BytesIO(b"hello"), filename=filename, headers=Headers({"content-type": "text/plain"}))
    with pytest.raises(HTTPException) as error:
        FileStorage(storage_dir).save(upload)
    assert error.value.status_code == 400
    assert_no_files(storage_dir)


@pytest.mark.parametrize(
    "filename,content,content_type",
    [("empty.txt", b"", "text/plain"), ("binary.txt", b"\xff\xfe", "text/plain"),
     ("nul.txt", b"a\x00b", "text/plain"), ("bad.json", b"not json", "application/json"),
     ("bad.json", b'{"x": NaN}', "application/json"),
     ("bad.json", b'{"x": Infinity}', "application/json"),
     ("bad.json", b'{"unfinished": [', "application/json")],
)
def test_invalid_content(client: TestClient, storage_dir: Path, filename, content, content_type):
    response = client.post("/uploads", files={"file": (filename, content, content_type)})
    assert response.status_code == 400
    assert_no_files(storage_dir)


def test_exact_size_limit(client: TestClient):
    content = b"x" * MAX_FILE_SIZE
    response = client.post("/uploads", files={"file": ("large.txt", content, "text/plain")})
    assert response.status_code == 201
    assert response.json()["size"] == MAX_FILE_SIZE
    assert client.get(response.json()["url"]).content == content


def test_json_recursion_error(client: TestClient, storage_dir: Path, monkeypatch):
    def fail_parse(*args, **kwargs):
        raise RecursionError("simulated excessive nesting")

    # 递归上限由运行环境决定，直接模拟解析器错误使测试不依赖该上限。
    with monkeypatch.context() as context:
        context.setattr("app.storage.json.loads", fail_parse)
        response = client.post("/uploads", files={"file": ("deep.json", b"[]", "application/json")})
    assert response.status_code == 400
    assert_no_files(storage_dir)


@pytest.mark.parametrize("extra", [1, 65536])
def test_over_size_limit(client: TestClient, storage_dir: Path, extra):
    response = client.post("/uploads", files={"file": ("large.txt", b"x" * (MAX_FILE_SIZE + extra), "text/plain")})
    assert response.status_code == 413
    assert_no_files(storage_dir)


def test_size_check_stops_reading_at_limit(storage_dir: Path):
    source = BytesIO(b"x" * (MAX_FILE_SIZE * 2))
    upload = UploadFile(source, filename="large.txt", headers=Headers({"content-type": "text/plain"}))
    with pytest.raises(HTTPException) as error:
        FileStorage(storage_dir).save(upload)
    assert error.value.status_code == 413
    assert source.tell() == MAX_FILE_SIZE + 1
    assert_no_files(storage_dir)


@pytest.mark.parametrize("kwargs", [{}, {"json": {"file": "hello"}}, {"data": {"file": "hello"}}])
def test_missing_or_non_file_field(client: TestClient, storage_dir: Path, kwargs):
    assert client.post("/uploads", **kwargs).status_code == 422
    assert_no_files(storage_dir)


def test_static_missing_file_and_directory(client: TestClient):
    assert client.get("/files/missing.txt").status_code == 404
    assert client.get("/files/").status_code == 404
    assert client.post("/files/missing.txt").status_code == 405


def test_static_does_not_expose_parent(client: TestClient, storage_dir: Path):
    (storage_dir / "secret.txt").write_text("private", encoding="utf-8")
    assert client.get("/files/%2e%2e/secret.txt").status_code == 404
    assert client.get("/files/secret.txt").status_code == 404


def test_head_and_conditional_get(client: TestClient):
    body = client.post("/uploads", files={"file": ("notes.txt", b"hello", "text/plain")}).json()
    response = client.get(body["url"])
    head = client.head(body["url"])
    assert head.status_code == 200 and head.content == b""
    assert head.headers["content-length"] == "5"
    cached = client.get(body["url"], headers={"If-None-Match": response.headers["etag"]})
    assert cached.status_code == 304
    assert cached.headers["x-content-type-options"] == "nosniff"


def test_write_failure_cleans_temporary_file(storage_dir: Path, monkeypatch):
    def fail_replace(*args):
        raise OSError("simulated disk failure")

    monkeypatch.setattr("app.storage.os.replace", fail_replace)
    with TestClient(create_app(storage_dir), raise_server_exceptions=False) as client:
        response = client.post("/uploads", files={"file": ("notes.txt", b"hello", "text/plain")})
    assert response.status_code == 500
    assert "simulated" not in response.text
    assert_no_files(storage_dir)


def test_openapi_multipart_schema(client: TestClient):
    schema = client.get("/openapi.json").json()
    operation = schema["paths"]["/uploads"]["post"]
    ref = operation["requestBody"]["content"]["multipart/form-data"]["schema"]["$ref"]
    model = schema["components"]["schemas"][ref.rsplit("/", 1)[-1]]
    assert model["required"] == ["file"]
    file_schema = model["properties"]["file"]
    assert file_schema["type"] == "string"
    assert file_schema.get("format") == "binary" or file_schema.get("contentMediaType") == "application/octet-stream"
    assert "201" in operation["responses"]
    assert not any(path.startswith("/files") for path in schema["paths"])
