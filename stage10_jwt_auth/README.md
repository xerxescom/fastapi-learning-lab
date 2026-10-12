# 阶段 10：JWT 登录与鉴权进阶

## 本阶段学习目标

- 使用 OAuth2 表单提交用户名和密码，验证后签发 JWT access token。
- 用 `OAuth2PasswordBearer` 提取 Bearer Token，通过依赖获得当前用户。
- 校验签名、过期时间、必要声明和用户状态。
- 理解认证失败 401 与账号不可访问 403 的区别。

## 核心概念

本阶段沿用 Stage 09 的注册、密码哈希、数据库依赖和响应脱敏方式，提供独立的 SQLite 数据库，无需启动其他阶段。

| 接口 | 请求 | 返回 |
| --- | --- | --- |
| `POST /users` | 注册 JSON | 201，公开用户字段 |
| `POST /token` | username/password 表单 | 200，access_token/token_type |
| `GET /users/me` | Bearer Token | 当前有效用户 |
| `GET /items` | Bearer Token | 当前用户的示例商品列表 |

`app/security.py` 负责 Argon2 密码验证和 PyJWT 签发、解码。JWT 使用固定 `HS256` 算法，解码时不接受 token 自行指定其他算法。内容包含 `sub`（字符串用户 ID）、`iat`（签发时间）、`exp`（过期时间）和 `token_type=access`。验证要求这些声明存在，检查过期时间，并拒绝无效用户 ID、非 access token 和已删除用户。

JWT 内容可被读取，签名不等于加密，因此本例不将密码、密码哈希、邮箱等数据放进 token。签发与验证的基本流程参考 [FastAPI 官方 JWT 教程](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/)。

`app/dependencies.py` 将两层依赖串起来：`get_current_user` 验证 token 并查数据库，`get_active_user` 检查账号状态。受保护接口依赖后者。每次访问都会读取当前数据库状态，因此停用账号后，已有 token 也无法继续访问。SQLite 用户表启用不复用 ID 的自增规则，避免删除用户后的旧 token 指向新用户。

| 情况 | 状态码 |
| --- | --- |
| 用户名或密码错误、缺少 token、签名不符、过期、用户已删除 | 401，带 `WWW-Authenticate: Bearer` |
| 凭据有效，但数据库中的 `is_active` 为 false | 403 |
| 登录表单字段缺失或注册数据不合法 | 422，不回显原始输入 |
| 注册用户名或邮箱重复 | 409 |

不存在的用户名也执行一次虚拟密码校验，减少明显的认证耗时差异；失败响应不区分用户不存在还是密码错误。`is_active` 不能由注册请求设置，本阶段没有公开停用接口，测试通过修改测试数据库演示 403，角色权限留到 Stage 11。

`app/config.py` 读取 `LAB_JWT_SECRET_KEY`（至少 32 个字符，无默认值）和 `LAB_ACCESS_TOKEN_EXPIRE_MINUTES`（默认 30，范围 1 到 1440）。字符长度校验不能保证密钥随机性，应通过 `secrets` 生成随机密钥。配置缓存于进程，启动 lifespan 时检查密钥，配置缺失或过短会阻止启动。实际密钥不提交 Git、不写入响应。

## 运行命令

在仓库根目录激活虚拟环境，进入本阶段，安装依赖并生成当前终端使用的随机密钥：

```powershell
.\.venv\Scripts\Activate.ps1
cd stage10_jwt_auth
python -m pip install -r requirements.txt
$env:LAB_JWT_SECRET_KEY = python -c "import secrets; print(secrets.token_urlsafe(32))"
python init_db.py
python -m uvicorn main:app --reload
```

访问 http://127.0.0.1:8000/docs 。先调用注册接口，再在 Swagger 的 Authorize 中填写 username 和 password，之后可直接调用受保护接口。

