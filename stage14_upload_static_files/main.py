"""Stage 14：上传文件与挂载静态文件目录。"""

from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, Request, UploadFile
from pydantic import BaseModel

from app.storage import DownloadFiles, FileStorage


class UploadResponse(BaseModel):
    filename: str
    stored_name: str
    content_type: str
    size: int
    url: str


def create_app(storage_dir: Path | None = None) -> FastAPI:
    storage = FileStorage(storage_dir or Path(__file__).parent / "uploads")
    application = FastAPI(title="Stage 14：文件上传与静态文件")
    application.mount("/files", DownloadFiles(directory=storage.public_dir), name="files")

    @application.post("/uploads", status_code=201, response_model=UploadResponse, tags=["files"])
    def upload_file(request: Request, file: Annotated[UploadFile, File()]) -> UploadResponse:
        # 同步路由在线程池内读取临时文件和写磁盘，不阻塞异步事件循环。
        try:
            stored_name, content_type, size = storage.save(file)
            return UploadResponse(
                filename=file.filename,
                stored_name=stored_name,
                content_type=content_type,
                size=size,
                url=str(request.url_for("files", path=stored_name)),
            )
        finally:
            file.file.close()

    return application


app = create_app()
