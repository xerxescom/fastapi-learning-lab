# Stage 22：日志与可观测性基础

## 本阶段学习目标

- 使用标准 `logging` 输出单行 JSON 日志。
- 用服务端生成的请求 ID 关联响应、请求日志和异常日志。
- 了解日志级别、字段白名单及敏感信息保护。
- 区分 liveness 与 readiness，并测试依赖故障和恢复。

## 核心概念

### 日志回答发生了什么

`app/logging_config.py` 只配置名为 `stage22` 的 logger，不覆盖根 logger 或 Uvicorn 的配置。配置可重复调用而不重复添加本阶段的控制台 handler；`propagate=False` 防止同一条记录再传播到根 logger 重复输出。

控制台 handler 默认写入 stderr。`JsonFormatter` 使用 `json.dumps()` 序列化，不手工拼接 JSON；时间为带时区的 UTC 时间。固定事件名配合结构化字段，比把所有信息拼成一句话更容易检索。

| 字段 | 含义 |
| --- | --- |
| timestamp / level / logger / event | 时间、级别、来源和事件名 |
| request_id | 服务端生成的 UUID，用于单次请求关联 |
| method / route | HTTP 方法与路由模板，不是原始 URL |
| status_code | 实际发送的响应状态码；发送前出错时默认 500 |
| duration_ms | ASGI 调用结束前的总耗时，单位毫秒 |
| failed | 是否有异常从应用传播出来，不等同于状态码是否为错误 |
| error_type | 异常事件中的异常类型，不含异常消息 |

`request.completed` 对每个 HTTP 请求记录一次：2xx/3xx 为 INFO，4xx 为 WARNING，5xx 或传播异常为 ERROR。这个级别策略只是教学选择，生产中应根据流量、告警和业务语义调整，不能把所有 4xx 都当成服务故障。

未处理异常还生成 `request.exception`，与完成日志共享 request_id。它们是同一请求的两个不同事件，并不是两次失败。正常处理的 409、422 不生成未处理异常事件。

### 请求关联与边界

`ObservabilityMiddleware` 使用纯 ASGI 包装，放在 FastAPI 错误响应层之外，500 响应也能带上 `X-Request-ID`。每个请求的状态保存在调用局部变量中，不放在共享中间件实例上，因此并发请求不会串号。客户端提供的 `X-Request-ID` 被忽略，避免把未经验证的输入当成可信关联信息。

如果流式响应已经发送了 200，之后才出现异常，就不能撤回响应头或再发一次 500。此时日志保留 `status_code=200`，同时记录 `failed=true` 和 ERROR 级别。这里的耗时也不是单纯的首字节耗时；后台任务等仍处于 ASGI 调用内的工作可能计入总耗时。

中间件不读取或缓冲正文，不记录查询串、Cookie、Authorization、原始路径参数。找不到路由时使用 `<unmatched>`，避免把未知路径里的秘密写入日志。格式器只允许已列出的 extra 字段，不附加任意 extra、异常消息或 traceback。

这不是通用脱敏器：事件名仍应使用代码里的固定字符串，不能把密码拼进日志消息。**保护范围仅限本阶段的应用日志与通用错误响应**。Uvicorn 默认 access log 可能记录 URL，默认 error log 可能记录异常堆栈和消息；反向代理也可能记录请求。示例保留这些独立配置以展示边界，生产环境必须分别审查，不能声称全链路已经脱敏。

### 两种健康检查

| 接口 | 目的 | 本例行为 |
| --- | --- | --- |
| `GET /health/live` | 应用是否能响应，是否需要重启 | 返回 200 和 alive，不检查外部依赖 |
| `GET /health/ready` | 当前是否适合接收业务流量 | 探针成功返回 200，失败或异常返回 503 |

外部依赖临时故障时，readiness 可以失败而 liveness 仍成功，避免通过频繁重启制造更大故障。依赖恢复后，下次 readiness 请求即可恢复成功。

应用工厂接收同步 `readiness_probe`，通过 Depends 提供给同步路由，检查在工作线程中执行。默认探针仅返回 True，**不代表已检查数据库或其他真实服务**。测试注入失败探针，无需运行数据库。

生产探针应轻量、限时，只检查必要依赖。线程池不是超时机制；真实数据库/HTTP 检查必须在对应客户端设置超时，必要时使用短期缓存，避免探针本身压垮依赖。本阶段不实现真实外部依赖、启动宽限期或资源生命周期，生命周期将在 Stage 23 学习。

