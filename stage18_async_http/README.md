# Stage 18：异步接口与外部 HTTP 调用

## 本阶段学习目标

- 使用 `async def` 和 `await` 调用外部 HTTP 服务。
- 在应用生命周期中复用 `httpx.AsyncClient`，关闭时释放连接。
- 区分连接、读取、写入、连接池等待和整体调用超时。
- 校验上游响应，统一映射错误，不透传内部信息。
- 用 `MockTransport` 测试外部服务，不依赖公网。

## 核心概念

### 同步与异步

主应用的 `GET /products/{product_id}` 使用 `await catalog.get_product(...)`。等待网络 I/O 时，事件循环可以处理其他请求；这不是把单次网络请求变快，也不是自动加速 CPU 密集计算。

FastAPI 的同步 `def` 路由通常在线程池执行。异步路由中应配合异步库；直接使用阻塞 HTTP 客户端、`time.sleep` 或重计算会阻塞事件循环。已有阻塞调用应明确在线程池或其他合适执行器处理，而不是只把函数改名为 `async def`。

本例每次路由只查一个商品，没有隐式重试或批量并发。测试通过事件同步验证两个请求能同时等待上游，不用“耗时必须小于某个值”的脆弱断言。

### 共享 HTTP 客户端

`main.py` 的 lifespan 创建一个 `AsyncClient`，保存在应用状态中，由依赖提供给封装类；退出 lifespan 时关闭。真实网络传输可复用连接池，避免每个请求重新建立客户端。

`app/catalog.py` 封装上游协议及错误；`app/config.py` 管理配置；`demo_upstream.py` 是另一独立服务进程，提供可预测的本地上游响应。

客户端设置最大连接数 10、最大空闲连接数 5，不自动跟随重定向，且 `trust_env=False`，不隐式使用系统代理等 HTTPX 环境配置。企业代理或自定义 CA 需求应显式配置，而不是关闭 TLS 校验。

上游地址只来自服务配置，用户只能传受限的整数 ID，不能提交任意 URL。配置拒绝 URL 用户名、密码、查询串和片段；重定向不继续访问其他目标。这不等于完整 SSRF 防护，生产仍需可信目标白名单及出站网络限制。本地演示有意使用回环地址。

### 超时与错误映射

`httpx.Timeout(1)` 为 connect、read、write、pool 四个阶段分别设置一秒。读取超时是等待数据的限制，不是整个下载必须在一秒内完成；因此还用 `asyncio.timeout(2)` 约束整体异步等待预算。它是协作式取消，不是能够抢占同步 CPU 计算的硬期限。

| 情况 | 主应用响应 |
| --- | --- |
| 上游 200 且数据有效 | 200，返回白名单商品字段 |
| 上游商品 404 | 404，`Product not found` |
| 上游其他状态，包括 3xx、429、5xx | 502，不透传正文和内部 Header |
| 连接、读取、写入或整体等待超时 | 504，`Upstream request timed out` |
| 等待连接池超时 | 503，`Upstream connection pool is busy` |
| 连接错误、读取错误或协议错误 | 502，`Unable to reach upstream service` |
| 内容类型、JSON、字段或商品 ID 不符合契约 | 502，`Invalid upstream response` |
| 响应内容超过示例上限 | 502，`Upstream response is too large` |
| 路径参数非法 | 422，不调用上游 |

上游 JSON 只接受 `application/json`，可以带 charset 参数。读取时分块收集解码后的响应内容，累计超过 64 KiB 就拒绝；正常、错误和超时路径都通过上下文管理器释放响应资源。这是小型可信目录接口的教学限制，不是完整的压缩炸弹或恶意流量防护方案。

商品模型严格检查 ID、名称和价格，拒绝字符串冒充数值、负价格以及 NaN/Infinity，并确认返回 ID 与请求相同。多余上游字段不会出现在输出中。价格用浮点数仅供示例，真实金额通常使用定点或最小货币单位整数。

不自动重试避免隐藏额外延迟；后续需要重试时，应定义可重试错误、总预算、退避、最大次数与幂等规则。不要对所有失败盲目重试。

