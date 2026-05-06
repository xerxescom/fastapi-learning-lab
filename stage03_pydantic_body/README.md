# 阶段 03：请求体与 Pydantic 模型

## 本阶段学习目标

- 学会在 FastAPI 中使用请求体（JSON Body）。
- 使用 Pydantic `BaseModel` 声明输入数据结构与校验规则。
- 理解字段默认值、可选字段（`Optional` / `| None`）的行为。
- 掌握 `response_model` 对输出数据的约束与过滤作用。

## 核心概念

- **请求体模型（Input Model）**：`ItemCreate` 描述客户端需要提交的字段。
- **响应模型（Output Model）**：`ItemResponse` 约束接口返回字段，防止泄露内部信息。
- **自动校验**：如 `name` 长度限制、`price > 0`，不满足时返回 `422`。
- **默认值与可选字段**：`in_stock=True` 是默认值，`description` 可不传。

## 运行命令

在当前目录（`stage03_pydantic_body`）执行：

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

### 1）完整请求体

```bash
curl -X POST "http://127.0.0.1:8000/items" \
  -H "Content-Type: application/json" \
  -d '{"name":"机械键盘","price":399.0,"in_stock":false,"description":"87键，红轴"}'
```

### 2）仅传必填字段（使用默认值）

```bash
curl -X POST "http://127.0.0.1:8000/items" \
  -H "Content-Type: application/json" \
  -d '{"name":"鼠标","price":99.9}'
```

## 预期返回

### 1）完整请求体返回

```json
{"id":1,"name":"机械键盘","price":399.0,"in_stock":false,"description":"87键，红轴"}
```

### 2）使用默认值返回

```json
{"id":1,"name":"鼠标","price":99.9,"in_stock":true,"description":null}
```

## 常见错误

1. **422（缺少必填字段）**  
   例如未传 `name` 或 `price`。

2. **422（字段格式或取值不合法）**  
   例如 `name` 为空字符串、`price <= 0`。

3. **误以为返回会包含全部内部字段**  
   即使服务端返回了额外字段，`response_model` 也会过滤掉未声明字段。

## 小练习

1. 在 `ItemCreate` 中新增 `tags: list[str] = []` 并补充测试。
2. 为 `price` 增加上限校验（如 `le=99999`）。
3. 新增 `GET /items/{item_id}` 并复用 `ItemResponse`。
