# Stage 24：部署入门

## 本阶段学习目标

- 将独立 FastAPI 应用作为 ASGI 服务运行，理解监听地址与端口映射。
- 用环境变量提供生产配置，并在错误配置下拒绝启动。
- 编写非 root、单进程的 Docker 镜像与健康探针。
- 了解 Uvicorn 参数、Gunicorn Worker、反向代理和优雅关闭的边界。

## 核心概念

### 应用配置不等于服务器配置

`Settings` 读取 `LAB_` 前缀环境变量：

| 环境变量 | 默认值 | 用途 |
| --- | --- | --- |
| LAB_APP_NAME | FastAPI Deployment Lab | 应用名称 |
| LAB_ENVIRONMENT | development | development/testing/production |
| LAB_RELEASE_VERSION | 1.0.0 | 发布标识 |
| LAB_DEBUG | false | FastAPI 调试模式 |
| LAB_DOCS_ENABLED | false | 同时控制 docs、redoc、openapi.json |
| LAB_ALLOWED_HOSTS | `["127.0.0.1","localhost"]` | Host 白名单，使用 JSON 数组 |

生产环境禁止 debug=True 和完全开放的 `*` Host。Host 配置填写域名或 IPv4 地址，不含协议、端口、路径；可以使用 `*.example.com` 表示子域名。本例不提供 IPv6 Host 配置。

本阶段默认不自动读取 `.env`，避免部署位置不同而读取意外文件。`.env.example` 是可直接交给 Docker `--env-file` 的非敏感配置模板；本地 Uvicorn 可以使用 `--env-file .env.example` 显式加载它。真实环境使用受控的环境变量或密钥服务，不把密码放进镜像。

`--host`、`--port`、`--workers` 是服务器参数，不由 LAB 配置字段控制。`0.0.0.0` 表示监听全部 IPv4 接口，不是浏览器访问地址。本地访问仍使用 `127.0.0.1` 或实际域名。

`/info` 只返回名称、环境和发布版本，不返回完整配置对象。关闭文档不是鉴权；本例没有用户系统，接口仍能直接调用。

### Host、代理与 HTTPS

`TrustedHostMiddleware` 拒绝未允许的 Host，保护范围包括健康检查。容器探针访问 `127.0.0.1`，所以运行配置必须保留这个 Host。实际域名也要明确加入白名单；白名单不是 CORS，也不是用户认证。

Docker 启动命令默认使用 `--no-proxy-headers`，不信任客户端随意发送的转发头。如果以后接入可信反向代理，应将 Uvicorn 调整为 `--proxy-headers --forwarded-allow-ips <可信代理IP>`，并在网络层阻止外部绕过代理直连。不要在开放直连端口上盲目信任 `*`。Host 白名单仍需要单独维护。

