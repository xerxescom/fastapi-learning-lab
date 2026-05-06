# 阶段 01：FastAPI 入门与基础路由

## 本阶段学习目标

- 能创建一个最小可运行的 FastAPI 应用。
- 能定义并访问基础 GET 路由。
- 能使用自动文档页面快速验证接口。
- 能使用 pytest 对接口进行基础测试。

## 核心概念

- **FastAPI 应用实例**：通过 `app = FastAPI(...)` 创建。
- **路径操作（Path Operation）**：用 `@app.get(...)` 等装饰器声明路由。
- **自动文档**：启动后访问 `/docs`（Swagger UI）和 `/redoc`。
- **健康检查**：`/health` 常用于服务存活检测。

## 运行命令

在当前目录（`stage01_hello_fastapi`）执行：

```bash
uvicorn main:app --reload
```

启动后访问：

- http://127.0.0.1:8000/
- http://127.0.0.1:8000/health
- http://127.0.0.1:8000/docs

## 测试命令

```bash
pytest -q
```

## 示例请求

### 1）根路由

```bash
curl http://127.0.0.1:8000/
```

### 2）健康检查

```bash
curl http://127.0.0.1:8000/health
```

## 预期返回

### 1）`GET /`

```json
{"message": "你好，FastAPI！"}
```

### 2）`GET /health`

```json
{"status": "ok"}
```

## 常见错误

1. **`ModuleNotFoundError: No module named 'fastapi'`**  
   未安装依赖，请先执行：`pip install fastapi uvicorn pytest httpx`。

2. **`Address already in use`**  
   8000 端口被占用，可改为：`uvicorn main:app --reload --port 8001`。

3. **导入错误（`from main import app` 失败）**  
   请确认你在 `stage01_hello_fastapi` 目录中运行命令。

## 小练习

1. 新增路由 `GET /hello/{name}`，返回 `{"message": "你好, {name}"}`。
2. 给应用补充 `summary` 字段，并观察 `/docs` 页面变化。
3. 为新路由编写一个测试用例，验证状态码和 JSON 返回。