日志只是可观测性的一部分：指标用于看错误率、延迟和容量趋势，分布式追踪用于关联跨服务调用。单个 request_id 不是完整的分布式 trace，本阶段不引入监控平台。

## 运行命令

在仓库根目录执行（Windows PowerShell，已有 `.venv`）：

```powershell
.\.venv\Scripts\Activate.ps1
cd stage22_logging_observability
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload
```

服务地址为 `http://127.0.0.1:8000`，接口文档为 `/docs`。无需数据库或其他服务。

若只想观察本例的结构化请求日志，可以关闭 Uvicorn 的独立 access log：

```powershell
python -m uvicorn main:app --reload --no-access-log
```

这不会关闭 Uvicorn error log，也不等于完整的生产日志安全配置。`/errors/unhandled` 是故障演示接口，不应原样公开到生产环境。

## 测试命令

在阶段目录执行：

```powershell
python -m pytest -q -p no:cacheprovider
```

验证结果：`19 passed`；当前环境有一条 Starlette TestClient 使用 httpx 的依赖弃用提示，不影响测试通过。

测试覆盖正常请求、404/409/422/500、日志级别、请求 ID、白名单格式化、依赖故障与恢复、应用实例隔离、并发关联、非 HTTP 转发，以及响应开始后的异常。测试专用 handler 采集本阶段 LogRecord，并在结束时移除，避免污染后续测试。

测试 500 响应时使用 `raise_server_exceptions=False`，否则 TestClient 会把服务器异常重新抛到测试代码。这不会改变实际服务器的异常传播机制。

## 示例请求

在另一个 PowerShell 窗口执行：

```powershell
Invoke-RestMethod 'http://127.0.0.1:8000/health/live'
Invoke-RestMethod 'http://127.0.0.1:8000/health/ready'
$response = Invoke-WebRequest -UseBasicParsing 'http://127.0.0.1:8000/items/42'
$response.Headers['X-Request-ID']
$response.Content
```

故障示例（curl.exe 会显示状态码和响应头）：

```powershell
curl.exe -i http://127.0.0.1:8000/errors/http
curl.exe -i http://127.0.0.1:8000/errors/unhandled
```

终端日志中的 request_id 应与响应头一致。readiness 故障通过测试注入探针演示，不提供公开的“切换故障状态”接口。

## 预期返回

存活检查返回 200：

```json
{"status":"alive"}
```

默认就绪检查返回 200 和 `{"status":"ready"}`；探针失败时返回 503 和 `{"status":"not_ready"}`。依赖异常的内部消息不会返回给调用方。

商品示例返回 200，正文 request_id 与 `X-Request-ID` 响应头一致：

```json
{"item_id":42,"request_id":"服务端生成的32位十六进制ID"}
```

请求完成日志类似下例（实际时间、ID、耗时会变化）：

```json
{"timestamp":"2026-10-12T10:00:00+00:00","level":"INFO","logger":"stage22","event":"request.completed","request_id":"0f6074655b504019841ab840098ce562","method":"GET","route":"/items/{item_id}","status_code":200,"duration_ms":1.25,"failed":false}
```

故障接口分别返回 409 和 500。500 的对外正文固定为：

```json
{"detail":"Internal server error"}
```

## 常见错误

- 重复调用 `basicConfig` 以为能覆盖所有日志：已有 handler 时它通常不起作用，强制覆盖又可能破坏宿主配置；本例只管理自己的 logger。
- 日志重复出现：检查 handler 是否重复添加，以及 propagate 是否又传给根 logger。
- 把原始 URL 当成路由模板：查询串和路径参数可能含敏感信息，本例只记录匹配后的路由模板。
- 认为格式器能消除所有敏感信息：固定事件名、业务记录规范、Uvicorn 和代理配置都要单独审查。
- 将数据库连接失败同时判为 liveness 失败：这可能触发无益的重启，应区分进程健康与服务就绪。
- 给探针添加很重或无超时的检查：健康检查也会消耗资源，应限制频率、超时和检查范围。
- 只看 status_code 忽略 failed：流式响应开始后出错，已发送的状态码可能仍为 200。
- 从仓库根目录收集所有阶段测试：各阶段有同名模块，应进入对应目录独立运行。

## 小练习

1. 增加业务日志事件，使用同一个 request_id 关联请求，但不记录用户输入正文。
2. 为真实 HTTP 依赖编写带客户端超时的 readiness 探针，并用 mock 验证超时返回 503。
3. 为健康检查日志实现可配置的采样策略，保留故障记录，减少高频成功探针的日志量。
4. 从 request.completed 日志统计错误率与耗时分位数，思考与专用指标系统的区别。
