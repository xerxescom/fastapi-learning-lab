# 阶段 02：路径参数与查询参数

## 本阶段学习目标

- 理解路径参数（Path Parameter）和查询参数（Query Parameter）的区别。
- 掌握 FastAPI 对参数类型的自动校验机制。
- 学会使用 `Query` 为查询参数添加默认值和边界限制。
- 编写覆盖正常与异常输入的基础测试。

## 核心概念

- **路径参数**：参数直接出现在 URL 路径中，例如 `/users/{user_id}`。
- **查询参数**：参数出现在 `?` 后，例如 `/items?limit=10&offset=0`。
- **参数校验**：当参数类型或约束不满足时，FastAPI 自动返回 `422 Unprocessable Entity`。
- **Query 校验器**：通过 `Query(ge=..., le=...)` 添加范围限制。

## 运行命令

在当前目录（`stage02_params`）执行：

```bash
uvicorn main:app --reload
```

## 测试命令

```bash
pytest -q
```

## 示例请求

### 1）路径参数

```bash
curl http://127.0.0.1:8000/users/123
```

### 2）查询参数（默认值）

```bash
curl http://127.0.0.1:8000/items
```

### 3）查询参数（自定义）

```bash
curl "http://127.0.0.1:8000/items?limit=20&offset=5&is_active=false"
```

## 预期返回

### 1）`GET /users/123`

```json
{"user_id": 123}
```

### 2）`GET /items`

```json
{"limit": 10, "offset": 0, "is_active": true}
```

### 3）`GET /items?limit=20&offset=5&is_active=false`

```json
{"limit": 20, "offset": 5, "is_active": false}
```

## 常见错误

1. **路径参数类型不匹配**  
   如 `/users/abc` 会触发 422，因为 `user_id` 需要 `int`。

2. **查询参数超出限制**  
   如 `limit=0` 不满足 `ge=1`，会触发 422。

3. **布尔值传参写法错误**  
   建议使用 `true/false`（不区分大小写），避免传入无法识别的值。

## 小练习

1. 给 `/users/{user_id}` 增加 `verbose: bool = False` 查询参数。
2. 给 `/items` 增加 `sort_by` 参数（如 `id`、`name`）。
3. 为新增参数补齐至少 2 条测试（正常 + 异常）。
