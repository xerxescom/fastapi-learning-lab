# Stage 15：表单、Cookie 与 Session 基础

## 本阶段学习目标

- 用 `Form` 接收表单登录数据，区分表单和 JSON 请求体。
- 使用 `Response.set_cookie`、`Cookie` 与 `delete_cookie` 设置、读取、删除 Cookie。
- 理解 Cookie 中的会话 ID 与服务器端登录状态之间的关系。
- 演示会话轮换、过期、退出撤销和 CSRF Token 校验。
- 对比服务端 Session、签名 Cookie 与 Stage 10 的 JWT。

## 核心概念

### 表单不是 JSON

登录使用 `application/x-www-form-urlencoded`，字段为 `username`、`password`。也可以用 multipart 表单提交；两者都需要 `python-multipart` 支持。相同字段如果用 JSON 提交，不能替代表单，接口返回 422。

用户名长度为 1 到 50，密码为 1 到 128。演示账号为 `learner`，密码为 `learn-fastapi-2026`，仅用于本地教学。程序使用 Argon2 校验演示账号的密码，不把密码或哈希写入 Cookie。校验错误响应去掉原始输入，避免在 422 中回显密码。

### Cookie 是传输和存储机制

| Cookie | 内容 | 用途 | HttpOnly |
| --- | --- | --- | --- |
| `lab_session` | 随机、不可预测的会话 ID | 查询服务器端登录状态 | true |
| `lab_theme` | `light` 或 `dark` | 非敏感界面偏好，不参与鉴权 | false |

两者都设置 `Path=/`、`SameSite=lax`，不设置 Domain。浏览器按 Cookie 规则自动携带，JavaScript 通常无需手动添加 Cookie 请求头。Cookie 是客户端输入：偏好值也必须校验，不能把 `theme=admin` 当作权限。

`HttpOnly` 限制 JavaScript 直接读取会话 Cookie，但不能单独防止 CSRF 或 XSS 引发的已登录操作。`Secure` 要求通过 HTTPS 传输；本地 HTTP 演示默认关闭，生产必须启用 HTTPS 并打开该选项。

删除 Cookie 要匹配原来的名称、Path 和 Domain。本例返回 `Max-Age=0`，同时删除服务端记录；只让浏览器删 Cookie 并不等于撤销被复制的会话 ID。

### 服务端 Session 流程

1. `GET /auth/csrf`：新客户端获得匿名会话 Cookie，响应返回该会话的 CSRF Token。
2. `POST /auth/login`：提交表单、Cookie 和 `X-CSRF-Token`；成功后轮换会话 ID 与 CSRF Token，并关联用户名。
3. `GET /auth/me`：浏览器自动携带 Cookie；服务器查到已登录状态后返回用户名。
4. `POST /auth/logout`：校验 CSRF Token，删除服务端会话并清除 Cookie。匿名会话也可以退出。

会话默认存活 1800 秒，按创建时间固定到期，不因读取 `/auth/me` 或 `/auth/csrf` 自动续期。服务器也检查到期时间，不只依赖浏览器的 `Max-Age`。成功登录会创建新的有效期；过期后重新获取 CSRF Token 得到匿名会话，仍须登录。

所有修改状态的接口，包括登录、退出和偏好设置/删除，都需要与当前会话匹配的 `X-CSRF-Token`。没有有效会话返回 401，有会话但 CSRF 不匹配返回 403。登录后要使用响应中的新 Token，不能沿用匿名 Token。Token 放在 Header，而不是 URL，敏感响应设置 `Cache-Control: no-store`。

`SameSite` 是补充防护，不替代 CSRF 校验。本例没有启用跨域凭证访问；不要为不可信来源开放携带凭证的 CORS。原生 HTML 表单不能直接添加这个自定义 Header，前端通常使用同源 fetch；本阶段用 PowerShell 演示完整流程。

### Session 与 JWT

| 方案 | 客户端保存什么 | 服务端状态 | 退出与撤销 |
| --- | --- | --- | --- |
| 本阶段服务端 Session | 随机会话 ID | 用户、到期时间、CSRF Token | 删除服务端记录即可使该 ID 失效 |
| 签名 Cookie Session | 已签名的会话内容 | 基本方案可不保存 | 删除浏览器 Cookie 不一定能撤销已复制的 Cookie |
| Stage 10 JWT | 已签名的 Token | 验签本身不要求保存会话 | 通常等待过期，或增加撤销状态 |

Cookie 和 JWT 不是同一层的概念：JWT 也可以放入 Cookie，放进去后仍需考虑 CSRF。JWT 的签名不等于加密；签名 Cookie 的内容也不应假定不可读。

这里没有使用 Starlette `SessionMiddleware`，因为本阶段选择演示“服务器存状态、客户端只拿 ID”。不要把签名 Cookie 方案与服务端会话存储混为一谈。

### 模块与教学边界

`main.py` 定义接口、Cookie 和依赖；`app/config.py` 读取配置；`app/security.py` 校验固定演示账号；`app/sessions.py` 使用带锁字典保存会话。

内存存储每个实例最多保留 1000 条有效记录，新建时回收过期记录，容量已满返回 503。这不是抗滥用方案，仍需要接入层限流、登录尝试限制和容量管理。读取已过期会话时也会移除对应记录。

**仅适合单进程本地学习。** 重启或 reload 会清空状态，多 worker 和多机器不共享字典；锁只保护单个存储操作，不提供跨请求的数据库事务语义。生产应采用成熟的共享会话方案，结合持久化用户、账号停用检查、HTTPS、CSRF、安全 Cookie、限流和审计。演示账号不能用于公开部署。

