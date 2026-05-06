# fastapi-learning-lab

一个 **FastAPI 中文学习仓库**，面向有 Python 基础、希望系统掌握 FastAPI 的开发者。

## 仓库目标

本仓库按阶段记录 FastAPI 从常见用法到进阶用法的学习内容，并提供：

- 可直接运行的最小示例代码
- 详尽但不过度啰嗦的中文注释
- 配套中文学习文档（README）
- 对应自动化测试

## 学习路线（持续更新）

- `stage01_hello_fastapi`：FastAPI 入门与基础路由

> 后续会逐步加入请求参数、Pydantic 模型、依赖注入、数据库、鉴权、测试进阶等阶段。

## 学习任务清单

- 查看 `docs/TASKS.md` 获取基于当前代码的分阶段任务与验收标准。

## 通用环境准备

建议使用 Miniconda 创建 Python 3.12 虚拟环境。

```bash
conda create -n fastapi-learning-lab python=3.12 -y
conda activate fastapi-learning-lab
pip install -U pip
pip install fastapi uvicorn pytest httpx
```

## 如何运行某个阶段

以第一阶段为例：

```bash
cd stage01_hello_fastapi
uvicorn main:app --reload
```

## 如何运行测试

以第一阶段为例：

```bash
cd stage01_hello_fastapi
pytest -q
```
