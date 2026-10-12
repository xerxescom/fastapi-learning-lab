# Stage 16：中间件与 CORS

## 本阶段学习目标

- 用中间件为请求添加 ID、耗时响应头和完成日志。
- 观察多层中间件的进入与返回顺序。
- 配置明确的跨域来源、方法、请求头和可读取的响应头。
- 验证预检、普通请求及异常响应的差异。

## 核心概念

### 中间件负责横切逻辑

日志、耗时、跨域等逻辑可覆盖多个接口，适合放在中间件；具体业务校验、身份与权限通常仍由路由和依赖负责。本例使用纯 ASGI 中间件，通过包装 `send` 修改响应头，不读取请求体，也不缓冲响应体。

`app/middleware.py` 提供请求观测与顺序演示，`main.py` 组装应用、CORS 和演示路由。

本阶段显式包装 ASGI 应用，最终导出的 `app` 不再直接是 FastAPI 实例，但 Uvicorn 和 TestClient 都可以运行它，`/docs` 和 `/openapi.json` 仍正常可用。需要直接调用 FastAPI 的方法时，应在内部 `api` 对象组装阶段完成。

### 顺序与错误响应

请求进入顺序为：

```text
RequestLog -> CORS -> outer -> inner -> FastAPI -> 路由
```

响应头向外返回时，先经过 inner，再经过 outer、CORS 和 RequestLog。调用 `/middleware-order` 后，响应体只能记录路由执行到当时的事件：

```json
{"trace": ["outer:before", "inner:before", "handler"]}
```

完整演示顺序出现在响应头：

```text
X-Middleware-Order: outer:before,inner:before,handler,inner:after,outer:after
```

这里的 `after` 指拦截到 `http.response.start`，不是整个响应体发送完毕。包装顺序由代码明确展示，不依赖注册顺序猜测。使用 FastAPI `add_middleware` 时，后添加的用户中间件位于先添加的外面，且仍位于框架外层错误处理之内；与这里包住整个 FastAPI 的方式有所不同。

CORS 在整个 FastAPI 外面，因此框架生成的 500 也能带跨域头。日志再放在 CORS 外面，因此提前返回的预检请求也会被记录。预检不进入 outer/inner 或路由，所以没有 `X-Middleware-Order`。

FastAPI 处理未捕获异常时可以发送通用 500 响应，随后仍将异常抛给服务器记录。观测中间件不会吞掉异常或重复发送响应；测试 500 的响应内容时使用 `raise_server_exceptions=False`。若流式响应已开始后才失败，不能再改成新的 500 状态。

### 耗时与日志

| 字段 | 含义 |
| --- | --- |
| `X-Request-ID` | 服务端生成的 UUID，用来关联一次请求的响应和日志 |
| `X-Process-Time-Ms` | 从进入观测中间件到开始响应的耗时，单位毫秒 |
| 日志 `duration_ms` | 下游 ASGI 调用结束时的耗时，通常包括响应体发送阶段 |

两种耗时测量点不同，流式响应时尤其明显；均不代表用户端完整网络耗时。使用 `perf_counter` 计算时间差。

日志记录方法、路由模板、状态码、耗时和请求 ID。比如 `/items/12` 记为 `/items/{item_id}`，避免记录具体路径参数；不记录查询串、请求体、Authorization 或 Cookie。未匹配路由与预检记为 `<unmatched>`。500 或异常使用 ERROR 级别，其他完成日志使用 INFO。

请求 ID 忽略客户端同名 Header，避免直接信任外部值。中间件实例被多个请求共享，所以请求 ID、计时和 trace 必须保存在单次调用局部变量或请求 scope 中，不能用实例字段保存。

### CORS 约定

Origin 由协议、主机和端口组成。`localhost` 与 `127.0.0.1` 不同，HTTP 与 HTTPS 不同，端口不同也不同。

本例允许以下来源：

```text
http://localhost:5173
http://127.0.0.1:5173
```

| 配置 | 取值 |
| --- | --- |
| `allow_credentials` | true，演示允许浏览器凭证请求；本阶段没有登录接口 |
| `allow_methods` | GET、POST |
| `allow_headers` | Content-Type、X-CSRF-Token，另有中间件支持的安全请求头 |
| `expose_headers` | X-Request-ID、X-Process-Time-Ms、X-Middleware-Order |
| `max_age` | 600 秒，浏览器可缓存预检结果的时间 |

凭证场景使用明确来源，不使用 `*`。应用工厂也拒绝来源通配符；可用 `create_app(allow_origins=[...])` 替换白名单，传空列表表示不允许任何跨域来源。生产应只保留可信前端地址。

预检是同时带 `Origin` 和 `Access-Control-Request-Method` 的 OPTIONS 请求。允许时返回 200，不允许来源、方法或请求头时返回 400。只有 Origin 的 OPTIONS 不是预检，会继续进入路由。

普通跨域请求不一定先预检。对于不允许的 Origin，本例通常仍执行接口，但不返回 `Access-Control-Allow-Origin`，浏览器不会把结果暴露给该来源的 JavaScript。curl、脚本和其他服务不遵守浏览器 CORS 访问限制。

