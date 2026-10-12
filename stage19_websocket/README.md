# Stage 19：WebSocket 入门

## 本阶段学习目标

- 完成 WebSocket 握手、接受连接、双向收发和关闭。
- 管理多条连接，将聊天消息广播给在线客户端。
- 校验文本 JSON 消息，处理非法输入、断开和发送失败。
- 使用 TestClient 与真实网络客户端分别验证协议行为。

## 核心概念

### WebSocket 与 HTTP

普通 HTTP 接口按请求返回响应；WebSocket 先进行 HTTP 握手升级，再在同一条连接上双向交换消息，服务端可以主动推送。常见用途包括聊天、协作状态、实时行情和任务进度；只需服务端单向推送时也可评估 SSE。

本例使用 `/ws/chat?name=alice`。服务端先检查参数与浏览器 Origin，再 `accept()`，注册连接并发送 welcome，随后循环接收文本消息。客户端正常断开、网络断开或服务端关闭后，在 `finally` 中移除连接。

WebSocket 路由不列入 OpenAPI，Swagger UI 不能直接测试其消息收发。对该路径发送普通 HTTP GET 会返回 404，不代表 WebSocket 路由不存在。

### 单房间协议

`name` 为 3 到 20 位小写字母、数字或下划线，且以字母开头。同名连接允许存在，服务器分配不同的随机 ID；昵称不是经过认证的用户身份。

客户端只发送文本 JSON：

```json
{"type": "chat", "text": "Hello FastAPI!"}
```

`text` 去除首尾空白后长度为 1 到 200 个字符，不接受多余字段。整条接收消息按 UTF-8 编码最多 4096 字节，字符数与字节数是两种限制。ASGI 接收的是完整消息，不应把这个业务限制误认为只限制一个底层分片。

服务器会给包括发送者在内的所有在线连接广播：

```json
{"type": "chat", "sender_id": "服务器分配的ID", "name": "alice", "text": "Hello FastAPI!"}
```

发送者 ID 和名称来自服务器的连接记录，不能通过消息字段伪造。前端展示聊天内容时应作为文本渲染，不要使用 `innerHTML`。

### 连接管理与失败

`main.py` 定义协议处理；`app/chat.py` 定义消息模型和连接管理器；`demo_client.py` 连接两个真实客户端验证广播。

每个应用实例最多 20 条连接，不保存聊天历史，也不发送加入/离开广播。welcome 中的 `online` 只是当时的连接数快照，不会持续更新；可通过 HTTP `/health` 查看当前实例在线数量。

同一事件循环中的连接表删除没有 await，便于在取消清理时完成；发送操作用锁串行化，避免并发广播交错写入同一连接。广播使用连接快照，发送失败或超过一秒的连接会被移除，并尝试关闭，其他连接继续收消息。

串行广播保持各客户端所见消息的顺序，但慢客户端仍可能在超时前拖慢其他客户端。本例不是高吞吐方案；生产通常需要有界发送队列、背压、限流、超时策略和监控。不要简单为每条消息无限创建并发发送任务。

### 关闭与安全边界

| 情况 | 行为 |
| --- | --- |
| name 缺失/非法，或 Origin 不允许 | 握手前拒绝；真实服务器通常返回 HTTP 403 |
| 已连接后消息模型或 JSON 非法 | 关闭码 1008 |
| 二进制消息 | 关闭码 1003 |
| 完整文本消息超过业务大小限制 | 关闭码 1009 |
| 连接容量已满 | accept 后关闭，关闭码 1013 |
| 广播发送失败或超时 | 移除连接，尝试用 1013 关闭 |
| 客户端正常退出 | 清理连接，不影响其他连接 |

握手前的关闭不是已经建立连接后的 WebSocket 关闭帧。TestClient 能观察 ASGI 的关闭码，真实客户端在握手失败时一般看到 HTTP 状态，浏览器未必暴露具体拒绝原因。

浏览器 Origin 白名单默认是 `http://127.0.0.1:8000` 和 `http://localhost:8000`。WebSocket 不使用普通 Fetch CORS 预检，配置 `CORSMiddleware` 不能替代 WebSocket Origin 校验。

命令行客户端可以不发送 Origin，本例允许这种连接。Origin 可被非浏览器客户端伪造，不是鉴权。**本例无身份认证，仅供本地学习，不能作为公开聊天室直接部署。** 使用 Cookie 鉴权时，还需检查 WebSocket 的 Origin 和会话有效性，防范跨站 WebSocket 劫持；不要把长期 Token 放进会被日志记录的 URL。

生产使用 `wss://`，配置反向代理 Upgrade、空闲超时、协议层消息上限、连接配额、心跳与重连策略。应用大小校验发生在消息已接收后，不能代替协议层和网络层的资源限制。

