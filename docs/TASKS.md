# fastapi-learning-lab 任务清单（基于当前最新代码）

> 当前已完成：`stage01_hello_fastapi`、`stage02_params`、`stage03_pydantic_body`、`stage04_depends`、`stage05_sqlite`、`stage06_project_layout`（均含应用、测试、中文文档）。

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

- [ ] 新建目录：`stage07_settings_env`
- [ ] 编写 `main.py`
  - [ ] 使用 `pydantic-settings` 管理配置
  - [ ] 支持 `.env` 示例
  - [ ] 区分开发配置与测试配置
  - [ ] 演示配置项默认值与类型校验
- [ ] 编写 `test_main.py`
  - [ ] 测试默认配置读取
  - [ ] 测试配置覆盖与校验
- [ ] 编写 `README.md`
  - [ ] 解释为什么不要把配置硬编码在业务代码中
  - [ ] 说明环境变量、`.env` 与测试配置的关系

### Stage 08：数据库进阶与 Alembic 迁移

- [ ] 新建目录：`stage08_alembic_migrations`
- [ ] 编写 `main.py`
  - [ ] 拆分 SQLAlchemy 模型、数据库会话与路由
  - [ ] 初始化 Alembic 迁移目录
  - [ ] 演示生成迁移与执行迁移
  - [ ] 使用依赖注入提供数据库会话
- [ ] 编写 `test_main.py`
  - [ ] 使用测试数据库隔离 CRUD 测试
  - [ ] 验证数据库会话依赖可覆盖
- [ ] 编写 `README.md`
  - [ ] 解释 `create_all` 与 Alembic 迁移的区别
  - [ ] 给出常用迁移命令

### Stage 09：用户注册与密码安全

- [ ] 新建目录：`stage09_user_register_password`
- [ ] 编写 `main.py`
  - [ ] 定义用户模型与用户响应模型
  - [ ] 使用密码哈希保存密码
  - [ ] 实现用户注册接口
  - [ ] 处理重复用户名或邮箱
- [ ] 编写 `test_main.py`
  - [ ] 测试注册成功
  - [ ] 测试密码不会明文返回
  - [ ] 测试重复用户与非法输入
- [ ] 编写 `README.md`
  - [ ] 解释密码哈希与明文密码的风险
  - [ ] 说明注册接口的常见校验点

### Stage 10：JWT 登录与鉴权进阶

- [ ] 新建目录：`stage10_jwt_auth`
- [ ] 编写 `main.py`
  - [ ] 实现登录接口
  - [ ] 签发 JWT access token
  - [ ] 编写获取当前用户的依赖
  - [ ] 创建受保护路由
  - [ ] 区分 401 与 403 的使用场景
- [ ] 编写 `test_main.py`
  - [ ] 测试登录成功与失败
  - [ ] 测试携带 token 访问受保护路由
  - [ ] 测试缺失、错误、过期 token
- [ ] 编写 `README.md`
  - [ ] 解释 JWT 的基本结构与适用边界
  - [ ] 说明 Bearer Token 的请求方式

### Stage 11：权限与角色控制

- [ ] 新建目录：`stage11_roles_permissions`
- [ ] 编写 `main.py`
  - [ ] 增加普通用户与管理员角色
  - [ ] 编写路由级权限依赖
  - [ ] 创建仅管理员可访问的接口
  - [ ] 演示最小 RBAC 设计
- [ ] 编写 `test_main.py`
  - [ ] 测试普通用户权限不足
  - [ ] 测试管理员访问成功
  - [ ] 测试未登录访问失败
- [ ] 编写 `README.md`
  - [ ] 解释认证与授权的区别
  - [ ] 说明角色权限依赖的复用方式

### Stage 12：请求响应规范与全局异常处理

- [ ] 新建目录：`stage12_response_errors`
- [ ] 编写 `main.py`
  - [ ] 定义统一成功响应格式
  - [ ] 定义统一错误响应格式
  - [ ] 创建自定义业务异常
  - [ ] 覆盖 404、422、500 的轻量示例
- [ ] 编写 `test_main.py`
  - [ ] 测试成功响应结构
  - [ ] 测试业务异常响应结构
  - [ ] 测试请求校验错误响应结构
- [ ] 编写 `README.md`
  - [ ] 解释统一响应格式的收益与取舍
  - [ ] 说明 FastAPI 默认异常与自定义异常的关系