**CORS 不是接口鉴权、服务器防火墙或 CSRF 防护。** 不能靠它阻止所有跨站请求产生副作用；Cookie 身份验证仍需 Stage 15 的 CSRF 等防护。浏览器携带跨域 Cookie 还受 fetch 的 credentials 选项、Cookie 的 SameSite/Secure 及浏览器策略约束，仅配置 CORS 不够。

参考：[FastAPI 中间件](https://fastapi.tiangolo.com/tutorial/middleware/)、[CORS](https://fastapi.tiangolo.com/tutorial/cors/)。

## 运行命令

在仓库根目录激活已有环境，再进入本阶段：

```powershell
.\.venv\Scripts\Activate.ps1
cd stage16_middleware_cors
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload
```

不需要数据库或配置文件。访问 `http://127.0.0.1:8000/docs`。请求完成后，终端可以看到 `stage16.requests` 日志；Uvicorn 还会输出自己的访问日志，二者不是重复执行接口。

## 测试命令

在本阶段目录运行：

```powershell
python -m pytest -q
```

使用独立应用测试响应头、日志字段、顺序、跨域白名单、预检拒绝、404/409/422/500、异常传播与并发隔离。测试客户端只检查 HTTP 响应，不会替浏览器执行 CORS 拦截；浏览器行为需要另外验证。

验证记录（2026-10-12）：`27 passed`；有一条 Starlette TestClient 使用 httpx 的依赖弃用提示，不影响测试通过。

## 示例请求

查看基本响应头及中间件顺序：

```powershell
curl.exe -i http://127.0.0.1:8000/middleware-order
curl.exe -i -H "Origin: http://localhost:5173" http://127.0.0.1:8000/health
```

允许的跨域预检：

```powershell
curl.exe -i -X OPTIONS -H "Origin: http://localhost:5173" -H "Access-Control-Request-Method: POST" -H "Access-Control-Request-Headers: content-type,x-csrf-token" http://127.0.0.1:8000/items
```

请求不允许的方法，以及不允许来源的普通请求：

```powershell
curl.exe -i -X OPTIONS -H "Origin: http://localhost:5173" -H "Access-Control-Request-Method: DELETE" http://127.0.0.1:8000/items
curl.exe -i -H "Origin: https://evil.example" http://127.0.0.1:8000/health
```

检查异常路径：

```powershell
curl.exe -i -H "Origin: http://localhost:5173" http://127.0.0.1:8000/items/not-an-int
curl.exe -i -H "Origin: http://localhost:5173" http://127.0.0.1:8000/errors/unhandled
```

## 预期返回

允许来源访问 `/health` 返回 HTTP 200 和 `{"status": "ok"}`，响应头包含：

```text
Access-Control-Allow-Origin: http://localhost:5173
Access-Control-Allow-Credentials: true
Access-Control-Expose-Headers: X-Request-ID, X-Process-Time-Ms, X-Middleware-Order
Vary: Origin
X-Request-ID: 每次请求生成的32位十六进制UUID
X-Process-Time-Ms: 本次实际测量的毫秒数
```

允许的预检返回 200、`Access-Control-Allow-Methods: GET, POST` 和 `Access-Control-Max-Age: 600`，有观测响应头但没有顺序响应头。

DELETE 预检返回 400；不允许来源访问 `/health` 则仍返回 200，但没有 `Access-Control-Allow-Origin`，不要把这误认为 CORS 配置失效。

非法路径参数返回 422。`/errors/unhandled` 返回 HTTP 500：

```json
{"detail": "Internal server error"}
```

允许来源的 500 响应仍带跨域头、请求 ID 和耗时头，不回显内部异常文字。服务端会记录异常，这是演示路由的预期结果，不能把该路由直接放进真实生产应用。

## 常见错误

- 用 curl 能读到响应，浏览器却不能：curl 不执行浏览器的同源限制，检查响应 CORS 头和实际 Origin。
- 白名单有 localhost 但使用 127.0.0.1：它们是不同来源，需要明确配置。
- 浏览器能收到响应却读不到请求 ID：检查 `expose_headers`，仅添加自定义响应头还不够。
- 预检返回 400：检查请求方法和 `Access-Control-Request-Headers`，不是只有 Origin 需要匹配。
- CORS 白名单不允许 DELETE，但服务端工具仍可请求 DELETE：CORS 不限制非浏览器调用，实际支持的方法由路由决定。
- 500 没有 CORS 头：检查 CORS 是否在生成该错误响应的层之外。
- trace 混入其他请求的事件：不要把单次请求状态放在共享中间件实例字段里。
- 误把响应头耗时当作完整下载耗时：该值在开始响应时写入，不能统计后续全部传输。

## 小练习

1. 增加 PUT 接口，分别验证路由支持与 CORS 方法白名单，两者不是同一配置。
2. 调整两层顺序中间件的包装顺序，预测响应头后再运行测试。
3. 添加一个慢速流式响应，对比响应头耗时和完成日志耗时。
4. 将来源白名单迁移到 Stage 07 的配置模型，测试开发与生产的配置隔离。
