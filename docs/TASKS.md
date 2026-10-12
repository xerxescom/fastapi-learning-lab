# fastapi-learning-lab 任务清单（基于当前最新代码）

> 当前已完成：`stage01_hello_fastapi`、`stage02_params`、`stage03_pydantic_body`、`stage04_depends`、`stage05_sqlite`、`stage06_project_layout`、`stage07_settings_env`、`stage08_alembic_migrations`、`stage09_user_register_password`、`stage10_jwt_auth`、`stage11_roles_permissions`、`stage12_response_errors`、`stage13_pagination_filtering`、`stage14_upload_static_files`、`stage15_form_cookie_session`、`stage16_middleware_cors`、`stage17_background_tasks`、`stage18_async_http`、`stage19_websocket`、`stage20_testing_advanced`、`stage21_openapi_docs`、`stage22_logging_observability`、`stage23_lifespan`、`stage24_deployment`、`stage25_mini_api`（均含应用、测试、中文文档）。

## 当前阶段（已完成）

- [x] Stage 01：FastAPI 入门与基础路由
  - [x] `main.py`：`GET /` 与 `GET /health`
  - [x] `test_main.py`：基础接口测试
  - [x] `README.md`：学习目标、运行测试说明、示例请求

---

## 下一阶段任务（建议按顺序推进）

### Stage 02：路径参数与查询参数

- [x] 新建目录：`stage02_params`
- [x] 编写 `main.py`
  - [x] 路径参数：`/users/{user_id}`
  - [x] 查询参数：`/items?limit=...&offset=...`
  - [x] 参数类型校验（`int`、`str`、`bool`）
- [x] 编写 `test_main.py`
  - [x] 正常参数测试
  - [x] 非法参数 422 测试
- [x] 编写 `README.md`
  - [x] 解释路径参数与查询参数差异
  - [x] 增加常见错误（422、参数类型错误）

### Stage 03：请求体与 Pydantic 模型

- [x] 新建目录：`stage03_pydantic_body`
- [x] 编写 `main.py`
  - [x] `POST /items`，使用 BaseModel
  - [x] 字段默认值与可选字段
  - [x] 响应模型 `response_model`
- [x] 编写 `test_main.py`
  - [x] 请求体合法/非法测试
  - [x] 响应字段断言
- [x] 编写 `README.md`
  - [x] 解释数据校验与错误返回

### Stage 04：依赖注入（Depends）

- [x] 新建目录：`stage04_depends`
- [x] 编写 `main.py`
  - [x] 公共查询参数依赖
  - [x] 简单鉴权依赖（Header Token）
- [x] 编写 `test_main.py`
  - [x] 正常请求与鉴权失败请求
- [x] 编写 `README.md`
  - [x] 解释依赖复用场景

### Stage 05：数据库入门（SQLite + SQLModel/SQLAlchemy）

- [x] 新建目录：`stage05_sqlite`
- [x] 编写 `main.py`
  - [x] SQLite 本地库
  - [x] 基础 CRUD（增删改查）
- [x] 编写 `test_main.py`
  - [x] 测试隔离（临时数据库）
- [x] 编写 `README.md`
  - [x] 数据库初始化与迁移说明（入门级）

### Stage 06：项目结构化与路由拆分

- [x] 新建目录：`stage06_project_layout`
- [x] 拆分 `routers/`、`schemas/`、`services/`
- [x] 统一异常处理与响应格式（轻量版）
- [x] 完善对应测试与文档

---

## 后续开发计划（核心能力 + 生产常用）

> 目标：继续保持“每个阶段只聚焦一个主题”的节奏，让学习者通过一个仓库逐步掌握 FastAPI 核心用法与常见生产项目能力。

### Stage 07：配置管理与环境变量

- [x] 新建目录：`stage07_settings_env`
- [x] 编写 `main.py`
  - [x] 使用 `pydantic-settings` 管理配置
  - [x] 支持 `.env` 示例
  - [x] 区分开发配置与测试配置
  - [x] 演示配置项默认值与类型校验
- [x] 编写 `test_main.py`
  - [x] 测试默认配置读取
  - [x] 测试配置覆盖与校验
- [x] 编写 `README.md`
  - [x] 解释为什么不要把配置硬编码在业务代码中
  - [x] 说明环境变量、`.env` 与测试配置的关系

