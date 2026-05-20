# 阶段 06：项目结构化与路由拆分

## 本阶段学习目标

- 理解 FastAPI 项目从单文件示例过渡到分层结构的基本方式。
- 学会使用 `APIRouter` 拆分路由。
- 学会将 Pydantic 模型放入 `schemas/`，将业务逻辑放入 `services/`。
- 理解轻量统一响应格式与业务异常处理。

## 核心概念

- **`main.py`**：应用入口，负责创建 `FastAPI` 实例、注册路由和异常处理器。
- **`routers/`**：存放接口定义，只处理 HTTP 请求与响应。
- **`schemas/`**：存放请求体和响应体模型，集中管理数据结构。
- **`services/`**：存放业务逻辑，本阶段使用内存字典模拟数据存储。
- **统一响应格式**：成功响应使用 `{"code":0,"message":"ok","data":...}`，业务错误使用相同结构返回错误信息。

## 运行命令

在当前目录（`stage06_project_layout`）执行：

```bash
uvicorn main:app --reload
```

启动后访问：

- http://127.0.0.1:8000/docs

## 测试命令

```bash
pytest -q
```

## 示例请求

### 1）创建商品

```bash
curl -X POST "http://127.0.0.1:8000/items" \
  -H "Content-Type: application/json" \
  -d '{"name":"机械键盘","price":399.0,"in_stock":true}'
```

### 2）查看商品列表

```bash
curl "http://127.0.0.1:8000/items"
```

### 3）访问不存在的商品

```bash
curl "http://127.0.0.1:8000/items/999"
```

## 预期返回

### 1）创建成功（201）

```json
{"code":0,"message":"Item created","data":{"id":1,"name":"机械键盘","price":399.0,"in_stock":true}}
```

### 2）列表响应（200）

```json
{"code":0,"message":"ok","data":[{"id":1,"name":"机械键盘","price":399.0,"in_stock":true}]}
```

### 3）业务错误（404）

```json
{"code":404,"message":"Item not found","data":null}
```

## 常见错误

1. **导入路径错误**  
   请在 `stage06_project_layout` 目录内运行命令，否则 `from routers...` 这类导入可能找不到模块。

2. **422（请求体不合法）**  
   例如 `name` 为空字符串，或 `price <= 0`。

3. **把业务逻辑写回路由函数**  
   本阶段重点是拆分职责，路由应尽量调用 service，而不是直接管理数据。

## 小练习

1. 新增 `description` 字段，并同步修改 schema、service 和测试。
2. 新增 `GET /items/{item_id}/stock`，只返回库存状态。
3. 将内存字典替换为 Stage 05 中的 SQLite 存储。