参考：[FastAPI 表单](https://fastapi.tiangolo.com/tutorial/request-forms/)、[响应 Cookie](https://fastapi.tiangolo.com/advanced/response-cookies/)、[OWASP CSRF 防护](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)。

## 运行命令

在仓库根目录激活已有环境，再进入本阶段：

```powershell
.\.venv\Scripts\Activate.ps1
cd stage15_form_cookie_session
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload
```

不需要数据库或初始化脚本。文档地址为 `http://127.0.0.1:8000/docs`。在 Swagger UI 中先调用 `/auth/csrf`，再将返回 Token 填入登录接口的 `X-CSRF-Token`。

可将 `.env.example` 复制为 `.env`，或设置同名环境变量：

| 配置 | 默认值 | 约束 |
| --- | --- | --- |
| `LAB_COOKIE_SECURE` | `false` | 本地 HTTP 使用 false，HTTPS 部署使用 true |
| `LAB_SESSION_TTL_SECONDS` | `1800` | 1 到 86400 秒 |

环境变量优先于 `.env`。本阶段不使用签名密钥，因为 Cookie 只是不可预测的查表 ID，权威状态保存在服务器；这不意味着可以省略 HTTPS。

## 测试命令

在本阶段目录运行：

```powershell
python -m pytest -q
```

测试使用独立应用和独立内存存储，替换时钟检查过期边界，不需要真实等待。`TestClient` 会保留 Cookie，适合测试跨请求登录状态；它不完整模拟浏览器的 SameSite、CORS 和 CSRF 行为，不能替代浏览器安全验收。

覆盖表单校验、错误脱敏、密码错误、会话轮换、退出撤销、旧 Cookie 重放、CSRF 绑定、固定到期、Secure 标志、偏好 Cookie、容量回收和实例隔离。

验证记录（2026-10-12）：`37 passed`；有一条 Starlette TestClient 使用 httpx 的依赖弃用提示，不影响测试通过。

## 示例请求

在另一 PowerShell 窗口执行。`-SessionVariable web` 创建 Cookie 容器，后续通过 `-WebSession $web` 自动携带 Cookie：

```powershell
$base = 'http://127.0.0.1:8000'
$csrf = Invoke-RestMethod "$base/auth/csrf" -SessionVariable web
$headers = @{'X-CSRF-Token' = $csrf.csrf_token}

$login = Invoke-RestMethod "$base/auth/login" -Method Post -WebSession $web -Headers $headers -ContentType 'application/x-www-form-urlencoded' -Body @{username='learner'; password='learn-fastapi-2026'}
$headers['X-CSRF-Token'] = $login.csrf_token

Invoke-RestMethod "$base/auth/me" -WebSession $web
Invoke-RestMethod "$base/cookies/theme" -Method Post -WebSession $web -Headers $headers -ContentType 'application/x-www-form-urlencoded' -Body @{theme='dark'}
Invoke-RestMethod "$base/cookies/theme" -WebSession $web
Invoke-RestMethod "$base/cookies/theme" -Method Delete -WebSession $web -Headers $headers
Invoke-RestMethod "$base/auth/logout" -Method Post -WebSession $web -Headers $headers
```

查看 Cookie 容器：

```powershell
$web.Cookies.GetCookies([Uri]$base)
```

退出后再访问 `/auth/me` 返回 401，PowerShell 会将该 HTTP 错误显示为异常，这是预期行为：

```powershell
Invoke-RestMethod "$base/auth/me" -WebSession $web
```

## 预期返回

获取 CSRF Token 返回 200，并设置 `lab_session` Cookie：

```json
{"csrf_token": "每个会话随机生成的Token"}
```

登录成功返回 200，Token 已轮换：

```json
{"csrf_token": "新的随机Token", "username": "learner"}
```

`GET /auth/me` 返回 `{"username": "learner"}`；设置主题返回 `{"theme": "dark"}`，后续读取保持该值；删除后回到 `{"theme": "light"}`。退出返回 `{"message": "Logged out"}`。

有效会话但错误 CSRF Token 返回 403：

```json
{"detail": "Invalid CSRF token"}
```

错误凭证返回 401 和 `{"detail": "Invalid username or password"}`。匿名会话访问 `/auth/me` 返回 401；会话缺失或过期返回 401 和 `{"detail": "Session missing or expired"}`。

## 常见错误

- 用 JSON 登录返回 422：本接口声明的是 `Form`，使用表单编码。
- 登录直接返回 401：先获取 `/auth/csrf`，并保留服务端设置的 Cookie。
- CSRF 返回 403：Header 必须和当前会话匹配；登录成功后更新为新 Token。
- Swagger UI 中手填 Cookie 不生效：Cookie 由浏览器管理，先在同一站点调用 `/auth/csrf`；调试完整流程可用 PowerShell Cookie 容器。
- HTTP 下打开 `Secure` 后无法保持登录：浏览器不会按普通 HTTP 发送该 Cookie，使用 HTTPS 或仅在本地演示关闭 Secure。
- 刷新配置后登录状态丢失：reload/重启清空内存会话，这是教学存储的预期行为。
- 修改 Cookie 就能变成管理员：不能；身份来源是服务器记录，不是 Cookie 中的用户名或偏好值。
- 以为有 HttpOnly 就不需要 CSRF：浏览器仍会自动携带 Cookie，必须分别处理这两类风险。

## 小练习

1. 为 `/auth/me` 增加计数信息，先决定哪些操作属于状态修改及是否需要 CSRF。
2. 将固定账号替换为 Stage 09 的用户表，确保账号停用后已有会话也无法继续访问。
3. 设计“退出所有设备”，比较单个会话撤销与用户级撤销的区别。
4. 在扩展分支尝试成熟共享会话存储，验证多 worker、过期清理和并发退出行为。