环境变量保存在当前终端及其子进程中；同一终端重启服务保留密钥，重新生成密钥后旧 token 失效。可选使用本阶段 `.env` 持久配置，参考 `.env.example`，其中密钥故意留空，需要填写随机值；环境变量优先于文件配置。修改配置后重启服务。

默认数据库为本阶段的 `users.db`，可通过 `LAB_DATABASE_URL` 覆盖。`init_db.py` 只初始化不存在的表，不迁移已有表；不要直接复用 Stage 09 数据库，因为本阶段增加账号状态和自增约束。已有库的结构调整参考 Stage 08 的 Alembic 流程。

## 测试命令

```powershell
python -m pytest -q
```

测试使用独立 SQLite 临时库、独立测试密钥，并隔离 `.env`、配置缓存与依赖覆盖。覆盖注册登录流程、错误密码、不存在的用户、缺失及无效 token、签名和算法限制、过期及缺失声明、停用账号、删除用户后 ID 不复用，以及 OpenAPI 的 OAuth2 声明。过期测试直接签发过去时间的 token，无需等待。

验证记录（2026-10-12）：Python 3.12，`35 passed`；`init_db.py` 初始化成功。有一条 Starlette TestClient 使用 httpx 的依赖弃用提示，不影响测试。

若受限沙箱不能创建系统临时目录，将当前终端的 `TEMP`、`TMP` 指向项目内可写临时目录后重试。

## 示例请求

启动服务后，在另一个 PowerShell 中执行：

```powershell
$body = @{ username = "alice"; email = "alice@example.com"; password = "Learning-pass-123" } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/users -ContentType 'application/json' -Body $body
$login = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/token -ContentType 'application/x-www-form-urlencoded' -Body @{ username = "alice"; password = "Learning-pass-123" }
$headers = @{ Authorization = "Bearer $($login.access_token)" }
Invoke-RestMethod -Uri http://127.0.0.1:8000/users/me -Headers $headers
Invoke-RestMethod -Uri http://127.0.0.1:8000/items -Headers $headers
```

重复注册返回 409；已经注册时可直接执行登录步骤。`/token` 接收表单而非 JSON，这是 Swagger OAuth2 密码流程所需的请求格式。密码保持原样，用户名与注册时相同，去除首尾空白并转为小写。

## 预期返回

登录成功返回 200，token 每次签发的值与时间有关：

```json
{"access_token":"<signed JWT>","token_type":"bearer"}
```

空数据库首次注册后访问当前用户：

```json
{"id":1,"username":"alice","email":"alice@example.com"}
```

认证失败返回 401：

```json
{"detail":"Could not validate credentials"}
```

凭据有效但账号停用返回 403：

```json
{"detail":"Inactive user"}
```

## 常见错误

1. **启动时报缺少密钥或密钥过短**：设置 `LAB_JWT_SECRET_KEY`，不能使用空 `.env.example` 中的值直接启动。
2. **登录返回 422**：检查是否按表单提交 `username`、`password`，不要使用注册接口的 JSON 格式。
3. **找不到 multipart 解析器**：安装本阶段 `requirements.txt` 中的 `python-multipart`。
4. **携带 token 仍然 401**：请求头需要 `Authorization: Bearer <token>`；检查是否过期、签名密钥是否变化、用户是否被删除。
5. **403 误以为 token 无效**：凭据已验证，数据库中的账号状态不允许访问。
6. **缺少 users 表或 is_active 字段**：使用本阶段自己的新数据库初始化；已有表结构变更需要迁移，`create_all()` 不会修改旧表。
7. **认为删除浏览器里的 token 就能服务端注销**：本例没有撤销列表或 refresh token。客户端删除 token 不能撤销已被复制的有效 token；生产环境还需 HTTPS、限流和按业务设计的撤销、轮换策略。

## 小练习

1. 修改 token 有效期，验证到期后接口返回 401。
2. 在测试数据库停用用户，验证已签发 token 返回 403。
3. 在 Stage 11 中加入角色权限依赖，不把权限检查写进每个路由。
