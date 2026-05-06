"""阶段 01：FastAPI 入门与基础路由示例。"""

from fastapi import FastAPI

# 通过 title/version/description 提供清晰的接口元信息，便于在 /docs 中学习。
app = FastAPI(
    title="FastAPI 学习实验室 - 阶段 01",
    version="0.1.0",
    description="第一个可运行的 FastAPI 应用，演示基础 GET 路由。",
)


@app.get("/")
def read_root() -> dict[str, str]:
    """根路由：用于验证服务是否启动成功。"""
    return {"message": "你好，FastAPI！"}


@app.get("/health")
def health_check() -> dict[str, str]:
    """健康检查路由：在真实项目中常用于容器探针。"""
    return {"status": "ok"}