参考：[HTTPX 异步调用](https://www.python-httpx.org/async/)、[超时](https://www.python-httpx.org/advanced/timeouts/)、[异常分类](https://www.python-httpx.org/exceptions/)、[测试传输](https://www.python-httpx.org/advanced/transports/)、[FastAPI 异步测试](https://fastapi.tiangolo.com/advanced/async-tests/)。

## 运行命令

在仓库根目录激活已有环境并安装依赖：

```powershell
.\.venv\Scripts\Activate.ps1
cd stage18_async_http
python -m pip install -r requirements.txt
```

在本阶段目录启动本地上游：

```powershell
python -m uvicorn demo_upstream:app --host 127.0.0.1 --port 9001
```

另开一个已激活相同环境的终端，在本阶段目录启动主应用：

```powershell
python -m uvicorn main:app --reload --port 8000
```

主应用文档地址为 `http://127.0.0.1:8000/docs`，上游文档地址为 `http://127.0.0.1:9001/docs`。不需要数据库，不调用公网 API。只启动主应用时，`/health` 仍返回 200，但商品查询会返回 502；该健康检查不表示上游可用。

可将 `.env.example` 复制为 `.env`，或设置同名环境变量：

| 配置 | 默认值 | 约束 |
| --- | --- | --- |
| `LAB_UPSTREAM_BASE_URL` | `http://127.0.0.1:9001/` | HTTP/HTTPS 地址，不带凭证、查询串和片段 |
| `LAB_HTTP_TIMEOUT_SECONDS` | 1 | 大于 0 且不超过 30，必须有限 |
| `LAB_REQUEST_DEADLINE_SECONDS` | 2 | 大于 0 且不超过 60，必须有限 |

环境变量优先于 `.env`。允许带基础路径，如 `https://catalog.example/api/`；使用相对路径 `products/1` 保留该前缀。更换上游端口时，同时修改配置。

## 测试命令

在本阶段目录执行，不需要启动任何服务：

```powershell
python -m pytest -q -p no:cacheprovider
```

禁用缓存可避免此前沙箱的缓存目录权限问题，普通本地环境也可直接使用 `python -m pytest -q`。

异步测试使用 pytest 的 AnyIO 插件并固定 asyncio 后端，无需额外安装 pytest-asyncio。通过 `MockTransport` 模拟上游，使用 `ASGITransport` 调用主应用。`ASGITransport` 不自动运行 lifespan，因此测试显式进入 `application.router.lifespan_context(application)`，保证资源在同一事件循环创建和使用。

覆盖请求地址和超时参数、客户端复用及关闭、错误状态映射、传输异常、整体取消、响应内容校验、输入边界、并发等待和配置校验。Mock 不能证明真实 TCP 连接复用或模拟所有网络超时，仍需真实 HTTP 集成检查。

验证记录（2026-10-12）：`43 passed`，无测试警告。

## 示例请求

两个服务启动后：

```powershell
curl.exe -i http://127.0.0.1:8000/products/1
curl.exe -i http://127.0.0.1:8000/products/2
curl.exe -i http://127.0.0.1:8000/products/3
curl.exe -i http://127.0.0.1:8000/products/4
curl.exe -i http://127.0.0.1:8000/products/99
curl.exe -i http://127.0.0.1:8000/products/0
```

对应演示行为：商品 1 正常；2 返回非法价格；3 返回 503；4 延迟三秒，触发默认超时；其他 ID 返回上游 404。主应用 ID 的允许范围为 1 到 1,000,000。

## 预期返回

商品 1 返回 HTTP 200，不包含上游的 `internal_note`：

```json
{"id": 1, "name": "Keyboard", "price": 99.0}
```

商品 2 返回 HTTP 502：

```json
{"detail": "Invalid upstream response"}
```

商品 3 返回 HTTP 502，不暴露上游内部正文：

```json
{"detail": "Upstream service returned an unexpected status"}
```

商品 4 默认返回 HTTP 504：

```json
{"detail": "Upstream request timed out"}
```

商品 99 返回 HTTP 404 和 `{"detail": "Product not found"}`；商品 0 返回 422。取消主应用的等待不保证上游已停止业务操作，尤其不能把超时当作写操作一定没有成功。

## 常见错误

- 商品查询返回 502：先确认上游服务已启动、端口和基础路径正确。
- 使用 `httpx.get` 但路由标记了 async：同步网络调用仍会阻塞，使用 `await AsyncClient.get` 或异步 stream。
- 每次请求都创建客户端：失去跨请求连接池复用，应按应用生命周期管理。
- 测试提示应用状态没有 catalog：检查是否启动 lifespan；ASGITransport 不会自动代劳。
- `Task attached to a different loop`：不要跨事件循环复用已创建的异步资源，测试应在同一循环进入生命周期。
- 以为 HTTP 500 会自动抛传输异常：收到响应和连接失败是不同情况，本例显式检查状态码。
- 把上游所有错误映射成 500：应区分找不到商品、网关故障、超时和本地容量问题。
- 关闭所有超时才能“稳定”：会增加资源无限等待风险，应根据上游服务目标设置合理预算。
- 停止等待就以为对方取消了操作：本地取消与远端事务结果不是同一回事。

## 小练习

1. 增加一个只对幂等 GET 生效的有限重试，测试总预算不会被每次重试重置。
2. 设计多商品查询，显式限制并发数，并决定部分失败如何返回。
3. 给上游调用添加安全日志，避免记录 Token、凭证或完整响应正文。
4. 区分 liveness 与 readiness，设计不会因频繁检查而压垮上游的策略。
