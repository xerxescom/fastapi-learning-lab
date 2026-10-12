# 阶段 08：数据库进阶与 Alembic 迁移

## 本阶段学习目标

- 拆分数据库配置、会话、ORM 模型、schema 与路由。
- 使用 Alembic 管理表结构版本，学习升级、回滚和自动生成迁移。
- 用请求级数据库会话依赖管理资源。
- 在临时数据库上执行真实迁移和 CRUD 测试。

## 核心概念

| 模块 | 职责 |
| --- | --- |
| `main.py` | 组装应用和路由 |
| `app/config.py` | 读取数据库连接配置 |
| `app/database.py` | 定义引擎、Base、会话工厂和 `get_db` |
| `app/models.py` | 描述当前 ORM 表结构 |
| `app/schemas.py` | 校验输入、序列化 ORM 响应 |
| `app/routers.py` | 商品 CRUD 接口 |
| `migrations/` | 迁移环境、脚本模板与版本历史 |

Stage 05 的 `create_all()` 适合创建不存在的表，但不会把已有表自动修改为新模型结构。本阶段使用 Alembic 记录结构变化，应用启动时不自动建表；先运行迁移，再启动服务。

迁移链是 `base → 0001 → 0002 (head)`：`0001` 创建商品表与名称索引，`0002` 增加非空 `in_stock` 字段，并通过数据库默认值为已有记录填入 `true`。ORM 的 `default` 在应用插入数据时生效，`server_default` 由数据库执行。本例同时保留二者。

`migrations/env.py` 导入模型以注册元数据，用 `Base.metadata` 比较目标结构；`render_as_batch=True` 支持 SQLite 的表结构变更。自动生成的迁移必须人工检查，尤其是重命名、数据转换和删除字段，不能把生成结果直接视为正确结果。

`get_db` 为每个请求提供独立会话，退出时关闭；CRUD 显式提交事务，未提交的事务在关闭会话时回滚。测试通过覆盖这个依赖把请求切到临时 SQLite 数据库，并实际执行迁移，而不是调用 `create_all()`。

`alembic.ini` 的 `sqlalchemy.url` 留空时读取应用配置；测试可通过 Alembic Config 显式指定 URL 或传入连接。该文件保持 ASCII，避免 Windows 默认编码读取中文注释时出错。

## 运行命令

在仓库根目录激活已有虚拟环境，然后进入本阶段：

```powershell
.\.venv\Scripts\Activate.ps1
cd stage08_alembic_migrations
python -m pip install -r requirements.txt
python -m alembic upgrade head
python -m alembic current
python -m uvicorn main:app --reload
```

访问 http://127.0.0.1:8000/docs 。默认数据库是本阶段目录中的 `items.db`，无需复制 Stage 05 数据库。本地数据库文件和 `.env` 均不提交。

可选：将 `.env.example` 复制为 `.env`。`LAB_DATABASE_URL` 由应用和迁移共用，进程环境变量优先于 `.env`。示例中的相对 SQLite 路径基于执行命令时的工作目录，因此请始终在本阶段目录运行。配置加载后需要重启应用才能生效。

### 迁移命令

```powershell
python -m alembic history
python -m alembic current
python -m alembic upgrade head
python -m alembic check
```

当前仓库已包含迁移环境，不需要再次初始化。新建其他项目时可使用 `python -m alembic init migrations`，再接入配置和 ORM 元数据。

修改 ORM 模型后，在已升级到 head 的开发数据库上生成下一个版本：

```powershell
python -m alembic revision --autogenerate -m "add description"
# 检查生成脚本的 upgrade 与 downgrade，再执行：
python -m alembic upgrade head
```

回滚练习请仅在可丢弃的学习数据库上执行；删除字段会丢失该字段的数据，回滚到 base 会删除商品表：

```powershell
python -m alembic downgrade -1
python -m alembic upgrade head
```

回滚到 `0001` 后，先升级回 head，再运行当前版本应用，因为当前模型需要 `in_stock` 字段。部署前备份数据并检查迁移，生产环境由部署流程单独执行迁移。

## 测试命令

```powershell
python -m pytest -q
```

每项测试使用独立临时数据库，结束后释放引擎和依赖覆盖。覆盖 CRUD、404、422、升级数据保留、回滚再升级、模型与迁移结构一致性，以及迁移 URL 配置。测试不需要先初始化开发数据库。

验证记录（2026-10-12）：Python 3.12，`12 passed`，包括自动生成迁移脚本模板验证；CLI `current` 返回 `0002 (head)`，`check` 返回 `No new upgrade operations detected.`。有一条 Starlette TestClient 使用 httpx 的依赖弃用提示。

受限沙箱若无法创建系统临时目录，可以将当前终端的 `TEMP`、`TMP` 指向项目内可写临时目录后重试。

## 示例请求

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/items -ContentType 'application/json' -Body '{"name":"Keyboard","price":399}'
curl.exe http://127.0.0.1:8000/items
curl.exe http://127.0.0.1:8000/items/1
```

也可以在 `/docs` 中依次执行 POST、GET、PUT、DELETE。`PUT` 完整替换商品字段，省略 `in_stock` 时使用默认值 `true`；删除成功返回 204，无响应体。

## 预期返回

空数据库第一次创建商品，返回 201：

```json
{"id":1,"name":"Keyboard","price":399.0,"in_stock":true}
```

商品列表返回 200，内容为商品数组。访问不存在的商品返回 404：

```json
{"detail":"Item not found"}
```

价格必须为有限正数，名称长度为 1 到 50；非法请求返回 FastAPI 默认 422。

## 常见错误

1. **`no such table: items`**：先执行 `python -m alembic upgrade head`，检查迁移和应用是否指向同一数据库。
2. **找不到 `app` 模块或配置文件**：在本阶段目录执行命令，不要在仓库根目录运行 `main:app`。
3. **自动生成迁移为空**：确认模型已导入，`target_metadata` 正确；模型与数据库一致时生成空迁移是正常的。
4. **`Target database is not up to date`**：先检查 `current` 和 `history`，升级数据库到现有 head 后再生成迁移。
5. **模型已改，表没改**：修改 Python 模型不会自动修改数据库，需要生成、审查并执行迁移。
6. **SQLite 回滚限制**：复杂变更需要 batch 模式；回滚会删除的数据不能仅靠再次升级找回。

## 小练习

1. 为商品增加可空 `description`，生成并审查第三个迁移，同步修改 schema 和测试。
2. 在旧版本数据库中插入商品，再升级并验证原有数据保持不变。
3. 测试会话关闭时未提交事务会回滚。

迁移环境与命令参考：[Alembic 官方教程](https://alembic.sqlalchemy.org/en/latest/tutorial.html)。
