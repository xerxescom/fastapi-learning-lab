# 阶段 04：依赖注入（Depends）

## 本阶段学习目标

- 理解 FastAPI 依赖注入（Depends）的基本用法。
- 学会抽取可复用的公共查询参数依赖。
- 学会实现简单的 Header Token 鉴权依赖。
- 通过测试覆盖正常请求与鉴权失败场景。

## 核心概念

- **依赖（Dependency）**：把“可复用逻辑”拆为函数，通过 `Depends(...)` 注入到路由。
- **公共查询参数依赖**：例如分页参数 `limit`、`offset`，避免多个路由重复定义。
- **鉴权依赖**：统一校验 `X-Token`，未通过时抛出 `HTTPException(401)`。

## 运行命令

在当前目录（`stage04_depends`）执行：

```bash
uvicorn main:app --reload
```

启动后可访问：

- http://127.0.0.1:8000/docs

## 测试命令

```bash
pytest -q
```

## 示例请求

### 1）带 token 的正常请求

```bash
curl "http://127.0.0.1:8000/reports?limit=2&offset=1" \
  -H "X-Token: learning-lab-token"
```

### 2）缺少 token 的请求

```bash
curl "http://127.0.0.1:8000/reports"
```

## 预期返回

### 1）`GET /reports?limit=2&offset=1`（token 正确）

```json
{"items":["report-a","report-b","report-c"],"limit":2,"offset":1,"count":3}
```

### 2）`GET /reports`（缺少 token）

```json
{"detail":"Invalid X-Token"}
```

## 常见错误

1. **401（缺少或错误 token）**  
   忘记传 `X-Token` 或 token 值不正确。

2. **422（查询参数不合法）**  
   例如 `limit=0`，不满足 `limit >= 1`。

3. **依赖写在路由里导致重复**  
   建议将公共逻辑提取成独立依赖函数，便于复用和测试。

## 小练习

1. 新增 `GET /logs`，复用同一分页依赖与鉴权依赖。
2. 给鉴权依赖增加第二个合法 token（如测试环境 token）。
3. 给分页依赖增加 `max_limit` 控制，并为其补充测试。