连接列表只存在一个进程，重启、reload 或服务退出会断开连接；多 worker/多机器不共享广播，需要额外的共享消息分发方案。广播没有持久化、离线补发或“恰好一次”保证。

参考：[FastAPI WebSocket](https://fastapi.tiangolo.com/advanced/websockets/)、[Starlette WebSocket API](https://starlette.dev/websockets/)、[WebSocket 测试](https://starlette.dev/testclient/)。

## 运行命令

在仓库根目录激活已有环境，再进入本阶段：

```powershell
.\.venv\Scripts\Activate.ps1
cd stage19_websocket
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000 --ws-max-size 4096
```

`websockets` 为 Uvicorn 提供 WebSocket 协议支持，也供演示客户端使用。`--ws-max-size` 是服务器协议层限制；与应用业务校验一起使用，而不是互相替代。HTTP 文档在 `http://127.0.0.1:8000/docs`。

## 测试命令

在本阶段目录运行，无需启动服务：

```powershell
python -m pytest -q -p no:cacheprovider
```

覆盖 welcome、广播、同名独立连接、正常断开、参数和 Origin、消息校验、二进制拒绝、字节边界、容量复用、慢连接、发送失败和并发广播顺序。使用独立应用隔离连接表。

TestClient 的内存通道不能完整模拟真实 TCP、协议分片、代理或浏览器安全策略，另有真实网络客户端用于集成验证。

验证记录（2026-10-12）：`34 passed`；有一条 Starlette TestClient 使用 httpx 的依赖弃用提示，不影响测试通过。

## 示例请求

服务启动后，在另一个已激活相同环境的终端进入本阶段目录：

```powershell
python demo_client.py
```

客户端建立 alice 和 bobby 两条连接，打印 welcome，由 alice 发送一条消息，两者都收到广播后正常退出。使用其他端口时：

```powershell
python demo_client.py --url ws://127.0.0.1:8001
```

也可以打开 `http://127.0.0.1:8000/docs`，在该页面浏览器开发者工具控制台执行：

```javascript
const alice = new WebSocket('ws://127.0.0.1:8000/ws/chat?name=alice');
alice.onmessage = event => console.log('alice', JSON.parse(event.data));
alice.onclose = event => console.log('closed', event.code, event.reason);
```

看到 welcome 后发送：

```javascript
alice.send(JSON.stringify({type: 'chat', text: '你好 FastAPI'}));
```

可在第二个同源页面建立 bobby 连接观察广播。结束时：

```javascript
alice.close(1000, 'done');
```

不要从任意其他网站的控制台连接：浏览器会携带那个网站的 Origin，服务器会拒绝。更换浏览器页面端口时需同步调整 `create_app(allowed_origins=...)` 的白名单。

## 预期返回

首个连接收到 welcome，ID 每次不同：

```json
{"type": "welcome", "client_id": "a9df09deddd44d69bf9e33e13590ae36", "name": "alice", "online": 1}
```

bobby 连接的 welcome 中 `online=2`。alice 发送消息后，两者都收到相同的 chat 事件：

```json
{"type": "chat", "sender_id": "a9df09deddd44d69bf9e33e13590ae36", "name": "alice", "text": "Hello FastAPI!"}
```

不合规消息关闭发送者，不广播错误内容；其他客户端仍可继续聊天。全部退出并完成清理后，`GET /health` 返回 `{"status":"ok","online":0}`。

## 常见错误

- 用 curl 普通 GET 测试得到 404：需要 WebSocket 客户端完成升级握手。
- 服务提示没有支持的 WebSocket 库：安装本阶段 requirements，并确认启动的是同一 Python 环境。
- 浏览器握手失败：检查 name、Origin 和代理 Upgrade 配置，不要只检查 CORS。
- 建立连接后马上发送报错：等待 `open`/welcome，连接仍在 CONNECTING 时不能发送。
- 发送普通字符串就被关闭：协议要求 JSON 对象，且包含 `type=chat` 和非空 text。
- 二进制 JSON 被拒绝：本例只接受文本帧中的 JSON，不提供二进制协议。
- 断开重连后 ID 不同：ID 对应一次连接，不是登录用户身份。
- 多 worker 下部分人收不到消息：连接表不共享，不应把本地广播当成分布式广播。
- 依赖 welcome 的在线人数一直变化：它是快照，本例没有成员变更推送。

## 小练习

1. 增加加入/离开事件，先定义事件顺序及断开时的发送策略。
2. 引入房间 ID，让广播只发送给同房间连接，并补充隔离测试。
3. 用有界队列为每个连接建立独立发送循环，设计队列满时的背压策略。
4. 接入 Stage 15 的认证，处理握手、会话到期与主动撤销，而不是仅验证昵称。
