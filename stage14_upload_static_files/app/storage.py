"""仅公开经过校验的文本文件，不使用客户端文件名作为磁盘路径。"""

import json
import os
import tempfile
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile
from starlette.responses import Response
from starlette.staticfiles import StaticFiles
from starlette.types import Scope

MAX_FILE_SIZE = 1024 * 1024
CHUNK_SIZE = 64 * 1024
ALLOWED_TYPES = {".txt": "text/plain", ".json": "application/json"}


def reject_json_constant(value: str) -> None:
    raise ValueError(f"Invalid JSON constant: {value}")


class DownloadFiles(StaticFiles):
    async def get_response(self, path: str, scope: Scope) -> Response:
        response = await super().get_response(path, scope)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Disposition"] = "attachment"
        return response


class FileStorage:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.public_dir = self.root / "public"
        self.public_dir.mkdir(parents=True, exist_ok=True)

    def save(self, upload: UploadFile) -> tuple[str, str, int]:
        filename = upload.filename or ""
        if (
            not filename.strip()
            or len(filename) > 200
            or any(char in filename for char in '/\\:')
            or any(ord(char) < 32 or ord(char) == 127 for char in filename)
        ):
            raise HTTPException(400, "Invalid filename")

        suffix = Path(filename).suffix.lower()
        content_type = (upload.content_type or "").split(";", 1)[0].strip().lower()
        if suffix not in ALLOWED_TYPES or content_type != ALLOWED_TYPES[suffix]:
            raise HTTPException(415, "Only .txt/text/plain and .json/application/json are allowed")

        # 不信任客户端声明的大小；最多读取上限加一个字节即可判断超限。
        data = bytearray()
        while chunk := upload.file.read(min(CHUNK_SIZE, MAX_FILE_SIZE + 1 - len(data))):
            data.extend(chunk)
            if len(data) > MAX_FILE_SIZE:
                raise HTTPException(413, "File exceeds 1 MiB")
        if not data:
            raise HTTPException(400, "Empty file is not allowed")
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            raise HTTPException(400, "File must use UTF-8 encoding") from None
        if "\x00" in text:
            raise HTTPException(400, "NUL characters are not allowed")
        if suffix == ".json":
            try:
                json.loads(text, parse_constant=reject_json_constant)
            except (ValueError, RecursionError):
                raise HTTPException(400, "File must contain valid JSON") from None

        stored_name = f"{uuid4().hex}{suffix}"
        temporary_path = None
        try:
            # 暂存文件不在静态目录内，写完再原子发布，避免下载到半个文件。
            with tempfile.NamedTemporaryFile(dir=self.root, suffix=".part", delete=False) as target:
                temporary_path = Path(target.name)
                target.write(data)
            os.replace(temporary_path, self.public_dir / stored_name)
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
        return stored_name, ALLOWED_TYPES[suffix], len(data)
