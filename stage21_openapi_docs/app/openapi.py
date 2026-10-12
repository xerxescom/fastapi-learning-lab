from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi


def install_openapi(application: FastAPI) -> None:
    def custom_openapi():
        if application.openapi_schema is not None:
            return application.openapi_schema
        schema = get_openapi(
            title=application.title, version=application.version,
            summary=application.summary, description=application.description,
            routes=application.routes, tags=application.openapi_tags,
            servers=application.servers, openapi_version=application.openapi_version,
        )
        # x- 扩展是文档元数据，不会改变接口行为，也不保证每种 UI 都展示。
        schema["info"]["x-learning-stage"] = 21
        application.openapi_schema = schema
        return schema

    application.openapi = custom_openapi
