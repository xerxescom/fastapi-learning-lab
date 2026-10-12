# 阶段 07：配置管理与环境变量

## 本阶段学习目标

- 使用 `pydantic-settings` 将配置从接口逻辑中提取出来。
- 理解默认值、`.env`、环境变量与显式传参之间的优先级。
- 使用 `Depends` 注入配置，并隔离开发环境与测试环境。
- 理解配置校验与配置缓存。

## 核心概念

`settings.py` 中的 `Settings` 继承 `BaseSettings`，配置字段支持类型转换与约束校验。变量统一使用 `LAB_` 前缀：

| 配置字段 | 环境变量 | 默认值 |
| --- | --- | --- |
| `app_name` | `LAB_APP_NAME` | `FastAPI Learning Lab` |
| `environment` | `LAB_ENVIRONMENT` | `development` |
| `debug` | `LAB_DEBUG` | `false` |
| `items_per_page` | `LAB_ITEMS_PER_PAGE` | `10` |

`environment` 仅接受 `development`、`testing`、`production`；分页数量必须在 1 到 100 之间。

本例配置优先级从高到低为：构造函数显式传参、进程环境变量、`.env` 文件、字段默认值。`.env` 固定读取本阶段目录中的文件，使用 UTF-8；文件不存在时仍可使用默认配置。未知的 `.env` 字段会被忽略。

`get_settings()` 使用 `lru_cache` 缓存配置，`Depends(get_settings)` 将它注入接口。配置首次使用时才加载，非法配置抛出 `ValidationError`，属于服务器配置问题，而不是请求参数的 422。更改配置后需要重启服务；测试通过 `cache_clear()` 清理缓存。

`/info` 只返回本例公开字段。以后加入密码、密钥等配置时，不应直接序列化整个 `Settings`。本例 `debug` 只是用于演示布尔配置，不会开启 FastAPI 的调试模式；设置 `environment` 也不会自动切换其他配置文件。

## 运行命令

在仓库根目录准备虚拟环境并安装本阶段依赖：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
cd stage07_settings_env
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -m uvicorn main:app --reload
```

已有虚拟环境时直接激活即可。复制 `.env` 为可选步骤，修改前请检查是否已有个人配置。实际 `.env` 已由仓库 `.gitignore` 忽略，提交的是 `.env.example`。

访问 http://127.0.0.1:8000/docs 查看接口。所有运行和测试命令均在本阶段目录执行。

## 测试命令

```powershell
python -m pytest -q
```

测试自动移除本例相关环境变量、禁用本地 `.env`、清理缓存与依赖覆盖。文件读取测试使用临时 `.env`，不会修改开发配置。API 测试使用 `dependency_overrides` 注入 `testing` 配置。

验证记录（2026-10-12）：Python 3.12，`11 passed`。当前安装版本发出一条 Starlette TestClient 使用 httpx 的弃用提示。若受限沙箱无法创建系统临时目录，可在当前终端把 `TEMP` 和 `TMP` 指向项目内可写的临时目录后重试。

## 示例请求

```powershell
curl.exe http://127.0.0.1:8000/info
```

停止服务后，可以在当前 PowerShell 中覆盖配置，再重新启动：

```powershell
$env:LAB_ENVIRONMENT = "production"
$env:LAB_ITEMS_PER_PAGE = "25"
python -m uvicorn main:app
```

这些环境变量只影响当前终端及其子进程。完成示例后可以使用 `Remove-Item Env:LAB_ENVIRONMENT, Env:LAB_ITEMS_PER_PAGE` 清理。

## 预期返回

默认配置响应（200）：

```json
{"app_name":"FastAPI Learning Lab","environment":"development","debug":false,"items_per_page":10}
```

按示例设置环境变量后，`environment` 为 `production`，`items_per_page` 为 `25`。

## 常见错误

1. **找不到 `pydantic_settings`**：确认在当前虚拟环境安装了 `requirements.txt`，导入名用下划线，安装包名用连字符。
2. **修改 `.env` 后没有生效**：配置已缓存，请重启服务；同时检查环境变量是否覆盖了文件值。
3. **配置校验失败**：例如 `LAB_ITEMS_PER_PAGE=0` 或 `LAB_DEBUG=perhaps`。修正服务器配置后重启。
4. **找不到 `settings` 模块**：在 `stage07_settings_env` 内启动 `main:app`。
5. **测试误用开发配置**：覆盖原始 `get_settings` 依赖，并在测试结束后清理覆盖与缓存。

## 小练习

1. 增加有范围限制的 `request_timeout` 配置并补充测试。
2. 添加数据库连接配置，但不要在公开接口返回连接凭据。
3. 将配置依赖复用到另一个接口，并验证测试覆盖同时生效。