### Stage 13：分页、排序与过滤

- [ ] 新建目录：`stage13_pagination_filtering`
- [ ] 编写 `main.py`
  - [ ] 实现 `limit/offset` 分页
  - [ ] 实现 `page/page_size` 分页
  - [ ] 支持排序参数
  - [ ] 支持基础条件过滤
- [ ] 编写 `test_main.py`
  - [ ] 测试分页结果与总数
  - [ ] 测试排序结果
  - [ ] 测试过滤条件
  - [ ] 测试参数边界
- [ ] 编写 `README.md`
  - [ ] 对比两种常见分页方式
  - [ ] 说明分页参数的边界限制

### Stage 14：文件上传与静态文件

- [ ] 新建目录：`stage14_upload_static_files`
- [ ] 编写 `main.py`
  - [ ] 使用 `UploadFile` 接收文件
  - [ ] 校验文件类型与大小
  - [ ] 挂载静态文件目录
  - [ ] 返回可访问的文件 URL
- [ ] 编写 `test_main.py`
  - [ ] 测试文件上传成功
  - [ ] 测试非法文件类型
  - [ ] 测试静态文件访问
- [ ] 编写 `README.md`
  - [ ] 解释 `UploadFile` 与普通表单字段的区别
  - [ ] 说明生产环境文件存储的扩展方向

### Stage 15：表单、Cookie 与 Session 基础

- [ ] 新建目录：`stage15_form_cookie_session`
- [ ] 编写 `main.py`
  - [ ] 实现表单登录示例
  - [ ] 演示 Cookie 读写
  - [ ] 演示简单 Session 思路
  - [ ] 对比 Cookie Session 与 JWT
- [ ] 编写 `test_main.py`
  - [ ] 测试表单提交
  - [ ] 测试 Cookie 设置与读取
  - [ ] 测试 Session 状态
- [ ] 编写 `README.md`
  - [ ] 解释表单请求与 JSON 请求的区别
  - [ ] 说明 Cookie、Session、JWT 的适用场景

### Stage 16：中间件与 CORS

- [ ] 新建目录：`stage16_middleware_cors`
- [ ] 编写 `main.py`
  - [ ] 编写自定义请求日志中间件
  - [ ] 统计请求耗时
  - [ ] 配置 CORS
  - [ ] 演示中间件执行顺序
- [ ] 编写 `test_main.py`
  - [ ] 测试中间件添加响应头
  - [ ] 测试 CORS 预检请求
  - [ ] 测试异常情况下中间件仍能工作
- [ ] 编写 `README.md`
  - [ ] 解释中间件的适用场景
  - [ ] 说明 CORS 与浏览器跨域限制

### Stage 17：后台任务与邮件发送模拟

- [ ] 新建目录：`stage17_background_tasks`
- [ ] 编写 `main.py`
  - [ ] 使用 `BackgroundTasks`
  - [ ] 模拟注册后发送通知邮件
  - [ ] 记录后台任务执行结果
  - [ ] 说明后台任务的适用边界
- [ ] 编写 `test_main.py`
  - [ ] 测试接口立即返回
  - [ ] 测试后台任务被触发
  - [ ] 测试任务参数传递
- [ ] 编写 `README.md`
  - [ ] 解释后台任务与请求响应生命周期
  - [ ] 说明何时需要 Celery 等任务队列

### Stage 18：异步接口与外部 HTTP 调用

- [ ] 新建目录：`stage18_async_http`
- [ ] 编写 `main.py`
  - [ ] 编写 async 路由
  - [ ] 使用 `httpx.AsyncClient` 调用外部服务
  - [ ] 处理超时与外部服务错误
  - [ ] 封装外部 API 客户端
- [ ] 编写 `test_main.py`
  - [ ] 测试 async 路由
  - [ ] mock 外部 HTTP 服务
  - [ ] 测试超时与错误响应
- [ ] 编写 `README.md`
  - [ ] 解释同步与异步路由的区别
  - [ ] 说明外部调用的超时设置为什么重要

### Stage 19：WebSocket 入门

- [ ] 新建目录：`stage19_websocket`
- [ ] 编写 `main.py`
  - [ ] 创建 WebSocket 连接
  - [ ] 实现简单回声服务或聊天室
  - [ ] 处理连接断开
  - [ ] 管理多个连接
