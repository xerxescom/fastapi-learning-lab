# Stage 23：应用生命周期与资源管理

## 本阶段学习目标

- 用 `lifespan` 管理启动准备和关闭清理。
- 区分应用级共享资源和请求级资源。
- 学会通过 `app.state` 与依赖注入借用共享资源。
- 验证启动失败、正常关闭、重复启动与取消路径的资源释放。

## 核心概念

### yield 把启动与关闭放在一起

`main.py` 用 `@asynccontextmanager` 定义 lifespan，并传给 `FastAPI(lifespan=lifespan)`：

```python
@asynccontextmanager
async def lifespan(application):
    async with store_factory() as store:
        snapshot = snapshot_loader(store)
        application.state.resources = Resources(store, snapshot, uuid4().hex)
        try:
            yield
        finally:
            del application.state.resources
```

`yield` 前执行启动准备，成功后服务器才开始正常处理请求；退出时执行清理。删除 state 引用后，外层资源上下文管理器负责关闭连接，路由不负责关闭它。

本例的顺序是：

1. 创建内存 SQLite 连接。
2. 创建表并插入两条样例商品。
3. 读取、校验并加载只读商品快照。
4. 将完整资源发布到 `application.state.resources`，进入服务阶段。
5. 关闭阶段先删除共享引用，再关闭 SQLite 连接。

若第 2 步失败，`open_catalog()` 的 finally 仍关闭已创建的连接；若第 3 步失败，退出资源上下文时也会关闭连接，而且不发布半初始化的 state。错误会向服务器传播，启动应失败，而不是带着损坏的资源继续运行。

模块级的 `app = create_app()` 只构造应用，不连接数据库。导入模块、读取 OpenAPI 或运行不需要数据库的工具，不应顺带创建昂贵资源。

### 替代 startup/shutdown 事件

旧式代码通常把关联的准备与清理拆成两个事件函数：

```python
# 旧式结构示意；本阶段不注册这些事件。
@app.on_event("startup")
async def startup():
    ...

@app.on_event("shutdown")
async def shutdown():
    ...
```

本例用 lifespan 的 yield 前后替代它们，让资源获取与释放写在同一作用域内。迁移时应把成对逻辑一起搬过去，不要同时依赖两套机制：指定 lifespan 后，不应期待旧事件处理器仍照常执行。

### 共享资源与请求依赖

`Resources` 包含共享连接包装器、只读快照和一个生命周期 ID。`get_resources()` 从当前应用的 state 获取它，各路由通过 `Depends` 借用同一实例。

- `/products` 返回启动时加载的商品快照。
- `/products/{product_id}` 通过共享连接查询单个商品。
- `/runtime` 显示生命周期 ID、快照数量和连接状态，不公开数据库凭据。
- `/health/live` 只检查应用可响应；`/health/ready` 判断资源是否已发布且未关闭。

同一生命周期的多次请求得到相同 instance_id；同一应用顺序启动两次，或两个独立应用启动，会得到不同连接和 ID。state 只在当前进程内共享，不是跨 worker 的全局存储。不要为同一个应用并行或嵌套启动多个 lifespan。

快照使用 tuple 和冻结的 Pydantic 模型，避免正常业务代码误改它。它不是实时缓存：数据库发生变化后不会自动刷新。本例没有写接口、缓存失效或持久化需求，重启后恢复样例数据。

### 同步资源与异步生命周期

lifespan 是异步上下文，并不意味着其中的普通 SQLite 调用自动变成异步 I/O。本例数据库很小，只在启动时做少量同步准备；实际慢速初始化应采用异步驱动，或明确放到工作线程，避免阻塞事件循环。

同步路由由框架在线程池执行，因此连接使用 `check_same_thread=False`，再通过 Lock 串行化访问。关闭线程检查不是并发安全方案，Lock 和单生命周期所有权同样重要。这个单连接教学方案不能代替生产项目的连接池、每请求 Session 与事务管理，相关结构可回顾 Stage 08 和 Stage 20。

多个不同资源需要统一管理时，可以使用 `AsyncExitStack` 按获取顺序注册清理、按相反顺序释放。本阶段只有一个拥有关闭行为的连接，直接使用嵌套上下文管理器即可。

finally 能覆盖正常退出和可传播的异常/取消，但不能保证断电、强制杀进程时执行。生产系统仍需要服务器的优雅关闭时间、正确的进程信号和可恢复的数据设计。本例取消测试验证的是进入 lifespan 后收到取消异常的清理路径，不等于所有异步驱动在任意取消时刻都能自动安全关闭。

## 运行命令

