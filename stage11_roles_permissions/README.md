# 阶段 11：权限与角色控制

## 本阶段学习目标

- 理解认证（是谁）与授权（能做什么）的区别。
- 用普通用户、管理员及权限映射实现最小 RBAC。
- 通过依赖组合复用账号状态与权限校验。
- 验证权限失败、注册提权防护和角色变更生效行为。

## 核心概念

本阶段在 Stage 10 的注册、JWT 登录和账号状态检查基础上增加 `role` 字段，仍然使用独立 SQLite 数据库。

`app/permissions.py` 定义两个角色及其权限：

| 角色 | `items:read` | `users:read` |
| --- | --- | --- |
| `user` | 允许 | 不允许 |
| `admin` | 允许 | 允许 |

`require_permission(permission)` 是一个返回依赖函数的工厂。每个受保护请求依次执行：提取 Bearer Token、验证 JWT、从数据库加载用户、检查 `is_active`、根据当前角色查询权限映射。路由只声明所需权限，不重复写角色判断。

JWT 只携带用户标识、签发和过期时间、token 类型，不携带角色。管理员降级后，同一个未过期 token 会立即失去管理权限；客户端添加 `role` 或请求 `scope` 也不能改变数据库中的授权结果。数据库约束仅允许 `user`、`admin` 两种角色。

| 接口 | 要求 | 响应 |
| --- | --- | --- |
| `POST /users` | 公开注册 | 新用户固定为普通用户 |
| `POST /token` | 表单用户名、密码 | JWT access token |
| `GET /users/me` | 已认证且未停用 | 自己的公开资料及角色 |
| `GET /items` | `items:read` | 示例商品列表 |
| `GET /admin/users` | `users:read` | 用户列表，含角色和账号状态 |
| `GET /admin/stats` | `users:read` | 用户总数与有效账号数 |

两个管理接口复用同一个权限依赖。所有用户响应均排除密码与密码哈希。注册请求禁止额外字段，提交 `role` 或 `is_active` 返回 422，不创建用户；角色由服务端管理，不提供公开提权接口。

未登录、token 无效或过期返回 401，并带 `WWW-Authenticate: Bearer`；账号停用或当前角色没有所需权限返回 403。管理员也必须通过账号状态检查，不享有停用例外。

本例使用数据库角色授权，没有将权限作为 OAuth2 scopes 放入 token；更细粒度的标准 scopes 可作为扩展，参见 [FastAPI OAuth2 scopes 官方文档](https://fastapi.tiangolo.com/advanced/security/oauth2-scopes/)。本阶段不实现多角色、多租户或权限管理后台。

## 运行命令

在仓库根目录激活虚拟环境，进入本阶段，设置随机密钥并初始化独立数据库：

```powershell
.\.venv\Scripts\Activate.ps1
cd stage11_roles_permissions
python -m pip install -r requirements.txt
$env:LAB_JWT_SECRET_KEY = python -c "import secrets; print(secrets.token_urlsafe(32))"
python init_db.py
python -m uvicorn main:app --reload
```

访问 http://127.0.0.1:8000/docs 。`LAB_JWT_SECRET_KEY` 至少 32 个字符，无默认密钥；token 默认 30 分钟有效，可用 `LAB_ACCESS_TOKEN_EXPIRE_MINUTES` 配置。`.env.example` 中的密钥故意留空，配置详情沿用 Stage 10。改变密钥会使旧 token 失效，改变角色则不需要重新签发 token。

默认库是本阶段目录中的 `users.db`，可用 `LAB_DATABASE_URL` 覆盖。请使用本阶段自己的新数据库；新增角色字段后，旧阶段数据库不能直接复用。`init_db.py` 不会迁移已有表，表结构变更参考 Stage 08 的 Alembic 流程。

### 设置管理员

先注册 `alice`。在另一个已激活虚拟环境、已进入本阶段目录的终端执行：

```powershell
python promote_user.py alice
```

本地命令与服务需指向相同数据库；用户名会去除首尾空白并转为小写。用户不存在时退出码为 1，不会自动创建账号；重复执行是幂等的。执行此命令需要数据库所在机器的访问权限，它用于学习环境的管理员引导，不暴露为 HTTP 接口，也不修改密码或账号启用状态。

## 测试命令

```powershell
python -m pytest -q
```

测试继承本阶段的 JWT 边界覆盖，并增加角色/接口权限矩阵、未登录访问管理接口、拒绝注册提权、当前 token 下的角色升降级、停用管理员、管理响应脱敏、数据库角色约束和管理员命令测试。

所有测试使用临时 SQLite、独立测试密钥、数据库依赖覆盖，并清理缓存与覆盖。若受限沙箱无法创建系统临时目录，将当前终端 `TEMP`、`TMP` 指向项目内可写临时目录后重试。

验证记录（2026-10-12）：Python 3.12，`54 passed`；`init_db.py` 和 `promote_user.py --help` 验证通过。有一条 Starlette TestClient 使用 httpx 的依赖弃用提示，不影响测试。

## 示例请求

服务启动后，在另一个 PowerShell 中注册并登录：

```powershell
$body = @{ username = "alice"; email = "alice@example.com"; password = "Learning-pass-123" } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/users -ContentType 'application/json' -Body $body
$login = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/token -ContentType 'application/x-www-form-urlencoded' -Body @{ username = "alice"; password = "Learning-pass-123" }
$headers = @{ Authorization = "Bearer $($login.access_token)" }
Invoke-RestMethod -Uri http://127.0.0.1:8000/users/me -Headers $headers
Invoke-RestMethod -Uri http://127.0.0.1:8000/admin/users -Headers $headers
```

普通用户访问管理接口时，PowerShell 会显示 403。按前述命令设置管理员后，继续用同一份 `$headers` 请求：

```powershell
Invoke-RestMethod -Uri http://127.0.0.1:8000/admin/users -Headers $headers
Invoke-RestMethod -Uri http://127.0.0.1:8000/admin/stats -Headers $headers
```

## 预期返回

空库首次注册返回 201：

```json
{"id":1,"username":"alice","email":"alice@example.com","role":"user"}
```

普通用户访问管理接口返回 403：

```json
{"detail":"Not enough permissions"}
```

设置管理员后，`GET /admin/users` 返回 200：

```json
[{"id":1,"username":"alice","email":"alice@example.com","role":"admin","is_active":true}]
```

只有一个有效用户时，`GET /admin/stats` 返回：

```json
{"total_users":1,"active_users":1}
```

## 常见错误

1. **登录成功仍返回 403**：认证成功不代表拥有管理权限，检查数据库角色；停用账号也会返回 403。
2. **注册时传入 role 导致 422**：注册不接受角色或账号状态字段，使用本地引导命令设置管理员。
3. **管理员命令提示用户不存在**：先注册用户，确认命令与服务共用本阶段数据库。
4. **数据库缺少 role 列**：不要直接使用旧阶段数据库；初始化新库或用迁移修改已有结构。
5. **在 token 中加入 admin 仍然无权限**：本例依据数据库角色授权，不信任 token 的额外角色声明或请求头中的角色。
6. **管理员无法绕过停用状态**：账号状态检查在权限检查之前执行，重新启用属于服务端管理操作。
7. **把角色权限等同于数据所有权**：本例只演示路由级 RBAC。后续涉及用户私有资源时，还需要独立的资源归属校验。

## 小练习

1. 增加 `editor` 角色和商品写权限，扩展权限矩阵测试。
2. 用 Alembic 为已有 Stage 10 用户库添加默认 `user` 角色。
3. 在受保护资源中加入所有者检查，区分路由权限与资源访问权限。