验证结果（2026-10-12）：`11 passed`；有一条 Starlette TestClient 使用 httpx 的依赖弃用提示，不影响测试通过。

### Stage 08：数据库进阶与 Alembic 迁移

- [x] 新建目录：`stage08_alembic_migrations`
- [x] 编写 `main.py`
  - [x] 拆分 SQLAlchemy 模型、数据库会话与路由
  - [x] 初始化 Alembic 迁移目录
  - [x] 演示生成迁移与执行迁移
  - [x] 使用依赖注入提供数据库会话
- [x] 编写 `test_main.py`
  - [x] 使用测试数据库隔离 CRUD 测试
  - [x] 验证数据库会话依赖可覆盖
- [x] 编写 `README.md`
  - [x] 解释 `create_all` 与 Alembic 迁移的区别
  - [x] 给出常用迁移命令

验证结果（2026-10-12）：`12 passed`；迁移 CLI 确认 `0002 (head)`，`alembic check` 无结构差异。有一条 Starlette TestClient 使用 httpx 的依赖弃用提示。

### Stage 09：用户注册与密码安全

- [x] 新建目录：`stage09_user_register_password`
- [x] 编写 `main.py`
  - [x] 定义用户模型与用户响应模型
  - [x] 使用密码哈希保存密码
  - [x] 实现用户注册接口
  - [x] 处理重复用户名或邮箱
- [x] 编写 `test_main.py`
  - [x] 测试注册成功
  - [x] 测试密码不会明文返回
  - [x] 测试重复用户与非法输入
- [x] 编写 `README.md`
  - [x] 解释密码哈希与明文密码的风险
  - [x] 说明注册接口的常见校验点

验证结果（2026-10-12）：`22 passed`；`init_db.py` 初始化成功，覆盖 Argon2 密码验证、响应与错误脱敏、唯一冲突及回滚。有一条 Starlette TestClient 使用 httpx 的依赖弃用提示。

### Stage 10：JWT 登录与鉴权进阶

- [x] 新建目录：`stage10_jwt_auth`
- [x] 编写 `main.py`
  - [x] 实现登录接口
  - [x] 签发 JWT access token
  - [x] 编写获取当前用户的依赖
  - [x] 创建受保护路由
  - [x] 区分 401 与 403 的使用场景
- [x] 编写 `test_main.py`
  - [x] 测试登录成功与失败
  - [x] 测试携带 token 访问受保护路由
  - [x] 测试缺失、错误、过期 token
- [x] 编写 `README.md`
  - [x] 解释 JWT 的基本结构与适用边界
  - [x] 说明 Bearer Token 的请求方式

验证结果（2026-10-12）：`35 passed`；数据库初始化成功，覆盖签名与声明校验、401/403、账号停用和删除后 ID 不复用。有一条 Starlette TestClient 使用 httpx 的依赖弃用提示。

### Stage 11：权限与角色控制

- [x] 新建目录：`stage11_roles_permissions`
- [x] 编写 `main.py`
  - [x] 增加普通用户与管理员角色
  - [x] 编写路由级权限依赖
  - [x] 创建仅管理员可访问的接口
  - [x] 演示最小 RBAC 设计
- [x] 编写 `test_main.py`
  - [x] 测试普通用户权限不足
  - [x] 测试管理员访问成功
  - [x] 测试未登录访问失败
- [x] 编写 `README.md`
  - [x] 解释认证与授权的区别
  - [x] 说明角色权限依赖的复用方式

验证结果（2026-10-12）：`54 passed`；数据库初始化及管理员命令入口验证通过，覆盖权限矩阵、角色升降级即时生效和注册提权防护。有一条 Starlette TestClient 使用 httpx 的依赖弃用提示。

### Stage 12：请求响应规范与全局异常处理

- [x] 新建目录：`stage12_response_errors`
- [x] 编写 `main.py`
  - [x] 定义统一成功响应格式
  - [x] 定义统一错误响应格式
  - [x] 创建自定义业务异常
  - [x] 覆盖 404、422、500 的轻量示例
- [x] 编写 `test_main.py`
  - [x] 测试成功响应结构
  - [x] 测试业务异常响应结构
  - [x] 测试请求校验错误响应结构
- [x] 编写 `README.md`
  - [x] 解释统一响应格式的收益与取舍
  - [x] 说明 FastAPI 默认异常与自定义异常的关系

