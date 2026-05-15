# 阶段 04：依赖注入（Depends）

## 本阶段学习目标

- 理解 FastAPI 的依赖注入机制（`Depends`）。
- 学会将重复的查询参数逻辑抽成可复用依赖。
- 学会实现最小可用的 Header Token 鉴权依赖。
- 理解多个依赖如何在同一接口中组合使用。

## 核心概念

- **依赖（Dependency）**：可被路由函数复用的“前置逻辑”。
- **公共查询参数依赖**：将 `q`、`limit`、`offset` 的解析与校验集中管理。
- **鉴权依赖**：读取请求头 `x-token`，不合法时抛出 `401`。
- **依赖组合**：一个接口可同时依赖“参数处理 + 鉴权校验”。

## 运行命令

在当前目录（`stage04_depends`）执行：

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

### 1）携带正确 Token 的请求

```bash
curl "http://127.0.0.1:8000/items?q=keyboard&limit=5&offset=2" \
  -H "x-token: learning-token"
```

### 2）缺少 Token 的请求

```bash
curl "http://127.0.0.1:8000/items"
```

## 预期返回

### 1）成功响应（200）

```json
{"message":"ok","q":"keyboard","limit":5,"offset":2}
```

### 2）鉴权失败（401）

```json
{"detail":"Invalid or missing token"}
```

## 常见错误

1. **401（Token 缺失或错误）**  
   请求头未带 `x-token`，或值不等于 `learning-token`。

2. **422（查询参数不合法）**  
   例如 `limit=0` 或 `offset=-1`。

3. **把依赖当普通函数手动调用**  
   一般应通过 `Depends(...)` 让 FastAPI 自动注入。

## 小练习

1. 在公共查询参数中新增 `sort_by`（如 `name`、`price`）并做校验。
2. 将固定 token 改为从环境变量读取。
3. 新增 `GET /users`，复用相同的查询参数依赖与鉴权依赖。
