# Stage 21：OpenAPI 文档与接口元数据

## 本阶段学习目标

- 用商品目录接口学习 tags、summary、description 和稳定的 operation ID。
- 区分响应模型、响应文档和实际 HTTP 行为。
- 编写请求示例、错误响应说明，并定制 OpenAPI schema 与 Swagger UI。
- 用测试验证文档里的响应契约，而不只检查文档页面能否打开。

## 核心概念

### OpenAPI 与文档页面

`/openapi.json` 是机器可读的接口描述；`/docs` 的 Swagger UI 和 `/redoc` 是它的可视化阅读器。客户端生成、接口协作和契约测试都可以使用这份描述。

应用的 title、version、summary、description 描述整个 API；tags 负责分组，`openapi_tags` 同时控制分组顺序。路由的 summary 是简短标题，description 解释业务约束。参数与字段的 description 则应解释单位、边界等细节，而不是重复字段名。

本例显式指定 `listProducts`、`createProduct` 等唯一的 `operation_id`，便于客户端生成工具命名。发布后修改它可能影响生成客户端的方法名，应当按接口契约变更处理。

### 响应模型不是响应文档

`response_model=ProductRead` 会校验普通路由返回值，并过滤 `internal_cost_cents` 等非公开字段。`responses={409: ...}` 只是补充文档，既不会自动抛出 409，也不会自动校验直接返回的 `JSONResponse`。

因此，本例由 `ProductError` 明确指定状态码，先用 `ErrorResponse.model_validate()` 校验错误内容，再由异常处理器构造响应。404 和 409 使用业务错误模型，422 保留 FastAPI 默认的请求校验格式。本阶段刻意不统一所有错误，以观察不同响应如何写入文档。

POST 成功响应还声明了 `Location` 响应头，代码实际设置该头指向新商品。文档声明和运行行为都要分别实现、测试。

### 示例与 schema 定制

`ProductCreate` 的 `json_schema_extra` 提供模型示例；`Body(openapi_examples=...)` 提供带名称与说明的多组请求示例，便于在 Swagger UI 中选择。示例不是自动创建的数据，重复提交同一 SKU 仍会返回 409。

`app/openapi.py` 基于 FastAPI 的 `get_openapi()` 生成完整文档，然后添加 `info.x-learning-stage`。路由还通过 `openapi_extra` 添加 `x-learning-topic`。`x-` 扩展可供工具读取，但阅读器可以忽略它，不应依赖它实现校验或权限控制。

生成结果缓存在 `application.openapi_schema`。一般应在注册完路由后生成并保持稳定；学习时修改路由后，可以设为 `None` 再生成，不要把动态重建文档当成生产请求路径上的常规操作。

### 弃用与隐藏

`deprecated=True` 标记旧接口，不会停用它。`include_in_schema=False` 只隐藏文档，`/internal/ping` 仍然可直接访问。真正的访问控制需要鉴权依赖等机制，本阶段没有实现认证。

目录数据保存在每个应用实例的内存中，重启会重置，多进程之间不共享；这是独立学习示例，不是可直接公开部署的商品服务。

## 运行命令

在仓库根目录执行（已创建 `.venv` 的 Windows PowerShell）：

```powershell
.\.venv\Scripts\Activate.ps1
cd stage21_openapi_docs
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload
```

访问 `http://127.0.0.1:8000/docs`、`http://127.0.0.1:8000/redoc` 或 `http://127.0.0.1:8000/openapi.json`。本阶段无需数据库、迁移或其他服务。

`jsonschema` 仅用于测试响应契约，应用运行本身不依赖它。

## 测试命令

在阶段目录执行：

```powershell
python -m pytest -q -p no:cacheprovider
```

验证结果：`31 passed`。当前环境有一条 Starlette TestClient 使用 httpx 的依赖弃用提示，不影响测试通过。

测试使用独立的应用实例，检查元数据、参数约束、示例、文档缓存、响应头、响应字段过滤以及 404/409/422。`Draft202012Validator` 从 OpenAPI 提取对应状态码的响应 schema，并在同一根对象下提供 components，以解析本地 `$ref`，校验实际 JSON 响应。

这不是完整 OpenAPI 规范校验，也不意味着 JSON Schema 能表达所有运行时规则。例如 JSON Schema 的 integer 可以接受数学上为整数的 `4900.0`，而本例 Pydantic 的严格整数校验会拒绝 JSON 浮点输入。唯一性等状态相关规则也仍需要行为测试。

文档页面测试检查 HTML 返回及配置，不替代浏览器视觉验证；默认页面资源来自 CDN，离线环境可能打不开阅读器，但仍可访问本地 `/openapi.json`。

## 示例请求

在另一个 PowerShell 窗口执行：

```powershell
Invoke-RestMethod 'http://127.0.0.1:8000/products?limit=10'

$body = @{ sku = 'MOU-002'; name = 'Mouse'; price_cents = 4900 } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8000/products' -ContentType 'application/json' -Body $body

Invoke-RestMethod 'http://127.0.0.1:8000/products/2'
Invoke-RestMethod 'http://127.0.0.1:8000/openapi.json'
```

也可以在 `/docs` 中选择“创建商品”的鼠标或耳机示例后发送请求。SKU 必须符合三个大写字母、连字符、三个数字的格式，价格单位为分。

## 预期返回

新启动的应用查询列表返回 200：

```json
{"items":[{"id":1,"sku":"KEY-001","name":"Keyboard","price_cents":9900}],"total":1}
```

首次创建鼠标返回 201，并带有 `Location: /products/2`：

```json
{"id":2,"sku":"MOU-002","name":"Mouse","price_cents":4900}
```

再次提交相同 SKU 返回 409：

```json
{"detail":{"code":"SKU_CONFLICT","message":"SKU already exists"}}
```

查询不存在的正整数 ID 返回 404：

```json
{"detail":{"code":"PRODUCT_NOT_FOUND","message":"Product not found"}}
```

负数价格、额外字段、非法 SKU 或 `limit=0` 返回 422，`detail` 是 FastAPI 默认的校验错误列表。成功响应不会包含内部成本。

## 常见错误

- 把 `responses` 当成异常实现：它只生成说明，真实状态码与响应内容必须由代码返回。
- 认为自定义 `JSONResponse` 也会被 `response_model` 自动过滤：直接返回 Response 会绕过普通响应模型处理，必须自行保证内容正确。
- 把隐藏或弃用接口当成禁止访问：两者都不是权限控制。
- 修改路由后仍看到旧文档：确认是否使用了已缓存的 schema，开发时通常直接重启服务。
- 示例第二次发送失败：内存中已存在该 SKU，换一个合法 SKU 或重启应用。
- 从仓库根目录运行所有阶段测试：不同阶段有同名 `main`、`app` 模块，应进入对应阶段独立运行。
- `/docs` 空白但 `/openapi.json` 正常：检查浏览器是否能加载 CDN 资源，不能仅凭页面 HTML 返回 200 判断资源已经渲染。

## 小练习

1. 新增商品删除接口，声明 204 和 404，并验证 204 的实际响应没有响应体。
2. 为价格字段补充业务描述和合法示例，测试文档 schema 与实际返回保持一致。
3. 为隐藏接口增加鉴权，分别测试“没有文档”和“没有权限”是两种独立行为。
4. 为旧版接口制定迁移计划：保留旧 operation ID，新增替代接口，在文档中明确弃用原因。