验证结果（2026-10-12）：`25 passed`；覆盖业务与框架异常、422 输入脱敏、500 内部错误保护、HTTP 响应头和 OpenAPI 响应模型。有一条 Starlette TestClient 使用 httpx 的依赖弃用提示。

### Stage 13：分页、排序与过滤

- [x] 新建目录：`stage13_pagination_filtering`
- [x] 编写 `main.py`
  - [x] 实现 `limit/offset` 分页
  - [x] 实现 `page/page_size` 分页
  - [x] 支持排序参数
  - [x] 支持基础条件过滤
- [x] 编写 `test_main.py`
  - [x] 测试分页结果与总数
  - [x] 测试排序结果
  - [x] 测试过滤条件
  - [x] 测试参数边界
- [x] 编写 `README.md`
  - [x] 对比两种常见分页方式
  - [x] 说明分页参数的边界限制

验证结果（2026-10-12）：`57 passed`；连续两次数据库初始化确认样例插入与已有数据保留，覆盖稳定排序、过滤后总数、空结果与分页边界。有一条 Starlette TestClient 使用 httpx 的依赖弃用提示。

### Stage 14：文件上传与静态文件

- [x] 新建目录：`stage14_upload_static_files`
- [x] 编写 `main.py`
  - [x] 使用 `UploadFile` 接收文件
  - [x] 校验文件类型与大小
  - [x] 挂载静态文件目录
  - [x] 返回可访问的文件 URL
- [x] 编写 `test_main.py`
  - [x] 测试文件上传成功
  - [x] 测试非法文件类型
  - [x] 测试静态文件访问
- [x] 编写 `README.md`
  - [x] 解释 `UploadFile` 与普通表单字段的区别
  - [x] 说明生产环境文件存储的扩展方向

验证结果（2026-10-12）：`43 passed`；覆盖类型与内容校验、大小边界、随机文件名、路径安全、静态下载和写盘失败清理。有一条 Starlette TestClient 使用 httpx 的依赖弃用提示。

### Stage 15：表单、Cookie 与 Session 基础

- [x] 新建目录：`stage15_form_cookie_session`
- [x] 编写 `main.py`
  - [x] 实现表单登录示例
  - [x] 演示 Cookie 读写
  - [x] 演示简单 Session 思路
  - [x] 对比 Cookie Session 与 JWT
- [x] 编写 `test_main.py`
  - [x] 测试表单提交
  - [x] 测试 Cookie 设置与读取
  - [x] 测试 Session 状态
- [x] 编写 `README.md`
  - [x] 解释表单请求与 JSON 请求的区别
  - [x] 说明 Cookie、Session、JWT 的适用场景

验证结果（2026-10-12）：`37 passed`；覆盖会话轮换、固定到期、退出撤销、CSRF 校验、Cookie 偏好、表单错误脱敏及实例隔离。有一条 Starlette TestClient 使用 httpx 的依赖弃用提示。

### Stage 16：中间件与 CORS

- [x] 新建目录：`stage16_middleware_cors`
- [x] 编写 `main.py`
  - [x] 编写自定义请求日志中间件
  - [x] 统计请求耗时
  - [x] 配置 CORS
  - [x] 演示中间件执行顺序
- [x] 编写 `test_main.py`
  - [x] 测试中间件添加响应头
  - [x] 测试 CORS 预检请求
  - [x] 测试异常情况下中间件仍能工作
- [x] 编写 `README.md`
  - [x] 解释中间件的适用场景
  - [x] 说明 CORS 与浏览器跨域限制

验证结果（2026-10-12）：`27 passed`；覆盖中间件顺序、预检允许与拒绝、异常响应 CORS 头、日志脱敏及并发请求状态隔离。有一条 Starlette TestClient 使用 httpx 的依赖弃用提示。

### Stage 17：后台任务与邮件发送模拟

- [x] 新建目录：`stage17_background_tasks`
- [x] 编写 `main.py`
  - [x] 使用 `BackgroundTasks`
  - [x] 模拟注册后发送通知邮件
  - [x] 记录后台任务执行结果
  - [x] 说明后台任务的适用边界
- [x] 编写 `test_main.py`
  - [x] 测试接口立即返回
  - [x] 测试后台任务被触发
  - [x] 测试任务参数传递