通常由反向代理或托管平台终止 HTTPS；本例仅提供本地 HTTP，没有配置证书、域名或真实公网部署。代理是否剥离路径前缀决定是否需要 `--root-path`，它不能替代代理路由规则。[Uvicorn 设置文档](https://uvicorn.dev/settings/)

### 进程与生命周期

本例使用 lifespan 设置就绪状态，只有进入生命周期后 `/health/ready` 才返回 200；退出后恢复为未就绪。它只表示应用已经启动，没有检查数据库或其他外部依赖。真实探针设计可回顾 Stage 22 和 Stage 23。

Uvicorn 原生支持多个 worker，Windows 也可以使用；`--reload` 与 `--workers` 不能同时使用。每个 worker 都有独立的内存和生命周期。[Uvicorn 部署文档](https://uvicorn.dev/deployment/)

Docker 示例每容器运行一个 Uvicorn 进程。扩容、重启与流量分配由部署平台另行负责；单机也可以按测量结果使用多个 worker。不要同时无规划地增加 worker 数量和容器副本，尤其要考虑每个进程的内存与连接池开销。

Dockerfile 使用 exec 形式的 CMD，让服务进程直接接收停止信号，而不是被 shell 包裹。容器停止等待时间应大于应用优雅关闭预算；本例分别使用 30 秒和 20 秒。[FastAPI Docker 文档](https://fastapi.tiangolo.com/deployment/docker/)

## 运行命令

### 本地开发与测试准备

在仓库根目录执行（Windows PowerShell，已有 `.venv`）：

```powershell
.\.venv\Scripts\Activate.ps1
cd stage24_deployment
python -m pip install -r requirements.txt
$env:LAB_ENVIRONMENT = 'development'
$env:LAB_DOCS_ENABLED = 'true'
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

服务地址为 `http://127.0.0.1:8000`，开发文档为 `/docs`。没有数据库，无需初始化数据。

### 本地模拟生产

停止开发服务器后，在相同 PowerShell 窗口执行：

```powershell
$env:LAB_ENVIRONMENT = 'production'
$env:LAB_DEBUG = 'false'
$env:LAB_DOCS_ENABLED = 'false'
$env:LAB_RELEASE_VERSION = '1.0.0'
$env:LAB_ALLOWED_HOSTS = '["127.0.0.1","localhost"]'
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --workers 2 --no-proxy-headers --timeout-graceful-shutdown 20
```

这是本地生产参数演示，不等于已完成公网部署。也可在新的干净终端中用 `--env-file .env.example` 显式加载示例；已有系统环境变量会优先于文件，所以先前设置的变量仍可能覆盖示例值。

| 参数 | 含义与注意点 |
| --- | --- |
| `--host` / `--port` | 监听地址与端口；容器中需要 0.0.0.0 才能从映射端口访问 |
| `--reload` | 开发重载，不用于生产 |
| `--workers` | 多进程数量，与 reload 互斥，按负载与资源预算调整 |
| `--timeout-keep-alive` | 空闲持久连接等待时间，不是单次请求超时 |
| `--timeout-graceful-shutdown` | 关闭时等待正在执行任务的预算 |
| `--limit-concurrency` | 限制并发连接/任务，超限可能返回 503，需压测后设定 |
| `--log-level` / `--no-access-log` | 日志配置；原始 URL、查询串和异常日志仍需安全审查 |

### Docker

确保 Docker Desktop 的 Linux 引擎运行，在本阶段目录执行：

```powershell
docker build -t fastapi-lab-stage24:local .
docker run --detach --name fastapi-lab-stage24 --publish 127.0.0.1:8000:8000 --env-file .env.example --read-only --tmpfs /tmp:rw,noexec,nosuid,size=16m --cap-drop ALL --security-opt no-new-privileges fastapi-lab-stage24:local
docker inspect --format '{{.State.Health.Status}}' fastapi-lab-stage24
docker logs fastapi-lab-stage24
```

浏览器或客户端访问宿主机 `http://127.0.0.1:8000`，不是容器 IP。`EXPOSE 8000` 只是镜像元数据，真正发布端口的是 `--publish`。绑定宿主机回环地址是为了避免学习示例意外对外开放。

镜像只安装运行依赖，测试依赖保留在 `requirements.txt`。构建先复制依赖清单利用缓存，再复制源码；使用 UID 10001 非 root 用户，`.dockerignore` 采用允许列表，排除本地环境与缓存。Python 不写 bytecode，示例无需磁盘持久化。

容器内 `python -m app.healthcheck` 使用标准库访问回环地址上的 readiness，设置 2 秒超时，不使用环境代理；失败以非零状态退出。HEALTHCHECK 只标记健康状态，普通 Docker 不会仅因 unhealthy 自动重启容器。生产平台应另行配置重启策略和流量摘除规则。

测试后清理本例容器（仅针对上面明确命名的容器）：

```powershell
docker stop --time 30 fastapi-lab-stage24
docker rm fastapi-lab-stage24
```

端口 8000 被占用时，可以将宿主机映射改为 `127.0.0.1:8001:8000`；容器内部仍使用 8000，健康探针不需要改变。容器名被占用时先确认旧容器用途，不要直接删除其他人的服务。

Dockerfile 的 Python 标签和依赖范围用于教学，不是严格的可复现锁定；发布时应测试并锁定依赖版本与基础镜像摘要、做漏洞扫描，并建立定期更新流程。

### Gunicorn + Uvicorn Worker（Linux / WSL）

在 Linux 环境中创建并激活该环境自己的 Python 虚拟环境，再进入本阶段目录：

```bash
python -m pip install -r requirements-gunicorn.txt
export LAB_ENVIRONMENT=production
export LAB_DEBUG=false
export LAB_DOCS_ENABLED=false
export LAB_ALLOWED_HOSTS='["127.0.0.1","localhost"]'
gunicorn main:app --bind 127.0.0.1:8000 --workers 2 --worker-class uvicorn_worker.UvicornWorker --graceful-timeout 20 --timeout 60 --forwarded-allow-ips 127.0.0.1
```

Gunicorn 管理进程，ASGI worker 运行 FastAPI；不要使用 Gunicorn 默认的 WSGI worker。这里使用独立的 `uvicorn-worker` 包，旧的 `uvicorn.workers` 已被标记为弃用。[Uvicorn 部署说明](https://uvicorn.dev/deployment/)、[uvicorn-worker 官方项目](https://github.com/Kludex/uvicorn-worker)

Gunicorn 不作为原生 Windows 运行路径，因此可选依赖使用平台标记，Windows 安装该文件会跳过 Gunicorn 和 worker。在 Windows 请使用 Uvicorn；WSL 内不要复用 Windows 的 `.venv`。上例的 60 秒是 Gunicorn worker 静默超时，不是严格的业务请求总超时。

## 测试命令

在阶段目录执行：

```powershell
python -m pytest -q -p no:cacheprovider
```

验证结果：`29 passed`；当前环境有一条 Starlette TestClient 使用 httpx 的依赖弃用提示，不影响测试通过。

测试覆盖应用入口、环境变量与显式配置文件、公开字段白名单、非法生产配置、文档开关、Host 拒绝、生命周期就绪状态及健康探针错误。Dockerfile 只做静态关键约定检查，不能替代真实镜像构建。

本次环境验证限制：Docker CLI 可用，但 Docker Desktop Linux 引擎未运行，未完成镜像构建与容器运行；原生 Windows 也未执行 Gunicorn。真实 Uvicorn HTTP 验证独立进行，不能将其算作 Docker 或 Linux Gunicorn 验证。

## 示例请求

启动本地生产示例或容器后执行：

```powershell
Invoke-RestMethod 'http://127.0.0.1:8000/health/live'
Invoke-RestMethod 'http://127.0.0.1:8000/health/ready'
Invoke-RestMethod 'http://127.0.0.1:8000/info'
curl.exe -i http://127.0.0.1:8000/docs
curl.exe -i -H 'Host: untrusted.example' http://127.0.0.1:8000/info
```

## 预期返回

两个健康接口返回 200，分别为 `{"status":"alive"}` 与 `{"status":"ready"}`。

生产配置的 `/info` 返回 200：

```json
{"app_name":"FastAPI Deployment Lab","environment":"production","release_version":"1.0.0"}
```

文档开关关闭时 `/docs`、`/redoc`、`/openapi.json` 返回 404。未允许的 Host 返回 400；生产配置开启 debug 或使用完全开放的 Host 会在应用构造时抛出配置错误，服务不应启动成功。

## 常见错误

- Docker 命令存在但无法连接引擎：先启动 Docker Desktop Linux 引擎，仅安装 CLI 不足以构建镜像。
- 容器启动却无法访问：检查容器监听是否为 0.0.0.0、端口是否发布，以及宿主机端口是否被占用。
- 访问返回 400：检查实际 Host 是否在白名单，填写域名而不是完整 URL。
- readiness 在容器内失败：确认允许 127.0.0.1，探针在容器内部访问的不是宿主机映射端口。
- 设置了 LAB_PORT 仍未改变端口：应用配置没有这个字段，使用服务器 `--port` 参数。
- 生产环境看到调试页面：本例直接拒绝 debug=True，但仍需确认实际部署代码与配置，不要仅依赖环境名称。
- 认为关闭文档就安全了：业务鉴权、HTTPS、网络隔离与访问日志审查都需要另行完成。
- 把 migrations 放进每个 worker 启动：多进程可能竞争执行迁移，应设计部署前的单独迁移步骤。

## 小练习

1. 启动 Docker 引擎后构建镜像，确认以非 root 运行，并观察 health 状态由 starting 变为 healthy。
2. 比较单 worker 与多 worker 的吞吐、内存和优雅关闭行为，不用固定公式猜测最佳进程数。
3. 接入本地反向代理，只信任该代理地址，分别测试可信与伪造转发头。
4. 将测试、镜像构建、漏洞扫描与发布版本注入串成一个最小 CI 流程。
