# Stage 25：综合项目 Mini Task API

## 本阶段学习目标

把前面学过的配置、数据库、依赖注入、认证授权、CRUD、分页、异常处理、文档和测试组织成一个独立后端项目。业务选择个人任务管理，保持真实的用户边界，不为了展示功能引入无关服务。

完成后可以独立走通：注册用户 -> 表单登录 -> 获取 JWT -> 创建任务 -> 分页查询 -> 更新任务 -> 删除任务，并验证另一个用户无法读取或修改这些任务。

## 核心概念

### 项目结构与请求流

```text
stage25_mini_api/
  main.py                 应用工厂、lifespan、健康检查
  init_db.py              显式初始化数据库
  manage_user.py          受控的角色管理命令
  app/config.py           环境配置与校验
  app/database.py         Engine 与请求级 Session
  app/models.py           User、Task 数据库模型
  app/schemas.py          输入、公开输出与泛型响应模型
  app/security.py         Argon2 与 JWT
  app/dependencies.py     当前用户、管理员依赖
  app/services.py         所有权查询、分页与事务
  app/routers.py          HTTP 路由
  app/errors.py           统一错误处理
  conftest.py             隔离数据库与依赖覆盖
  test_main.py            行为、边界与安全回归测试
```

任务请求先由 Bearer 依赖提取 token，再校验签名与声明，通过当前数据库账号验证状态，最后由带 `owner_id` 条件的查询处理业务。Session 在同一个请求中通过 Depends 缓存复用，请求结束关闭，不在并发请求间共享。

Engine 在 lifespan 中创建和释放。导入模块不连接数据库，也不要求立即读取 JWT 密钥；服务启动时配置校验失败则不进入正常服务。数据库表由独立命令初始化，不在每个 worker 的启动逻辑里执行结构迁移。

### 用户、JWT 与数据隔离

用户名去除首尾空白并转小写，邮箱统一小写；数据库对两者设置唯一约束。注册只能创建普通用户，拒绝角色、账号状态、密码哈希等额外字段。密码使用 `pwdlib[argon2]` 哈希，公开用户模型不包含密码或哈希。[FastAPI 密码哈希与 JWT 教程](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/)

登录使用 OAuth2 password 表单教学流程，必须提供 `grant_type=password`，不是 JSON 登录。成功返回标准的 `access_token` 和 `token_type`，以便 Swagger UI 的 Authorize 使用。

JWT 固定使用 HS256，要求 sub、iat、exp、iss、aud、token_type，校验签名、有效期、签发方和受众。sub 是数据库用户 ID，角色不放在 token 内；账号停用和角色变化在下一次请求即时生效。不存在的账号或错误密码返回同样的 401 与 Bearer 挑战，已验证身份但账号停用/权限不足返回 403。

JWT 是签名凭证，不是加密数据，也不包含退出撤销机制。删除客户端 token 不会让已泄露的 token 自动失效；本例只能通过到期、停用账号或换密钥等方式限制使用。生产中的第三方/跨应用身份认证应另外评估成熟身份服务和授权流程，本阶段不是完整 OAuth2 授权服务器。

所有任务操作都限制为当前用户所有，访问他人任务统一返回 404，避免确认任务是否存在。管理员只能查看用户列表，不能因此读取他人的任务。用户 ID 使用 SQLite AUTOINCREMENT，避免删除用户后旧 token 被新用户复用。

### 更新、分页与事务

PATCH 使用 `exclude_unset=True`，只修改真正提交的字段；允许 `completed=false`、空 description，不允许空对象、显式 null 或修改 owner_id。创建任务返回 201 和 Location，删除返回真正无正文的 204。

查询使用 `page/page_size`，支持 completed、标题子串 q、sort=id/title/priority、order=asc/desc。总数包含当前用户与所有过滤条件；空页仍保留过滤后的总数。非唯一排序追加 ID 作为稳定次序。q 中的 `%`、`_` 作为普通字符匹配，不开放 SQL 通配符；SQLite 默认的 LIKE 对 ASCII 大小写行为仍由数据库决定。

用户名与邮箱冲突由数据库唯一约束兜底，失败后显式 rollback，保证 Session 可以继续使用。SQL 参数由 SQLAlchemy 绑定，排序字段来自枚举白名单，不把用户输入直接拼进 SQL。

### 响应契约与健康检查

普通成功响应为 `{"data": ...}`，列表 data 包含 items、total、page、page_size。令牌接口保留 OAuth2 标准返回，健康成功响应为简单 status，204 不包裹响应体。

所有处理过的错误统一为 `{"error":{"code":"...","message":"...","details":[]}}`，422 的 details 只保留位置、类型和说明，不回显 input/ctx。未知 500 不向客户端暴露异常消息。HTTP 异常保留 WWW-Authenticate、Allow 等响应头，OpenAPI 中也声明了错误模型。

