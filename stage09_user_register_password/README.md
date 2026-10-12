# 阶段 09：用户注册与密码安全

## 本阶段学习目标

- 定义用户表、注册请求模型和公开响应模型。
- 使用 `pwdlib[argon2]` 保存密码哈希并验证密码。
- 处理用户名、邮箱校验及重复注册。
- 验证数据库、响应与校验错误不会泄露明文密码。

## 核心概念

本阶段提供 `POST /users`，请求包含 `username`、`email`、`password`。注册成功返回 201，响应只有 `id`、`username`、`email`。

| 模块 | 职责 |
| --- | --- |
| `app/database.py` | 数据库配置、引擎、请求级会话依赖 |
| `app/models.py` | 用户表与唯一约束 |
| `app/schemas.py` | 输入校验和公开响应字段 |
| `app/security.py` | 密码哈希与验证 |
| `app/services.py` | 注册业务、提交与冲突回滚 |
| `app/routers.py` | 注册接口和 HTTP 状态码 |
| `main.py` | 应用组装及校验错误脱敏 |

用户名去除首尾空白并转为小写，长度 3 到 30，只允许字母开头、后接小写字母、数字或下划线。邮箱使用 `EmailStr` 校验并统一转为小写，最长 254 个字符。本例明确将完整邮箱按不区分大小写处理，这是一项教学业务规则。

密码长度为 8 到 128 个字符，不裁剪空白、不改变大小写。长度约束只用于演示，不代表完整的生产密码策略。输入模型使用 `SecretStr` 避免普通模型打印直接显示密码，哈希前才通过 `get_secret_value()` 取出原始值。

密码使用 `PasswordHash.recommended()` 的 Argon2 实现，库自动生成随机盐；相同密码产生不同的哈希。验证时使用库的 `verify()`，不直接比较重新计算的哈希，也不使用明文、可逆加密或普通 SHA-256 替代密码哈希。[FastAPI 官方密码哈希教程](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/#password-hashing)

数据库只有 `password_hash` 字段，响应模型不包含密码或哈希。默认校验错误可能携带原始输入，本阶段错误处理器只返回 `loc`、`msg`、`type`，避免把请求密码回显给客户端。`SecretStr` 不会自动保护网络请求或原始请求日志，后续接入日志时仍应避免记录密码字段。

注册先查重，再提交；数据库为用户名、邮箱分别设置唯一约束，防止并发请求绕过预检查。提交遇到唯一冲突后先回滚，再返回 409，且会话仍可继续使用。错误信息统一为 `Username or email already registered`。

本阶段目录可独立运行，使用自己的新数据库。为集中学习注册，`init_db.py` 仅显式初始化不存在的表，不在应用启动时建表，也不复制 Stage 08 商品库。它不能更新已存在的表结构；需要修改用户表时，按 Stage 08 的 Alembic 流程管理迁移。

## 运行命令

在仓库根目录激活虚拟环境，然后进入本阶段：

```powershell
.\.venv\Scripts\Activate.ps1
cd stage09_user_register_password
python -m pip install -r requirements.txt
python init_db.py
python -m uvicorn main:app --reload
```

访问 http://127.0.0.1:8000/docs 。默认数据库是本阶段目录中的 `users.db`，重启服务后保留用户。

可选：复制 `.env.example` 为 `.env`，用 `LAB_DATABASE_URL` 覆盖连接地址。示例相对路径基于工作目录，请在本阶段内执行命令。初始化与服务启动使用同一环境配置，修改配置后需重启。数据库文件与 `.env` 被忽略，不提交 Git。

## 测试命令

```powershell
python -m pytest -q
```

测试用独立临时 SQLite 数据库并覆盖 `get_db`，不读取或修改实际用户记录。验证成功注册、真实哈希与密码验证、随机盐、重复用户名/邮箱、规范化、非法输入、校验错误脱敏，以及预检查过期后的唯一约束与事务回滚。

验证记录（2026-10-12）：Python 3.12，`22 passed`；`init_db.py` 执行成功。有一条 Starlette TestClient 使用 httpx 的依赖弃用提示，不影响本阶段测试。

受限沙箱若无法创建系统临时目录，可将当前终端 `TEMP`、`TMP` 指向项目内可写临时目录后重试。

## 示例请求

```powershell
$body = @{ username = "alice"; email = "alice@example.com"; password = "Learning-pass-123" } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/users -ContentType 'application/json' -Body $body
```

在 `/docs` 中重复提交同一请求可观察 409；把密码改为 `short` 或邮箱改为无效格式可观察 422。本例没有公开用户列表或密码验证接口，登录与 token 签发放在 Stage 10。

## 预期返回

空数据库首次注册，返回 201：

```json
{"id":1,"username":"alice","email":"alice@example.com"}
```

重复注册返回 409：

```json
{"detail":"Username or email already registered"}
```

非法请求返回 422，`detail` 为错误数组，包含字段位置、错误类型与说明，不包含原始 `input` 或密码。`password_hash` 仅保存在数据库中，不出现在 API 响应里。

## 常见错误

1. **`no such table: users`**：先执行 `python init_db.py`，确认与应用使用同一数据库配置。
2. **缺少 `email_validator` 或 Argon2 后端**：在当前虚拟环境安装整个 `requirements.txt`，其中包含 `email-validator` 和 `pwdlib[argon2]`。
3. **修改大小写后依然冲突**：用户名、邮箱按本例规则统一为小写，唯一约束针对规范化后的值。
4. **直接返回 ORM 用户对象中的所有属性**：使用公开响应模型，禁止返回密码哈希。
5. **用新哈希字符串与旧哈希比较**：随机盐会令结果不同，应调用 `verify_password()`。
6. **生产环境直接照搬示例**：上线时还需 HTTPS、注册限流、邮箱验证、密码策略与泄露密码检查等；相关配置和安全机制应随业务补齐。

## 小练习

1. 为用户增加创建时间，配合 Stage 08 为用户表建立 Alembic 迁移。
2. 增加拒绝常见弱密码的校验，同时保证错误响应不泄露密码。
3. 在 Stage 10 中复用 `verify_password()` 实现登录，并为错误密码编写测试。
