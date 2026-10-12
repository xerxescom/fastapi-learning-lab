# 阶段 12：请求响应规范与全局异常处理

## 本阶段学习目标

- 使用泛型 Pydantic 模型声明统一成功响应。
- 将业务异常、HTTP 异常、请求校验异常和未知异常集中处理。
- 保留 HTTP 状态码与必要响应头，同时统一 JSON 格式。
- 区分请求错误与服务端响应错误，避免泄露原始输入和内部详情。

## 核心概念

本阶段独立运行，使用两个内存商品，无需数据库、登录或密钥。报价接口只计算价格和检查可用库存，不扣减库存、不创建订单。

| 模块 | 职责 |
| --- | --- |
| `app/schemas.py` | 泛型成功响应、错误响应、校验错误及业务模型 |
| `app/exceptions.py` | 可预期的业务异常及错误码 |
| `app/handlers.py` | 注册并实现全局异常处理器 |
| `app/services.py` | 商品查询和报价逻辑 |
| `app/routers.py` | 接口与明确的响应模型 |
| `main.py` | 应用工厂与模块组装 |

成功与失败统一使用 `code`、`message`、`data`。成功时 `code=0`，`data` 为具体业务结果；失败时 `code` 为非零错误码，普通错误的 `data=null`，校验错误的 `data.errors` 给出字段问题。

`SuccessResponse[T]` 保留 `data` 的具体类型，例如商品、商品列表、报价结果。路由显式使用响应模型，FastAPI 据此校验输出并生成 OpenAPI；错误响应通过 `responses` 声明。统一包装有利于客户端按同一方式处理，但会增加一层结构，客户端也需适配。

| 错误来源 | HTTP 状态 | code | message |
| --- | --- | --- | --- |
| 商品不存在 | 404 | 40401 | Item not found |
| 库存不足 | 409 | 40901 | Not enough stock |
| 未知路由 | 404 | 40400 | Not Found |
| 请求校验失败 | 422 | 42200 | Request validation failed |
| 未处理服务端异常 | 500 | 50000 | Internal server error |

业务错误使用专用错误码；通用 HTTP 异常使用 `状态码 × 100`。这些是本示例的约定，不是 FastAPI 标准错误码。HTTP 错误仍返回对应的 4xx/5xx，不以 200 表示失败。

业务层抛出 `ItemNotFoundError`、`OutOfStockError`，无需依赖 FastAPI。处理器将它们转成 HTTP 响应。HTTP 处理器注册的是 Starlette 的 `HTTPException` 基类，因此也能覆盖 FastAPI 的异常，以及框架产生的未知路由 404、方法不支持 405；同时保留 `WWW-Authenticate`、`Allow`、`Retry-After` 等响应头。

422 只返回字段位置、说明、类型，不回显原始 `input`、`ctx` 或请求体。未知异常返回固定 500 消息，内部堆栈记录在服务端日志；显式 HTTP 5xx 也不向客户端返回内部详情。HTTP 4xx 的字符串 `detail` 被视为可公开说明，结构化 `detail` 则使用标准状态说明，避免绕过本例的响应契约。

请求校验失败说明客户端输入不合法，返回 422；响应模型校验失败说明服务端生成了错误结果，返回 500。生产配置需要保持 `debug=False`，调试模式可能返回堆栈页面。服务端日志同样需要限制访问，异常内容中也应避免携带真实凭据。

异常处理器不修改正常响应。本例显式包装业务 JSON，不用中间件重新解析所有响应，因此 `/docs`、`/openapi.json` 和重定向仍保留原格式。后续文件下载、流式响应和无内容的 204 也应保留各自的 HTTP 语义。

机制参考：[FastAPI 官方异常处理教程](https://fastapi.tiangolo.com/tutorial/handling-errors/)。

## 运行命令

在仓库根目录激活虚拟环境，然后进入本阶段：

```powershell
.\.venv\Scripts\Activate.ps1
cd stage12_response_errors
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload
```

访问 http://127.0.0.1:8000/docs 。商品 1 单价 99、库存 5；商品 2 库存为 0，便于演示库存冲突。

`/examples/unauthorized` 固定触发 401，`/examples/server-error` 固定触发 500，仅供学习使用。实际业务应用不应暴露故障演示接口。

## 测试命令

```powershell
python -m pytest -q
```

每个测试创建独立应用实例。测试 500 响应时必须使用 `TestClient(..., raise_server_exceptions=False)`；默认客户端会重新抛出服务端异常，便于调试，但此时不能直接检查 500 JSON。

覆盖成功响应、报价不改变库存、业务 404/409、框架 404/405、请求及响应校验、错误信息脱敏、服务端日志、必要 HTTP 响应头、OpenAPI 错误模型和重定向。

验证记录（2026-10-12）：Python 3.12，`25 passed`。有一条 Starlette TestClient 使用 httpx 的依赖弃用提示，不影响测试。

## 示例请求

```powershell
curl.exe http://127.0.0.1:8000/items/1
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/items/1/quote -ContentType 'application/json' -Body '{"quantity":2}'
curl.exe -i http://127.0.0.1:8000/items/999
curl.exe -i http://127.0.0.1:8000/missing-route
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/items/1/quote -ContentType 'application/json' -Body '{"quantity":0}'
curl.exe -i http://127.0.0.1:8000/examples/server-error
```

PowerShell 的 `Invoke-RestMethod` 遇到 4xx/5xx 会显示错误；也可以在 `/docs` 中检查响应体与状态码。

## 预期返回

商品查询返回 200：

```json
{"code":0,"message":"ok","data":{"id":1,"name":"Keyboard","price":99.0,"stock":5}}
```

报价返回 200：

```json
{"code":0,"message":"Quote calculated","data":{"item_id":1,"quantity":2,"total":198.0}}
```

商品不存在返回 404：

```json
{"code":40401,"message":"Item not found","data":null}
```

校验失败返回 422，其中说明文字由 Pydantic 生成，可能随版本变化：

```json
{"code":42200,"message":"Request validation failed","data":{"errors":[{"loc":["body","quantity"],"message":"Input should be greater than or equal to 1","type":"greater_than_equal"}]}}
```

未知异常返回 500：

```json
{"code":50000,"message":"Internal server error","data":null}
```

## 常见错误

1. **只处理 FastAPI HTTPException，未知路由仍返回默认格式**：注册 Starlette 基类的处理器。
2. **错误统一返回 200**：业务错误码不能替代 HTTP 状态码，客户端和监控都需要真实状态。
3. **直接输出 `exc.errors()` 或 `str(exc)`**：可能泄露原始输入或内部详情，应明确选择可公开字段。
4. **自定义 HTTP 处理器丢失响应头**：转发 `exc.headers`，否则会破坏认证或重试语义。
5. **把响应模型错误变成 422**：这属于服务端实现错误，应返回 500 并排查日志。
6. **测试 500 时直接抛出 RuntimeError**：设置 `raise_server_exceptions=False` 后检查响应。
7. **报价库存不减少**：本例是只读报价，非订单提交；金额使用 float 仅用于示例，真实金额处理应单独设计精度规则。

## 小练习

1. 新增一种业务异常及错误码，并验证 HTTP 状态与响应结构。
2. 将统一响应和异常处理器接入 Stage 11，确认 401 的认证响应头仍然保留。
3. 为错误加入请求标识，关联客户端报错与服务端日志，并编写一致性测试。
