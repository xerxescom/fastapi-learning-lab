# Stage 20：测试进阶

## 本阶段学习目标

- 使用 `conftest.py` 分层管理 pytest fixture。
- 组合临时数据库、请求级会话、数据工厂和 TestClient。
- 用 `dependency_overrides` 替换数据库和业务依赖，并保证恢复。
- 通过参数化测试覆盖输入边界、业务规则和隔离行为。
- 区分不访问数据库的单元测试、数据库服务测试与 API 集成测试。

## 核心概念

### 用一个小 API 练测试

本例提供任务创建、查询、筛选、完成状态修改和删除。标题去除首尾空白后为 1 到 80 个字符，标题唯一；PATCH 的 completed 只接受 JSON 布尔值。业务配额默认 100 条，测试替换为 3 条。

`app/database.py` 提供请求级会话依赖；`app/services.py` 提供业务函数和配额依赖；`main.py` 组装接口。`init_db.py` 显式建表，导入模块或启动测试不会自动修改应用数据库。

配额检查使用先计数再插入，目的是演示业务依赖替换，不保证并发请求下的严格配额；真实系统需更完整的事务与并发设计。本例也没有身份认证，仅用于本地测试学习。

### 夹具依赖图

```text
tmp_path -> db_engine -> application -> client
                    -> db_session -> task_factory
application -> override_dependency
```

| Fixture | 职责 |
| --- | --- |
| `db_engine` | 在当前用例的临时目录建 SQLite 表，结束时释放连接池 |
| `db_session` | 提供直接查询或服务测试使用的独立 Session |
| `application` | 创建独立应用，覆盖数据库和业务策略依赖，结束时恢复 |
| `client` | 进入 TestClient 上下文，运行应用生命周期 |
| `task_factory` | 按需插入并提交不同测试数据 |
| `override_dependency` | 用上下文临时覆盖某个依赖，并恢复其原值 |

所有这些 fixture 默认 function scope。测试函数按名字声明所需 fixture，pytest 按依赖顺序创建，按相反顺序清理；不必手动调用 fixture 函数。纯业务测试不声明数据库 fixture，因此不会为它们建表。

本阶段优先清晰可靠的“每用例一个临时数据库”，不是共用一个全局库再尝试清空。将数据库 fixture 改成 session scope 会引入跨用例状态，不能仅为了加速就放大 scope。

### 依赖覆盖不是 monkeypatch 一切

覆盖键必须是路由 `Depends` 使用的那个函数对象：

```python
application.dependency_overrides[get_db] = override_db
application.dependency_overrides[get_policy] = lambda: TaskPolicy(max_tasks=3)
```

这个机制只影响 FastAPI 解析依赖，不会替换业务代码直接调用的普通函数。使用应用工厂可以让每个测试拥有独立的覆盖字典，避免全局 app 污染。

临时覆盖使用上下文：

```python
with override_dependency(get_policy, lambda: TaskPolicy(max_tasks=0)):
    response = client.post('/tasks', json={'title': 'blocked'})
    assert response.status_code == 409
```

上下文无论正常返回还是抛异常都会恢复原值，也支持嵌套。不要在共享应用处理其他请求时随意修改覆盖表；它不是面向生产并发请求的动态配置机制。

### 数据库隔离与断言

应用夹具配置一个 `must-not-use.db` 哨兵路径，再用 `get_db` 覆盖指向临时测试库。结束时检查哨兵文件从未出现，帮助发现漏用覆盖的错误。它是本示例的保护措施，不是通用数据库访问沙箱。

HTTP 请求使用每次请求新建的 Session，不复用测试的 `db_session`。数据工厂写入后 commit，其他会话才能读到；响应可与直接查询数据库的结果交叉断言。SQLAlchemy 的身份映射可能缓存对象，其他会话修改后必要时调用 `expire_all()` 或重新查询。

本例通过临时文件库隔离线程访问，不使用默认的 `sqlite:///:memory:`；内存库与连接池搭配不当时，不同连接可能看到不同数据库。`check_same_thread=False` 仅允许 SQLite 连接跨线程使用，不代表可以并发共享同一个 Session。

服务测试直接制造唯一约束冲突，确认 rollback 后**同一个** Session 还能继续提交，避免仅用下一次 HTTP 请求掩盖会话已失效的问题。

### 测试分层与参数化

| 文件 | 类型 | 重点 |
| --- | --- | --- |
| `tests/test_capacity.py` | unit | 纯业务边界，无 HTTP 或数据库 fixture |
| `tests/test_services.py` | integration | 真实 SQLite、提交、冲突与回滚 |
| `test_main.py` | integration | HTTP 校验、CRUD、依赖替换与数据库组合 |

`pytest.ini` 注册 unit/integration 标记并限制本阶段收集路径。参数化让每组输入成为独立用例，便于定位失败；这里覆盖标题、分页、严格布尔值、404 行为与配额。隔离用例分别创建相同标题，验证第二组不会受第一组数据影响，不依赖测试执行顺序。