`/health/live` 不检查数据库；`/health/ready` 检查数据库连接以及两个业务表是否可查询。它不是完整迁移版本审计或下游依赖检查。表不存在时返回 503，业务路由则可能返回通用 500，所以先执行初始化。

### 前 24 阶段回顾

| 阶段 | 本项目中的落点或延伸 |
| --- | --- |
| 01-02 路由与参数 | CRUD 路由、ID、分页参数约束 |
| 03 Pydantic | 输入/输出分离、PATCH、泛型响应 |
| 04 Depends | 配置、Session、当前用户、管理员依赖 |
| 05 数据库 | SQLite 持久化、SQLAlchemy 模型 |
| 06 项目结构 | config/database/models/schemas/services/routers |
| 07 配置 | LAB_ 环境变量、.env、必需密钥校验 |
| 08 迁移 | 显式初始化与每请求会话；正式结构演进应接入 Alembic |
| 09 注册 | Argon2、唯一约束、密码脱敏 |
| 10 JWT | 签名、声明、过期、401 |
| 11 权限 | 数据库角色、403、受控管理命令 |
| 12 异常 | 统一业务/框架/校验/服务器错误 |
| 13 查询 | 过滤后的总数、稳定排序、分页边界 |
| 14 文件 | 任务附件适合作为扩展，当前没有上传接口 |
| 15 表单与会话 | token 接口使用表单；当前不使用 Cookie Session |
| 16 中间件/CORS | 当前无跨域客户端，不默认开放 CORS |
| 17 后台任务 | 任务通知可以扩展，当前不发送邮件 |
| 18 异步 HTTP | 当前同步数据库路由在线程池运行；外部调用可另加 AsyncClient |
| 19 WebSocket | 任务实时提醒可以扩展，当前没有长连接 |
| 20 测试 | 临时库、分层 fixture、参数化、dependency_overrides |
| 21 OpenAPI | 标签、摘要、OAuth2 方案、成功与错误模型 |
| 22 可观测性 | 健康检查与固定事件错误日志；不宣称已有完整日志平台 |
| 23 生命周期 | 启动配置校验、Engine 获取与释放 |
| 24 部署 | 可使用 Uvicorn 入口；部署安全配置需按 Stage 24 另行接入 |

不把所有专题机械地塞进任务服务：附件、邮件、WebSocket 等仍由独立阶段展示。综合项目的重点是把核心业务闭环和可测试的边界串起来。

## 运行命令

在仓库根目录执行（Windows PowerShell，已有 `.venv`）：

```powershell
.\.venv\Scripts\Activate.ps1
cd stage25_mini_api
python -m pip install -r requirements.txt
$env:LAB_JWT_SECRET_KEY = python -c "import secrets; print(secrets.token_urlsafe(48))"
$env:LAB_ENVIRONMENT = 'development'
python init_db.py
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

访问 `http://127.0.0.1:8000/docs`，可先注册，再用 Authorize 登录。

默认数据库是本阶段目录下的 `mini_api.db`，不与旧阶段共享。`init_db.py` 可重复执行，不删除已有数据，但 create_all 不会升级已存在表的结构。正式演进应使用 Stage 08 的 Alembic 迁移流程；不要拿旧阶段数据库直接套用新模型。

配置默认读取本阶段 `.env`；系统环境变量优先，测试显式禁用配置文件。`.env.example` 不提供密钥，必须自行生成随机密钥并通过受控配置提供。上面的变量只在当前终端会话及其子进程中生效；换终端或重启进程时必须使用原来的密钥才能继续验证已有 token，不要每次请求重新生成。

配置项为 LAB_ENVIRONMENT、LAB_DATABASE_URL、LAB_JWT_SECRET_KEY、LAB_ACCESS_TOKEN_EXPIRE_MINUTES。后者默认 30，允许 1-1440。当前只支持同步 SQLite；自定义相对数据库路径按进程工作目录解析。

注册 alice 后，停止 Uvicorn，在仍保留密钥环境变量的同一个终端提升角色，再启动服务：

```powershell
python manage_user.py alice --role admin
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

降回普通用户使用 `--role user`。命令需要受控的主机与数据库访问权限，公网不提供提权接口。已有 token 会在下一次请求读取新角色。

## 测试命令

在阶段目录执行：

```powershell
python -m pytest -q -p no:cacheprovider
```

受限 Windows 环境若无法写系统临时目录，可使用仓库虚拟环境下的临时目录：

```powershell
New-Item -ItemType Directory -Force ..\.venv\pytest-tmp | Out-Null
$env:TEMP = (Resolve-Path ..\.venv\pytest-tmp).Path
$env:TMP = $env:TEMP
python -m pytest -q -p no:cacheprovider
```

验证结果（2026-10-12）：`86 passed`；真实 Uvicorn HTTP 与 CLI 流程也通过，包含重复初始化、管理员角色升降级以及重启后的任务和 token 保留。

集成测试通过 dependency_overrides 替换 get_db 和 get_settings。应用自身指向一个禁止访问的路径，夹具结束时断言它从未被创建，避免测试误用真实库；专门的数据库未初始化测试则直接使用自己的临时路径。不要在仓库根目录同时收集所有阶段的同名模块。

覆盖完整业务流、哈希验证、输入脱敏、令牌声明、账号停用/删除、角色变更、任务隔离、PATCH、分页过滤排序、事务回滚、外键约束、错误契约、启动校验与关闭释放。当前环境有一条 Starlette TestClient 使用 httpx 的依赖弃用提示，不影响测试通过。

## 示例请求

在另一个 PowerShell 窗口执行（首次注册）：

```powershell
$base = 'http://127.0.0.1:8000'
$registration = @{ username = 'alice'; email = 'alice@example.com'; password = 'learning-password-123' } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "$base/auth/register" -ContentType 'application/json' -Body $registration

