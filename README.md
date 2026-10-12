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
- `stage02_params`：路径参数与查询参数
- `stage03_pydantic_body`：请求体与 Pydantic 模型
- `stage04_depends`：依赖注入（Depends）
- `stage05_sqlite`：数据库入门（SQLite + SQLAlchemy）
- `stage06_project_layout`：项目结构化与路由拆分
- `stage07_settings_env`：配置管理与环境变量
- `stage08_alembic_migrations`：数据库进阶与 Alembic 迁移
- `stage09_user_register_password`：用户注册与密码安全
- `stage10_jwt_auth`：JWT 登录与鉴权进阶
- `stage11_roles_permissions`：权限与角色控制
- `stage12_response_errors`：请求响应规范与全局异常处理
- `stage13_pagination_filtering`：分页、排序与过滤
- `stage14_upload_static_files`：文件上传与静态文件
- `stage15_form_cookie_session`：表单、Cookie 与 Session 基础
- `stage16_middleware_cors`：中间件与 CORS
- `stage17_background_tasks`：后台任务与邮件发送模拟
- `stage18_async_http`：异步接口与外部 HTTP 调用
- `stage19_websocket`：WebSocket 入门
- `stage20_testing_advanced`：测试进阶
- `stage21_openapi_docs`：OpenAPI 文档与接口元数据
- `stage22_logging_observability`：日志与可观测性基础
- `stage23_lifespan`：应用生命周期与资源管理
- `stage24_deployment`：部署入门
- `stage25_mini_api`：综合项目 Mini Task API

> Stage 01-25 主学习路线已完成。综合项目位于 `stage25_mini_api`，整合注册、JWT、权限、任务 CRUD、分页、配置、异常与测试；后续可按各阶段 README 的小练习继续扩展。

## 学习任务清单

- 查看 `docs/TASKS.md` 获取基于当前代码的分阶段任务与验收标准。

## 通用环境准备

建议使用 Miniconda 创建 Python 3.12 虚拟环境。

```bash
conda create -n fastapi-learning-lab python=3.12 -y
conda activate fastapi-learning-lab
python -m pip install -U pip
```

## 如何运行某个阶段

以第一阶段为例：

```bash
cd stage01_hello_fastapi
python -m pip install -r requirements.txt
uvicorn main:app --reload
```

## 如何运行测试

以第一阶段为例：

```bash
cd stage01_hello_fastapi
pytest -q
```

各阶段都有独立的 `requirements.txt`。切换阶段后先安装该阶段依赖；不要在仓库根目录直接执行 `pytest`，不同阶段的同名模块需要独立进程隔离。

## 自动化检查

GitHub Actions 会在向默认分支 `Aivor` 提交或创建 PR 时检查阶段结构，并独立安装依赖、执行各阶段测试。综合项目额外覆盖 Windows，汇总结果见 `CI Gate`。

本地可在安装所需阶段依赖后执行：

```bash
python scripts/stages.py
python -m unittest discover -s tests_ci -v
python scripts/stages.py --test --stage stage25_mini_api
```

全量测试、JUnit 报告及 CI 排错说明见 [自动化测试说明](docs/CI.md)。
