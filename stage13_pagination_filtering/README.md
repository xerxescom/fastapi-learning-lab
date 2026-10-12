# Stage 13：分页、排序与过滤

## 本阶段学习目标

- 在 SQLite 查询中实现两种分页，而不是先加载全部记录再切片。
- 组合关键词、分类、库存与价格过滤，并返回过滤后的总数。
- 使用查询参数模型约束边界，用排序白名单保证查询可控。
- 测试空结果、越界页、同价商品排序和非法参数。

## 核心概念

### 两种分页方式

| 接口 | 默认参数 | 响应元数据 |
| --- | --- | --- |
| `GET /items` | `limit=10&offset=0` | `total`、`limit`、`offset` |
| `GET /items/pages` | `page=1&page_size=10` | `total`、`page`、`page_size`、`pages` |

两者共享 `app/services.py` 的查询逻辑。页码从 1 开始，换算公式为 `offset = (page - 1) * page_size`；总页数为向上取整的 `total / page_size`，零条结果对应零页。

查询先应用过滤条件，单独统计 `total`，再对匹配记录排序并执行 `LIMIT/OFFSET`。因此 `total` 不是当前页的记录数，也不是未过滤的全表记录数。合法但超出结果范围的页返回 200 和空 `items`，保留请求的页码。

### 参数校验

| 参数 | 规则 |
| --- | --- |
| `limit`、`page_size` | 1 到 100 |
| `offset` | 0 到 1,000,000 |
| `page` | 1 到 10,000 |
| `q` | 可选；去除首尾空白后长度为 1 到 50，匹配商品名称 |
| `category` | 可选；`office` 或 `accessories` |
| `in_stock` | 可选布尔值；显式传 `false` 也必须参与过滤 |
| `min_price`、`max_price` | 可选；有限且非负，包含边界，下限不能大于上限 |
| `sort_by` | `id`、`name` 或 `price`，默认 `id` |
| `order` | `asc` 或 `desc`，默认 `asc` |

使用 `Annotated[参数模型, Query()]` 将 Pydantic 模型展开为查询参数，自动生成 OpenAPI 文档。`extra="forbid"` 拒绝拼错或多余的参数，也拒绝混用两种分页参数。非法参数返回 FastAPI 默认的 422 响应；跨字段价格校验同样属于请求校验。

排序字段通过白名单映射到 SQLAlchemy 列，不拼接用户提供的 SQL。按名称或价格排序时，额外按 ID 升序排列，让相同值的记录顺序稳定。名称排序使用 SQLite 默认排序规则，不等同于中文拼音或自然排序。

关键词查询使用 `icontains(..., autoescape=True)`：示例中的英文名称可忽略大小写匹配，`%` 和 `_` 作为字面字符，而不是用户可控的 SQL 通配符。Unicode 大小写行为取决于数据库，不应假设所有语言都等价。

### 数据与模块

`database.py` 提供数据库会话依赖；`models.py` 定义商品表；`schemas.py` 定义查询和响应模型；`services.py` 构建查询；`routers.py` 负责参数与响应；`seed.py` 提供教学数据。

初始化空表时按以下顺序插入 8 条记录：

| ID | 名称 | 价格 | 分类 | 有库存 |
| --- | --- | --- | --- | --- |
| 1 | Keyboard | 99 | office | true |
| 2 | Mouse | 49 | accessories | true |
| 3 | Monitor | 199 | office | false |
| 4 | USB Cable | 19 | accessories | true |
| 5 | Desk Lamp | 49 | office | true |
| 6 | Laptop Stand | 49 | office | false |
| 7 | 100% Cotton Case | 29 | accessories | true |
| 8 | Under_score Pad | 19 | accessories | false |

本阶段独立运行，不要求先启动之前的阶段，也不重复引入用户鉴权和统一响应封装。价格采用浮点数仅用于教学，真实金额通常使用定点类型或整数最小货币单位。