$token = Invoke-RestMethod -Method Post -Uri "$base/auth/token" -ContentType 'application/x-www-form-urlencoded' -Body @{ grant_type = 'password'; username = 'alice'; password = 'learning-password-123' }
$headers = @{ Authorization = "Bearer $($token.access_token)" }
Invoke-RestMethod "$base/users/me" -Headers $headers

$body = @{ title = 'Learn FastAPI'; priority = 2 } | ConvertTo-Json
$created = Invoke-RestMethod -Method Post -Uri "$base/tasks" -Headers $headers -ContentType 'application/json' -Body $body
$id = $created.data.id
Invoke-RestMethod "$base/tasks?page=1&page_size=10&sort=priority&order=asc" -Headers $headers
Invoke-RestMethod -Method Patch -Uri "$base/tasks/$id" -Headers $headers -ContentType 'application/json' -Body '{"completed":true}'
Invoke-RestMethod -Method Delete -Uri "$base/tasks/$id" -Headers $headers
```

示例密码仅用于本地学习，不要用于真实账号。重复注册 alice 返回 409，不会覆盖原用户；直接登录即可继续。

## 预期返回

注册返回 201：

```json
{"data":{"id":1,"username":"alice","email":"alice@example.com","role":"user","is_active":true}}
```

登录返回 200，token 内容每次可能不同，不要写入日志或提交到 Git：

```json
{"access_token":"签名的JWT","token_type":"bearer"}
```

创建任务返回 201，并带 Location 响应头：

```json
{"data":{"title":"Learn FastAPI","description":"","completed":false,"priority":2,"id":1,"owner_id":1}}
```

分页列表的 data 为 `{"items":[...],"total":1,"page":1,"page_size":10}`。删除返回 204，无响应正文。

跨用户访问与不存在的任务都返回 404：

```json
{"error":{"code":"TASK_NOT_FOUND","message":"Task not found","details":[]}}
```

缺少或无效 token 返回 401，并带 `WWW-Authenticate: Bearer`；普通用户访问 `/admin/users` 返回 403；字段不合法返回 422；重复用户名/邮箱返回 409；未知服务器错误返回脱敏的 500。

## 常见错误

- 启动报缺少 JWT 密钥：.env.example 的空值不是可用密钥，需要先配置至少 32 字符的随机密钥。
- readiness 返回 503：确认配置指向正确数据库并已执行 init_db.py，不要通过自动建表掩盖部署问题。
- 登录返回 422：使用表单编码，并提供 grant_type=password，不要发送 JSON。
- PATCH 返回 422：至少提供一个支持的非 null 字段，不能修改 owner_id。
- 另一个用户读取任务返回 404：这是刻意的数据隔离，不是管理员可任意绕过的规则。
- 重启后 token 全失效：检查是否重新生成了签名密钥，或系统环境变量覆盖了 .env。
- 数据库锁定或写入吞吐不足：SQLite 适合轻量学习，busy_timeout 不是无限并发写入方案，生产数据库与事务策略应另行设计。
- 直接公网部署：本例未实现限流、密码重置、邮箱验证、refresh token、token 撤销、Host 白名单或生产文档开关；LAB_ENVIRONMENT=production 不会自动补齐这些能力。
- 以为 500 脱敏就不会泄密：应用不返回异常细节，但 Uvicorn/代理日志仍要独立审查。HTTPS、备份、迁移、依赖锁定与安全更新同样需要单独落实。

## 小练习

1. 用 Alembic 增加任务截止日期，编写迁移及升级/回滚测试，不修改已有迁移历史。
2. 为注册与登录接入限流，加入密码重置和密钥轮换方案，不自行发明身份协议。
3. 将 Stage 14 的上传安全规则整合为任务附件，并检查附件所有权与删除清理。
4. 为任务状态变化增加通知，比较 BackgroundTasks 与可靠队列的适用边界。
5. 使用 Stage 22 的请求关联日志和 Stage 24 的容器配置，为本项目加入 CI、镜像构建及可观测性。
