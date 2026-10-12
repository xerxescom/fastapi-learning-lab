# Stage 17：后台任务与邮件发送模拟

## 本阶段学习目标

- 通过 `BackgroundTasks.add_task` 在响应发送后执行轻量工作。
- 传递任务参数，查询 `pending/running/succeeded/failed` 状态。
- 区分注册成功、任务安排成功与邮件发送成功。
- 理解进程内后台任务与持久化任务队列的边界。

## 核心概念

### 注册后安排通知

`POST /users` 接收用户名和邮箱，创建内存注册资料与通知记录，调用 `background_tasks.add_task(...)`，再返回 HTTP 201。后台任务随后生成欢迎邮件并写入模拟发件箱，全程不连接 SMTP、不发送真实邮件。

本阶段只模拟注册资料登记，不收集密码，也不实现账号认证。完整密码注册请回看 Stage 09。用户名去除首尾空白后，必须为 3 到 30 位小写字母、数字或下划线，且以字母开头；邮箱使用 `EmailStr` 校验，不进行邮箱所有权验证。

用户名或邮箱重复返回 409，非法输入返回 422，均不会安排新的通知。邮箱重复判断忽略大小写，属于本教学应用的业务约定。

模块职责：`main.py` 定义接口和应用工厂；`app/schemas.py` 定义模型；`app/state.py` 管理内存状态；`app/tasks.py` 执行通知任务。

### 响应与任务生命周期

```text
接收注册资料 -> 创建用户和 pending 通知 -> 安排任务
             -> 发送 201 响应体
             -> 执行任务：running -> succeeded 或 failed
```

响应中的通知是安排任务时的快照，所以状态为 `pending`、`attempts=0`。之后查询通知时可能已完成。返回 201 表示注册资料创建成功，不代表欢迎邮件已经送达。

`BackgroundTasks` 是响应关联的进程内任务，不是独立 worker。同步 `def` 任务通过线程池执行；异步任务应使用真正的异步 I/O，不能在 `async def` 内直接调用阻塞函数。添加多个任务时按添加顺序执行，不自动并行；未处理异常会阻止后续任务继续执行。

响应发送在先，不等于任务有持久化保障，也不保证客户端网络延迟。服务进程仍需完成后台调用，线程池和资源仍可能被占用。`TestClient` 和普通 ASGI 测试传输通常等整个应用调用结束，所以一次测试请求返回时任务可能已完成，不能据此判断生产 HTTP 是否提前响应。

测试中的生命周期用例让发送器等待事件，确认 ASGI 响应体已发送、通知处于 `running`，再释放发送器，避免依赖睡眠时间断言。

### 任务参数与失败

任务接收通知 ID、邮箱和用户名等值，不复用 `Request`、`UploadFile` 或请求作用域数据库会话。以后整合数据库时，通常传记录 ID，在任务内创建并关闭独立会话，并先完成注册事务再安排任务。

本例保留共享内存状态对象和发送函数，是为了教学及测试注入；它们不是请求结束即释放的资源。模型使用不可变快照，字典和发件箱操作带锁，但锁不提供跨进程事务。

默认发送器收到 `fail@example.com` 时故意失败，便于观察失败状态。任务捕获发送异常，记录通用错误 `Notification delivery failed`，只在日志中记录通知 ID，不输出邮箱、邮件正文或内部异常详情。失败不会回滚用户，也不能把已发送的 201 改成 500。

`attempts` 当前最多为 1，没有自动重试。相同任务 ID 只有在 `pending` 时才能启动，避免本实例重复调用已完成或失败任务；这不是跨进程幂等或“恰好一次”交付保证。进程在发送成功与写入状态之间崩溃等情况，需要持久化设计处理。

### 使用边界

每个应用实例独立保存用户、通知和发件箱，最多登记 1000 个用户；达到上限返回 503。重启或 reload 后数据清空，多 worker/多机器不共享状态。

**所有查询接口都没有鉴权，仅供本地学习。** `/demo/outbox` 和用户资料包含邮箱等信息，不能直接部署到公网。真实服务需要身份权限、限流、邮箱验证、日志策略和数据保留规则。

轻量、短时、允许失败丢失的附带工作可以使用 `BackgroundTasks`。涉及支付、必须送达的通知、长耗时计算、定时调度、重试和多 worker 调度时，应考虑 Celery 等成熟任务队列，以及持久化任务记录、幂等和监控。引入队列本身也不自动解决“数据库提交与任务发布”的一致性，综合项目可进一步学习事务 outbox。

