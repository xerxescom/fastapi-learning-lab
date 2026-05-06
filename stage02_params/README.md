# 阶段 02：路径参数与查询参数

## 本阶段学习目标

- 理解并使用路径参数（Path Parameters）。
- 理解并使用查询参数（Query Parameters）。
- 掌握常见参数类型（`int`、`str`、`bool`）及其自动校验。
- 通过测试验证合法与非法参数场景。

## 核心概念

- **路径参数**：写在 URL 路径中，通常用于标识具体资源，例如 `/users/{user_id}`。
- **查询参数**：写在 `?` 之后，通常用于筛选、分页、开关控制，例如 `/items?limit=20&offset=0`。
- **类型校验**：FastAPI 会根据函数参数类型自动解析与校验，不符合要求时返回 `422 Unprocessable Entity`。

## 运行命令

在当前目录（`stage02_params`）执行：

```bash
uvicorn main:app --reload
```

启动后访问：

- http://127.0.0.1:8000/users/1
- http://127.0.0.1:8000/items?limit=10&offset=0
- http://127.0.0.1:8000/docs

## 测试命令

```bash
pytest -q
```

## 示例请求

### 1）路径参数：获取用户

```bash
curl "http://127.0.0.1:8000/users/42?short=true"
```

### 2）查询参数：分页与筛选

```bash
curl "http://127.0.0.1:8000/items?limit=20&offset=5&q=notebook&active=false"
```

## 预期返回

### 1）`GET /users/42?short=true`

```json
{"user_id": 42, "username": "user-42", "short": true}
```

### 2）`GET /items?limit=20&offset=5&q=notebook&active=false`

```json
{"limit": 20, "offset": 5, "q": "notebook", "active": false}
```

## 常见错误

1. **422（路径参数类型错误）**  
   例如访问 `/users/not-an-int`，`user_id` 需要 `int`，因此会返回 422。

2. **422（查询参数超出约束）**  
   例如 `limit=0`，但 `limit` 被约束为 `1~100`，会返回 422。

3. **布尔参数理解偏差**  
   `active=false` 会被正确解析为 `False`；若传递不可识别文本，也可能触发 422。

## 小练习

1. 为 `/items` 增加 `sort_by: str = "created_at"` 参数。
2. 增加 `GET /orders/{order_id}` 路由，并给 `order_id` 添加最小值约束。
3. 为新增参数和路由补充 pytest 用例（含至少 1 个 422 场景）。
