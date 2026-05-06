# fastapi-learning-lab 任务清单（基于当前最新代码）

> 当前已完成：`stage01_hello_fastapi`、`stage02_params`。

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
  - [x] 参数类型校验（`int`、`bool`）
- [x] 编写 `test_main.py`
  - [x] 正常参数测试
  - [x] 非法参数 422 测试
- [x] 编写 `README.md`
  - [x] 解释路径参数与查询参数差异
  - [x] 增加常见错误（422、参数类型错误）

### Stage 03：请求体与 Pydantic 模型

- [ ] 新建目录：`stage03_pydantic_body`
- [ ] 编写 `main.py`
  - [ ] `POST /items`，使用 BaseModel
  - [ ] 字段默认值与可选字段
  - [ ] 响应模型 `response_model`
- [ ] 编写 `test_main.py`
  - [ ] 请求体合法/非法测试
  - [ ] 响应字段断言
- [ ] 编写 `README.md`
  - [ ] 解释数据校验与错误返回

### Stage 04：依赖注入（Depends）

- [ ] 新建目录：`stage04_depends`
- [ ] 编写 `main.py`
  - [ ] 公共查询参数依赖
  - [ ] 简单鉴权依赖（Header Token）
- [ ] 编写 `test_main.py`
  - [ ] 正常请求与鉴权失败请求
- [ ] 编写 `README.md`
  - [ ] 解释依赖复用场景

### Stage 05：数据库入门（SQLite + SQLModel/SQLAlchemy）

- [ ] 新建目录：`stage05_sqlite`
- [ ] 编写 `main.py`
  - [ ] SQLite 本地库
  - [ ] 基础 CRUD（增删改查）
- [ ] 编写 `test_main.py`
  - [ ] 测试隔离（临时数据库）
- [ ] 编写 `README.md`
  - [ ] 数据库初始化与迁移说明（入门级）

### Stage 06：项目结构化与路由拆分

- [ ] 新建目录：`stage06_project_layout`
- [ ] 拆分 `routers/`、`schemas/`、`services/`
- [ ] 统一异常处理与响应格式（轻量版）
- [ ] 完善对应测试与文档

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