测试夹具不要过度 autouse，避免每个纯业务用例都启动 HTTP 客户端或数据库。本例数据工厂直接构造数据库记录是测试准备，不表示生产接口可以绕过业务校验。

SQLite 测试不能证明其他数据库的锁、事务隔离与方言行为完全正确。以后切换数据库时，需要对应数据库的集成测试；也不要把“全部断言通过”等同于并发、安全和性能已全部验收。

参考：[FastAPI 依赖覆盖](https://fastapi.tiangolo.com/advanced/testing-dependencies/)、[pytest fixture](https://docs.pytest.org/en/stable/how-to/fixtures.html)、[参数化测试](https://docs.pytest.org/en/stable/how-to/parametrize.html)。

## 运行命令

在仓库根目录激活已有环境，再进入本阶段：

```powershell
.\.venv\Scripts\Activate.ps1
cd stage20_testing_advanced
python -m pip install -r requirements.txt
python init_db.py
python -m uvicorn main:app --reload
```

文档地址为 `http://127.0.0.1:8000/docs`。默认数据库固定为阶段目录的 `tasks.db`，已被 Git 忽略。初始化使用 `create_all`，可重复执行但不会迁移已有表结构；迁移请回看 Stage 08。

## 测试命令

在本阶段目录执行，不需要运行 init_db 或启动服务：

```powershell
python -m pytest -q -p no:cacheprovider
python -m pytest -q -m unit -p no:cacheprovider
python -m pytest -q -m integration -p no:cacheprovider
python -m pytest -v test_main.py -k override -p no:cacheprovider
```

始终在本阶段目录运行，避免仓库其他独立阶段中的同名 `app` 模块干扰导入。`-p no:cacheprovider` 避免本机沙箱缓存目录权限问题，普通环境可省略。

若默认临时目录权限受限，可设置可写目录再运行：

```powershell
$env:TEMP = Join-Path (Resolve-Path ..\.venv).Path 'pytest-tmp'
New-Item -ItemType Directory -Force -Path $env:TEMP | Out-Null
$env:TMP = $env:TEMP
python -m pytest -q -p no:cacheprovider
```

验证记录（2026-10-12）：`47 passed`，其中 unit 6 项、integration 41 项。有一条 Starlette TestClient 使用 httpx 的依赖弃用提示，不影响测试通过。

## 示例请求

在另一个 PowerShell 窗口执行：

```powershell
$base = 'http://127.0.0.1:8000'
$task = Invoke-RestMethod "$base/tasks" -Method Post -ContentType 'application/json' -Body '{"title":"Learn fixtures"}'
Invoke-RestMethod "$base/tasks/$($task.id)"
Invoke-RestMethod "$base/tasks/$($task.id)" -Method Patch -ContentType 'application/json' -Body '{"completed":true}'
Invoke-RestMethod "$base/tasks?completed=true&limit=10&offset=0"
Invoke-WebRequest "$base/tasks/$($task.id)" -Method Delete
```

再次提交相同标题会返回 409；PATCH 提交 `{"completed":"true"}` 而不是布尔值时返回 422。

## 预期返回

首次创建返回 HTTP 201，ID 由数据库生成：

```json
{"id": 1, "title": "Learn fixtures", "completed": false}
```

修改后返回 HTTP 200 和 `completed=true`，列表查询返回数组。DELETE 返回 HTTP 204、无响应体，再查询该记录返回 404。

重复标题返回 HTTP 409：

```json
{"detail": "Task title already exists"}
```

配额达到上限返回 HTTP 409 和 `{"detail":"Task capacity reached"}`。测试覆盖可设置为 0 立即触发，无需创建 100 条记录。

## 常见错误

- 测试提示找不到 tasks 表：检查测试引擎是否建表、get_db 是否指向正确引擎，而不是先初始化学习库来掩盖错误。
- 运行应用提示找不到表：正常运行则需要先执行 `python init_db.py`。
- 测试创建了学习库文件：检查依赖键的函数对象与 app 实例是否一致。
- 测试数据接口不可见：不同会话之间需要提交，不要只 flush。
- 唯一冲突后 Session 不能继续使用：执行 rollback，服务测试应覆盖该行为。
- 一个测试改变了其他测试的配额：检查 override 是否恢复，避免共用全局应用。
- 想在所有地方复用一个 Session：Session 不是线程安全的全局连接，不要跨请求并发共享。
- 放大 fixture scope 后测试依赖顺序：先解决隔离设计，不能靠固定执行顺序修复。
- 单元测试也出现 TestClient 导入提示：conftest 被加载不代表数据库 fixture 被执行，可检查实际测试依赖和标记。

## 小练习

1. 为删除后重新创建、重复标题大小写等行为补测试，先明确业务契约。
2. 添加可替换的时间依赖，固定测试时间，不使用 sleep 验证业务到期。
3. 研究事务回滚/SAVEPOINT 夹具，验证接口内部 commit 后仍能隔离，并比较 SQLite 与目标数据库。
4. 增加 CI 流程，分别执行 unit 与 integration，同时验证覆盖率统计不替代行为断言。