参考：[FastAPI 查询参数模型](https://fastapi.tiangolo.com/tutorial/query-param-models/)。此写法要求 FastAPI 0.115.0 或更新版本。

## 运行命令

在仓库根目录使用已有 Python 环境，或激活根目录虚拟环境：

```powershell
.\.venv\Scripts\Activate.ps1
cd stage13_pagination_filtering
python -m pip install -r requirements.txt
python init_db.py
python -m uvicorn main:app --reload
```

访问 `http://127.0.0.1:8000/docs`。默认数据库为当前阶段目录的 `items.db`，已被 Git 忽略。需要自定义时，可将 `.env.example` 复制为 `.env`，设置 `LAB_DATABASE_URL`；同名环境变量优先。

必须在本阶段目录执行命令，避免相对 SQLite 路径落到其他目录。初始化脚本使用 `create_all` 建表，仅在商品表为空时插入样例数据；重复执行保留已有数据，不覆盖修改，也不补齐部分删除的数据。它不是并发运行的生产数据导入器。

`create_all` 不负责修改已有表结构；结构演进请回看 Stage 08 的 Alembic 迁移。

## 测试命令

在本阶段目录运行：

```powershell
python -m pytest -q
```

测试使用每个用例独立的临时 SQLite 数据库，通过 `dependency_overrides` 替换会话依赖，不读写学习用的 `items.db`。

覆盖两种分页、过滤后总数、稳定排序、组合过滤、字面通配符、空表、空结果、合法越界、参数边界、重复初始化及 OpenAPI 查询参数声明。

验证记录（2026-10-12）：`57 passed`。有一条 Starlette TestClient 使用 httpx 的依赖弃用提示，不影响测试通过。连续执行两次初始化脚本，分别确认插入样例和保留已有数据。

若 Windows 环境限制了默认临时目录权限，可指定一个可写目录后重试：

```powershell
$env:TEMP = Join-Path (Resolve-Path ..\.venv).Path 'pytest-tmp'
New-Item -ItemType Directory -Force -Path $env:TEMP | Out-Null
$env:TMP = $env:TEMP
python -m pytest -q
```

## 示例请求

PowerShell 中使用 `curl.exe`，并为包含 `&` 的 URL 加引号：

```powershell
curl.exe "http://127.0.0.1:8000/items?limit=2&offset=2"
curl.exe "http://127.0.0.1:8000/items/pages?page=2&page_size=3"
curl.exe "http://127.0.0.1:8000/items?category=office&in_stock=false&min_price=0&max_price=100"
curl.exe "http://127.0.0.1:8000/items/pages?in_stock=true&sort_by=price&order=desc&page=2&page_size=2"
curl.exe "http://127.0.0.1:8000/items?q=%25"
curl.exe "http://127.0.0.1:8000/items/pages?q=notfound"
curl.exe "http://127.0.0.1:8000/items?min_price=100&max_price=10"
```

`%25` 是 URL 编码后的 `%`，会匹配 `100% Cotton Case`。

## 预期返回

以下示例基于刚初始化、尚未修改的数据。第一个请求跳过两条记录后返回两条，`total` 仍为 8：

```json
{
  "items": [
    {"id": 3, "name": "Monitor", "price": 199.0, "category": "office", "in_stock": false},
    {"id": 4, "name": "USB Cable", "price": 19.0, "category": "accessories", "in_stock": true}
  ],
  "total": 8,
  "limit": 2,
  "offset": 2
}
```

第二个请求返回 ID 4、5、6，元数据为 `total=8`、`page=2`、`page_size=3`、`pages=3`。办公用品、无库存且价格不超过 100 的组合过滤仅返回 ID 6。

有库存商品按价格降序的第二页返回 ID 5、7，元数据为 `total=5`、`page=2`、`page_size=2`、`pages=3`。同价商品始终按 ID 升序排列。

无匹配结果时：

```json
{"items": [], "total": 0, "page": 1, "page_size": 10, "pages": 0}
```

最后一个请求价格区间颠倒，返回 HTTP 422，`detail` 包含查询参数校验错误，不返回 500。

## 常见错误

- `no such table: items`：先在阶段目录运行 `python init_db.py`。
- 把 `page` 设为 0，或把 `limit` 设为 0/101：超出参数边界，返回 422。
- 向 `/items` 传 `page`，或向 `/items/pages` 传 `limit`：两种分页契约不同，多余参数被拒绝。
- 用 `if in_stock` 判断是否添加过滤：会漏掉 `false`；可选参数应检查 `is not None`，价格 0 也一样。
- 用 `len(items)` 当作总数：这是当前页数量，必须在分页前统计匹配总数。
- 忘记稳定排序：同价记录跨页可能出现顺序不确定。ID 次排序解决同值排序问题，但不保证数据变化时的分页快照一致性。
- 深分页性能差：较大的 OFFSET 仍有扫描成本，参数上限并不保证性能。并发插入、删除也可能造成跨页漂移；本例的计数与取页是两次查询，未承诺并发写入时的原子快照。

## 小练习

1. 新增品牌过滤，为共享查询逻辑和两种接口补上测试。
2. 添加 `has_next`，明确空结果与越界页时的行为。
3. 为中文名称设计明确的排序需求，比较数据库排序规则与应用层排序的取舍。
4. 尝试基于 ID 的游标分页，对比深分页效率和并发修改下的行为。