- [x] 编写 `README.md`
  - [x] 解释后台任务与请求响应生命周期
  - [x] 说明何时需要 Celery 等任务队列

验证结果（2026-10-12）：`31 passed`；覆盖响应先于任务完成发送、参数传递、失败状态、重复任务保护、任务顺序和实例隔离。禁用 pytest 缓存后重跑通过，仅有一条 Starlette TestClient 使用 httpx 的依赖弃用提示。

### Stage 18：异步接口与外部 HTTP 调用

- [x] 新建目录：`stage18_async_http`
- [x] 编写 `main.py`
  - [x] 编写 async 路由
  - [x] 使用 `httpx.AsyncClient` 调用外部服务
  - [x] 处理超时与外部服务错误
  - [x] 封装外部 API 客户端
- [x] 编写 `test_main.py`
  - [x] 测试 async 路由
  - [x] mock 外部 HTTP 服务
  - [x] 测试超时与错误响应
- [x] 编写 `README.md`
  - [x] 解释同步与异步路由的区别
  - [x] 说明外部调用的超时设置为什么重要

验证结果（2026-10-12）：`43 passed`，无测试警告；覆盖客户端复用与关闭、超时与取消、上游协议错误、响应校验、配置和并发等待。附带可独立运行的本地模拟上游。

### Stage 19：WebSocket 入门

- [x] 新建目录：`stage19_websocket`
- [x] 编写 `main.py`
  - [x] 创建 WebSocket 连接
  - [x] 实现简单回声服务或聊天室
  - [x] 处理连接断开
  - [x] 管理多个连接
- [x] 编写 `test_main.py`
  - [x] 测试 WebSocket 连接成功
  - [x] 测试消息收发
  - [x] 测试连接关闭
- [x] 编写 `README.md`
  - [x] 解释 WebSocket 与 HTTP 的区别
  - [x] 说明实时通信的常见使用场景

验证结果（2026-10-12）：`34 passed`；覆盖多连接广播、断开清理、消息校验、Origin、容量复用、发送失败和并发顺序。有一条 Starlette TestClient 使用 httpx 的依赖弃用提示。

### Stage 20：测试进阶

- [x] 新建目录：`stage20_testing_advanced`
- [x] 编写 `main.py`
  - [x] 提供可测试的依赖结构
  - [x] 演示测试数据库与业务依赖
  - [x] 保留适合参数化测试的接口
- [x] 编写 `test_main.py`
  - [x] 使用 pytest fixture 分层
  - [x] 使用 dependency override
  - [x] 编写参数化测试
  - [x] 组合测试客户端与测试数据库
- [x] 编写 `README.md`
  - [x] 解释测试分层与夹具设计
  - [x] 说明如何让 FastAPI 应用更容易测试

验证结果（2026-10-12）：`47 passed`（unit 6、integration 41）；覆盖分层夹具、临时数据库隔离、依赖覆盖恢复、参数化边界及同一 Session 冲突后回滚。有一条 Starlette TestClient 使用 httpx 的依赖弃用提示。

### Stage 21：OpenAPI 文档与接口元数据

- [x] 新建目录：`stage21_openapi_docs`
- [x] 编写 `main.py`
  - [x] 配置 tags、summary、description
  - [x] 使用 `response_model` 与 `responses`
  - [x] 定制 OpenAPI schema
  - [x] 优化 Swagger UI 中的接口说明
- [x] 编写 `test_main.py`
  - [x] 测试 `/openapi.json` 可访问
  - [x] 断言关键接口元数据
  - [x] 测试错误响应文档存在
- [x] 编写 `README.md`
  - [x] 解释自动生成接口文档的价值
  - [x] 说明如何写出更清晰的接口元数据

验证结果（2026-10-12）：`31 passed`；覆盖元数据、请求示例、响应头、文档缓存、字段过滤及实际响应的 JSON Schema 校验。有一条 Starlette TestClient 使用 httpx 的依赖弃用提示。

### Stage 22：日志与可观测性基础

- [x] 新建目录：`stage22_logging_observability`
- [x] 编写 `main.py`
  - [x] 配置标准 `logging`
  - [x] 记录请求日志
  - [x] 记录错误日志
  - [x] 添加健康检查与 readiness/liveness 示例
- [x] 编写 `test_main.py`
  - [x] 测试健康检查接口
  - [x] 测试日志记录被触发
  - [x] 测试错误路径可观测