- [ ] 编写 `test_main.py`
  - [ ] 测试 WebSocket 连接成功
  - [ ] 测试消息收发
  - [ ] 测试连接关闭
- [ ] 编写 `README.md`
  - [ ] 解释 WebSocket 与 HTTP 的区别
  - [ ] 说明实时通信的常见使用场景

### Stage 20：测试进阶

- [ ] 新建目录：`stage20_testing_advanced`
- [ ] 编写 `main.py`
  - [ ] 提供可测试的依赖结构
  - [ ] 演示测试数据库与业务依赖
  - [ ] 保留适合参数化测试的接口
- [ ] 编写 `test_main.py`
  - [ ] 使用 pytest fixture 分层
  - [ ] 使用 dependency override
  - [ ] 编写参数化测试
  - [ ] 组合测试客户端与测试数据库
- [ ] 编写 `README.md`
  - [ ] 解释测试分层与夹具设计
  - [ ] 说明如何让 FastAPI 应用更容易测试

### Stage 21：OpenAPI 文档与接口元数据

- [ ] 新建目录：`stage21_openapi_docs`
- [ ] 编写 `main.py`
  - [ ] 配置 tags、summary、description
  - [ ] 使用 `response_model` 与 `responses`
  - [ ] 定制 OpenAPI schema
  - [ ] 优化 Swagger UI 中的接口说明
- [ ] 编写 `test_main.py`
  - [ ] 测试 `/openapi.json` 可访问
  - [ ] 断言关键接口元数据
  - [ ] 测试错误响应文档存在
- [ ] 编写 `README.md`
  - [ ] 解释自动生成接口文档的价值
  - [ ] 说明如何写出更清晰的接口元数据

### Stage 22：日志与可观测性基础

- [ ] 新建目录：`stage22_logging_observability`
- [ ] 编写 `main.py`
  - [ ] 配置标准 `logging`
  - [ ] 记录请求日志
  - [ ] 记录错误日志
  - [ ] 添加健康检查与 readiness/liveness 示例
- [ ] 编写 `test_main.py`
  - [ ] 测试健康检查接口
  - [ ] 测试日志记录被触发
  - [ ] 测试错误路径可观测
- [ ] 编写 `README.md`
  - [ ] 解释日志、健康检查与可观测性的基础关系
  - [ ] 说明生产排障时需要哪些信息

### Stage 23：应用生命周期与资源管理

- [ ] 新建目录：`stage23_lifespan`
- [ ] 编写 `main.py`
  - [ ] 使用 lifespan 管理应用生命周期
  - [ ] 演示 startup/shutdown 替代写法
  - [ ] 初始化共享资源
  - [ ] 在关闭时释放资源
- [ ] 编写 `test_main.py`
  - [ ] 测试生命周期启动逻辑
  - [ ] 测试生命周期关闭逻辑
  - [ ] 测试共享资源可用
- [ ] 编写 `README.md`
  - [ ] 解释 lifespan 的使用场景
  - [ ] 说明资源初始化与释放的常见坑

### Stage 24：部署入门

- [ ] 新建目录：`stage24_deployment`
- [ ] 编写 `main.py`
  - [ ] 提供可部署的最小应用
  - [ ] 增加健康检查接口
  - [ ] 演示读取生产配置
- [ ] 编写 `test_main.py`
  - [ ] 测试部署入口应用
  - [ ] 测试健康检查接口
- [ ] 编写 `README.md`
  - [ ] 说明 Uvicorn 常用运行参数
  - [ ] 说明 Gunicorn + Uvicorn Worker 的基本用法
  - [ ] 提供 Dockerfile 示例
  - [ ] 总结生产环境配置注意事项

### Stage 25：综合项目 Mini API

- [ ] 新建目录：`stage25_mini_api`
- [ ] 编写 `main.py`
  - [ ] 整合用户、鉴权、数据库、分页、异常、配置、测试
  - [ ] 形成一个小型但完整的 FastAPI 后端项目
  - [ ] 保持模块结构清晰，避免过度封装
- [ ] 编写 `test_main.py`
  - [ ] 覆盖注册、登录、鉴权、CRUD、分页、异常路径
  - [ ] 使用测试数据库与依赖覆盖
  - [ ] 验证主要业务流程
- [ ] 编写 `README.md`
  - [ ] 给出完整运行与测试说明
  - [ ] 回顾 Stage 01-24 的关键知识点
  - [ ] 提供后续扩展路线

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
