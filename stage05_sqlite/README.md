# 阶段 05：数据库入门（SQLite + SQLAlchemy）

## 本阶段学习目标
- 理解如何在 FastAPI 中接入 SQLite。
- 学会使用 SQLAlchemy 建模并完成基础 CRUD。
- 学会通过依赖注入管理数据库会话（`Session`）。
- 理解测试隔离：使用临时 SQLite 数据库执行测试。

## 核心概念
- **SQLite**：本地轻量数据库，适合入门阶段与小型示例。
- **ORM 模型**：`Item` 类映射到 `items` 表。
- **数据库会话依赖**：`get_db` 负责创建/关闭会话。
- **测试隔离**：测试通过依赖覆盖切换到临时数据库。

## 运行命令
```bash
uvicorn main:app --reload
```

## 测试命令
```bash
pytest -q
```

## 示例请求
```bash
curl -X POST "http://127.0.0.1:8000/items" \
  -H "Content-Type: application/json" \
  -d '{"name":"机械键盘","price":399.0,"in_stock":true}'
```

## 预期返回
```json
{"id":1,"name":"机械键盘","price":399.0,"in_stock":true}
```

## 常见错误
1. **422（请求体不合法）**：例如 `price <= 0`。
2. **404（资源不存在）**：访问/更新/删除不存在的 `item_id`。
3. **SQLite 连接报错**：连接串写错或目录无写权限。

## 小练习
1. 给 `Item` 增加 `description` 字段并补齐测试。
2. 为 `GET /items` 增加分页参数。
3. 增加按名称模糊搜索。

## 数据库初始化与迁移说明（入门级）
- 本阶段采用 `Base.metadata.create_all(...)` 自动建表。
- 真实项目建议引入 Alembic 管理迁移。