- [x] 编写 `README.md`
  - [x] 解释日志、健康检查与可观测性的基础关系
  - [x] 说明生产排障时需要哪些信息

验证结果（2026-10-12）：`19 passed`；覆盖 JSON 日志白名单、请求与错误关联、并发隔离、探针故障与恢复，以及响应开始后的异常记录。有一条 Starlette TestClient 使用 httpx 的依赖弃用提示。

### Stage 23：应用生命周期与资源管理

- [x] 新建目录：`stage23_lifespan`
- [x] 编写 `main.py`
  - [x] 使用 lifespan 管理应用生命周期
  - [x] 演示 startup/shutdown 替代写法
  - [x] 初始化共享资源
  - [x] 在关闭时释放资源
- [x] 编写 `test_main.py`
  - [x] 测试生命周期启动逻辑
  - [x] 测试生命周期关闭逻辑
  - [x] 测试共享资源可用
- [x] 编写 `README.md`
  - [x] 解释 lifespan 的使用场景
  - [x] 说明资源初始化与释放的常见坑

验证结果（2026-10-12）：`21 passed`；覆盖启动与关闭、共享连接复用、部分启动失败清理、重复生命周期、取消清理和显式异步生命周期测试。有一条 Starlette TestClient 使用 httpx 的依赖弃用提示。

### Stage 24：部署入门

- [x] 新建目录：`stage24_deployment`
- [x] 编写 `main.py`
  - [x] 提供可部署的最小应用
  - [x] 增加健康检查接口
  - [x] 演示读取生产配置
- [x] 编写 `test_main.py`
  - [x] 测试部署入口应用
  - [x] 测试健康检查接口
- [x] 编写 `README.md`
  - [x] 说明 Uvicorn 常用运行参数
  - [x] 说明 Gunicorn + Uvicorn Worker 的基本用法
  - [x] 提供 Dockerfile 示例
  - [x] 总结生产环境配置注意事项

验证结果（2026-10-12）：`29 passed`；覆盖部署入口、生产配置校验、Host 白名单、文档开关和健康探针。有一条 Starlette TestClient 使用 httpx 的依赖弃用提示。Docker Linux 引擎未运行，未完成镜像构建和容器验证；原生 Windows 未执行 Gunicorn。

### Stage 25：综合项目 Mini API

- [x] 新建目录：`stage25_mini_api`
- [x] 编写 `main.py`
  - [x] 整合用户、鉴权、数据库、分页、异常、配置、测试
  - [x] 形成一个小型但完整的 FastAPI 后端项目
  - [x] 保持模块结构清晰，避免过度封装
- [x] 编写 `test_main.py`
  - [x] 覆盖注册、登录、鉴权、CRUD、分页、异常路径
  - [x] 使用测试数据库与依赖覆盖
  - [x] 验证主要业务流程
- [x] 编写 `README.md`
  - [x] 给出完整运行与测试说明
  - [x] 回顾 Stage 01-24 的关键知识点
  - [x] 提供后续扩展路线

验证结果（2026-10-12）：`86 passed`；覆盖注册与哈希、JWT 声明校验、账号状态、角色即时变化、任务所有权隔离、CRUD、分页排序过滤、错误脱敏与事务回滚。真实 HTTP/CLI 验证了重复初始化、角色升降级和重启后的数据保留。有一条 Starlette TestClient 使用 httpx 的依赖弃用提示。

---

## 每阶段通用验收标准（DoD）

- [ ] 目录中必须包含：`main.py`、`README.md`、`test_main.py`
- [ ] 示例可直接运行
- [ ] 中文注释聚焦关键设计点，不机械逐行注释
- [ ] `README.md` 包含以下固定章节：
  - [ ] 本阶段学习目标
  - [ ] 核心概念
  - [ ] 运行命令
  - [ ] 测试命令
  - [ ] 示例请求
  - [ ] 预期返回
  - [ ] 常见错误
  - [ ] 小练习
- [ ] 本阶段 `pytest` 全部通过

---

## 推荐执行方式

每次只推进一个 stage，流程固定为：

1. 先写最小可运行 `main.py`
2. 再写最小覆盖的 `test_main.py`
3. 最后补齐中文 `README.md`
4. 运行测试并记录结果
5. 输出阶段总结（新增内容/运行方式/测试方式/适合学习点）