本阶段不引入 Redis、Celery 或真实邮件凭证。参考：[FastAPI Background Tasks](https://fastapi.tiangolo.com/tutorial/background-tasks/)。

## 运行命令

在仓库根目录激活已有环境，再进入本阶段：

```powershell
.\.venv\Scripts\Activate.ps1
cd stage17_background_tasks
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload
```

无需数据库、初始化脚本或环境变量。访问 `http://127.0.0.1:8000/docs`，终端会输出通知成功或失败日志。

## 测试命令

在本阶段目录运行：

```powershell
python -m pytest -q
```

每个测试使用独立的内存状态；可向 `create_app(state=..., sender=...)` 注入发送器检查参数或模拟阻塞。覆盖任务触发、参数、响应发送顺序、失败状态、重复注册、重复任务、任务顺序、未捕获异常、容量和实例隔离。

验证记录（2026-10-12）：`31 passed`。本机沙箱首次运行还提示 pytest 缓存目录无写入权限；禁用缓存重跑后，仅有一条 Starlette TestClient 使用 httpx 的依赖弃用提示，不影响测试通过：

```powershell
python -m pytest -q -p no:cacheprovider
```

## 示例请求

在另一个 PowerShell 窗口执行：

```powershell
$base = 'http://127.0.0.1:8000'
$result = Invoke-RestMethod "$base/users" -Method Post -ContentType 'application/json' -Body '{"username":"learner","email":"learner@example.com"}'
$result | ConvertTo-Json -Depth 5
Invoke-RestMethod "$base/notifications/$($result.notification.id)"
Invoke-RestMethod "$base/users/$($result.user.id)"
Invoke-RestMethod "$base/demo/outbox"
```

模拟发送失败：

```powershell
$failed = Invoke-RestMethod "$base/users" -Method Post -ContentType 'application/json' -Body '{"username":"failed_user","email":"fail@example.com"}'
Invoke-RestMethod "$base/notifications/$($failed.notification.id)"
Invoke-RestMethod "$base/users/$($failed.user.id)"
```

通知可能尚在执行，可再次查询；不需要等待任务完成后才创建下一个用户。再次提交相同用户名或邮箱会返回 409，PowerShell 将非成功 HTTP 状态显示为异常。

## 预期返回

首次注册返回 HTTP 201，随机通知 ID 每次不同：

```json
{
  "user": {"id": 1, "username": "learner", "email": "learner@example.com"},
  "notification": {
    "id": "fc544c26-90f7-440a-8bc1-aeb02c901315",
    "user_id": 1,
    "status": "pending",
    "attempts": 0,
    "error": null
  }
}
```

任务成功后，查询通知得到 `status=succeeded`、`attempts=1`、`error=null`。模拟发件箱包含：

```json
[
  {
    "notification_id": "fc544c26-90f7-440a-8bc1-aeb02c901315",
    "recipient": "learner@example.com",
    "subject": "Welcome to FastAPI Learning Lab",
    "body": "Hello learner, your demo registration is complete."
  }
]
```

失败示例的注册仍返回 201，用户仍存在。任务完成后状态为 `failed`、`attempts=1`、`error="Notification delivery failed"`，发件箱不会新增该邮件。

访问不存在的用户或通知返回 404；错误类型的 ID 返回 422。

## 常见错误

- 在路由里直接调用发送函数：会阻塞响应，不是后台执行；使用 `background_tasks.add_task`。
- 写成 `add_task(send_welcome_email(...))`：这是立即调用函数；应传函数本身及参数。
- 用 `TestClient` 总耗时判断是否提前响应：客户端会等待应用后台调用结束，应测试发送顺序或使用真实 HTTP。
- 返回 201 就认为邮件成功：注册结果和发送结果是两个阶段，查询通知状态确认。
- 失败后看不到 500：响应已发送，本例将失败记录在通知中，这是预期行为。
- 发送失败后重新调用任务却没重试：本例只允许 pending 状态启动，重试需要另外设计状态转换与幂等。
- reload 后找不到任务：内存状态不持久化，后台任务也不是可靠队列。
- 把请求数据库会话传给任务：请求资源可能已被清理，应在任务内重新获取资源。

## 小练习

1. 增加审计任务，验证多个任务的顺序，以及前一个任务失败后的策略。
2. 设计带上限的显式重试，先定义重复发送风险、状态转换和幂等规则。
3. 使用 SQLite 保存通知状态，演示重启后如何识别未完成任务，而不是假定它们自动恢复。
4. 将此流程接入 Stage 09 的真实注册接口，考虑事务提交、任务安排与错误返回之间的一致性。