在仓库根目录执行（Windows PowerShell，已有 `.venv`）：

```powershell
.\.venv\Scripts\Activate.ps1
cd stage23_lifespan
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload
```

服务地址为 `http://127.0.0.1:8000`，文档为 `/docs`。SQLite 来自 Python 标准库，无需数据库服务、初始化命令或磁盘数据库文件。

Uvicorn 默认会运行 ASGI lifespan。不要用 `--lifespan off` 启动本例，否则依赖资源的接口会返回 503。`--reload` 重载时会创建新资源并重置样例数据；多个 worker 也各自拥有一份内存数据库。

## 测试命令

在阶段目录执行：

```powershell
python -m pytest -q -p no:cacheprovider
```

验证结果：`21 passed`。当前环境有一条 Starlette TestClient 使用 httpx 的依赖弃用提示，不影响测试通过。

测试重点包括：工厂不提前建连接、启动准备、请求间复用、关闭后的连接不可用、初始化与快照加载失败清理、再次启动、并发查询、取消清理，以及关闭后的 503。

同步客户端要使用上下文管理器：

```python
with TestClient(create_app()) as client:
    assert client.get("/products").status_code == 200
```

仅构造 `TestClient(app)` 不等于执行生命周期。`httpx.ASGITransport` 也不会自动启动 lifespan，异步测试需要显式管理：

```python
async with application.router.lifespan_context(application):
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=application), base_url="http://test"
    ) as client:
        response = await client.get("/products")
```

这些是测试用的生命周期控制方式，不应在每次真实请求中重新进入 lifespan。真实运行时由 ASGI 服务器管理启动和关闭。

## 示例请求

在另一个 PowerShell 窗口执行：

```powershell
Invoke-RestMethod 'http://127.0.0.1:8000/health/ready'
Invoke-RestMethod 'http://127.0.0.1:8000/runtime'
Invoke-RestMethod 'http://127.0.0.1:8000/products'
Invoke-RestMethod 'http://127.0.0.1:8000/products/1'
Invoke-RestMethod 'http://127.0.0.1:8000/runtime'
```

两次 runtime 的 instance_id 应相同；重启服务后应改变。使用 Ctrl+C 请求服务器优雅关闭，而不是通过业务接口销毁共享资源。

## 预期返回

就绪检查返回 200：

```json
{"status":"ready"}
```

runtime 返回 200，instance_id 的具体值每次启动不同：

```json
{"instance_id":"0f6074655b504019841ab840098ce562","cached_products":2,"store_closed":false}
```

商品列表返回 200：

```json
[{"id":1,"name":"Keyboard","price_cents":9900},{"id":2,"name":"Mouse","price_cents":4900}]
```

查询不存在的正整数 ID 返回 404 和 `{"detail":"Product not found"}`，非法 ID 返回 422。测试中刻意不启动 lifespan 或在关闭后请求时，就绪检查返回 503 和 `{"status":"not_ready"}`，资源接口返回 503 和 `{"detail":"Application resources unavailable"}`。

正常 Uvicorn 启动失败时不会开始服务，正常关闭后也不会继续接收请求；以上关闭后的 HTTP 检查是进程内测试，用来验证清理状态，并非生产服务器会在关闭后继续提供 503。

## 常见错误

- 在模块导入时建立连接：会让测试收集、工具导入与 worker 启动产生难以控制的副作用。
- 在每个请求里创建、关闭应用共享连接：破坏复用，也可能导致其他请求使用已关闭的连接。
- 只在 yield 后直接写 close：若上下文主体抛出异常，清理可能被跳过，应使用 finally 或资源上下文管理器。
- 初始化一半就把 state 发布出去：后续准备失败时，容易留下不可用引用；本例全部准备成功后才发布。
- 认为 async def 会让同步数据库查询自动异步：阻塞调用仍会阻塞当前线程。
- 认为 `check_same_thread=False` 等于线程安全：它仅关闭线程限制，仍需正确的并发控制与所有权设计。
- 测试里忘记进入客户端上下文：没有执行启动逻辑，就拿不到共享资源。
- 把内存快照当成跨进程缓存：每个 worker 独立初始化，写入和失效需要另外设计。

## 小练习

1. 增加启动配置校验，让非法配置阻止启动，并断言已创建的资源仍被关闭。
2. 把商品快照替换为真正的异步上游加载，加入客户端超时和加载失败清理测试。
3. 引入第二个资源，用 AsyncExitStack 验证后创建的资源先释放。
4. 给启动阶段记录耗时与失败日志，结合 Stage 22 思考哪些初始化信息可以公开。
