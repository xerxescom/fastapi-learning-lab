# Stage 14：文件上传与静态文件

## 本阶段学习目标

- 用 `UploadFile` 接收 `multipart/form-data` 文件，而不是 JSON 请求体。
- 校验扩展名、Content-Type、实际字节数与文本内容。
- 使用随机文件名保存文件，通过 `StaticFiles` 提供访问 URL。
- 测试上传、下载、边界限制、路径安全和失败清理。

## 核心概念

### UploadFile 与表单字段

`UploadFile` 提供文件名、Content-Type 和文件对象；普通 `Form` 字段只是字符串等表单值。接收 multipart 文件需要安装 `python-multipart`。不要手动给 curl 请求设置不含 boundary 的 `Content-Type`，让客户端生成。

相比直接声明 `bytes`，`UploadFile` 使用可转存磁盘的临时文件。异步路由可以 `await file.read()`；本阶段使用同步 `def` 路由，通过 `file.file.read()` 分块读取，磁盘操作在线程池执行。路由在 `finally` 中关闭上传文件。

### 上传契约

`POST /uploads` 接收必填字段 `file`，一次保存一个文件，成功返回 201。

| 项目 | 约定 |
| --- | --- |
| 文本 | `.txt` + `text/plain`，UTF-8 编码 |
| JSON | `.json` + `application/json`，UTF-8 且能够解析 |
| 大小 | 1 到 1,048,576 字节（1 MiB），含上下边界 |
| 文件名 | 最多 200 个字符，不允许路径分隔符、冒号和控制字符 |
| 空文件、非法编码、无效 JSON | 400 |
| 不支持的扩展名或 MIME 不匹配 | 415 |
| 超过大小限制 | 413 |
| 缺少文件或把字段当普通文本提交 | 422 |

扩展名不区分大小写，Content-Type 可带 `charset` 等参数。JSON 可以是对象、数组或合法标量；拒绝 `NaN`、`Infinity` 等非标准常量。文本中也拒绝 NUL 字符。这里没有图片上传、文件预览或通用恶意文件检测。

MIME 和文件名由客户端提供，不能独立证明文件类型。因此还要检查实际内容。本例最多从上传文件读取上限加一个字节，避免应用校验时无界读取；校验后才写入最终文件。

**重要边界：** FastAPI 在进入路由前已经解析 multipart。本阶段的 1 MiB 限制是单个文件的业务限制，不是整个 HTTP 请求的流式接入限制，也不阻止解析器处理额外字段或文件。生产环境还需在反向代理或接入层限制请求体、上传数量、连接时长和并发，并设置用户配额。

### 存储与静态访问

`main.py` 提供应用工厂和接口，`app/storage.py` 负责校验、保存及静态响应设置。默认目录固定在本阶段下，不依赖启动时的工作目录：

```text
uploads/
  临时随机名.part       # 不在静态挂载目录中
  public/
    UUID.txt            # 写完后才原子移动到此处
```

客户端原始文件名仅作为响应元数据，不直接参与存储路径。UUID 文件名避免普通同名上传互相覆盖；临时文件写完关闭后再发布，失败会清理临时文件。目录已被 Git 忽略，不要提交用户文件。

`/files` 挂载 `StaticFiles`，文件以附件下载，并设置 `X-Content-Type-Options: nosniff`。支持 GET、HEAD 和缓存条件请求，不提供目录列表。挂载的子应用不会作为普通接口列在 OpenAPI 中。

**目录内文件是公开的，随机 URL 不等于授权。** 不要上传密码、Token 或其他隐私资料。私有文件应经过鉴权下载接口，或使用对象存储的短期签名 URL；用户上传内容也宜由独立域名提供。禁止其他非可信进程往公开目录写入文件或符号链接。

生产扩展方向包括：对象存储、HTTPS、身份与访问控制、容量配额、病毒扫描、过期清理、备份与审计。多 worker/多机器部署不能假设本地磁盘天然共享。

参考：[FastAPI 文件上传](https://fastapi.tiangolo.com/tutorial/request-files/)、[静态文件挂载](https://fastapi.tiangolo.com/tutorial/static-files/)。

## 运行命令

在仓库根目录激活已有环境，再进入本阶段：

```powershell
.\.venv\Scripts\Activate.ps1
cd stage14_upload_static_files
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload
```

不需要数据库和初始化脚本。应用创建时自动准备 `uploads/public`。访问 `http://127.0.0.1:8000/docs`，选择 `/uploads`，可以直接选文件上传。

返回的绝对 URL 来自请求地址。反向代理部署时需要正确配置可信代理头及外部地址，不能无条件信任任意客户端提供的转发头。

## 测试命令

在本阶段目录运行：

```powershell
python -m pytest -q
```

每个测试使用 `tmp_path` 创建独立存储目录，再传入 `create_app(storage_dir)`，不读写默认上传目录。覆盖文本/JSON、中文名称、同名文件、类型伪装、非法内容、大小边界、路径穿越、静态访问、缓存、OpenAPI 和写盘失败后的清理。

验证记录（2026-10-12）：`43 passed`；有一条 Starlette TestClient 使用 httpx 的依赖弃用提示，不影响测试通过。

若 Windows 默认临时目录无写入权限，可改用可写目录：

```powershell
$env:TEMP = Join-Path (Resolve-Path ..\.venv).Path 'pytest-tmp'
New-Item -ItemType Directory -Force -Path $env:TEMP | Out-Null
$env:TMP = $env:TEMP
python -m pytest -q
```

## 示例请求

在本阶段目录开另一个 PowerShell 窗口，用仓库内的样例文件：

```powershell
curl.exe -i -F "file=@examples/hello.txt;type=text/plain" http://127.0.0.1:8000/uploads
curl.exe -i -F "file=@examples/config.json;type=application/json" http://127.0.0.1:8000/uploads
```

PowerShell 可以直接取返回的 URL 并下载：

```powershell
$result = curl.exe -s -F "file=@examples/hello.txt;type=text/plain" http://127.0.0.1:8000/uploads | ConvertFrom-Json
curl.exe -i $result.url
```

故意发送错误类型或缺少文件：

```powershell
curl.exe -i -F "file=@examples/hello.txt;type=application/json" http://127.0.0.1:8000/uploads
curl.exe -i -X POST http://127.0.0.1:8000/uploads
```

## 预期返回

上传文本成功时 HTTP 201，随机文件名每次不同；大小按实际字节数计算，包括文件换行。以下为 LF 换行的样例，若 Git 转成 CRLF，大小会增加一字节：

```json
{
  "filename": "hello.txt",
  "stored_name": "5d3112b6a9554f40b8b02637f140b1ef.txt",
  "content_type": "text/plain",
  "size": 14,
  "url": "http://127.0.0.1:8000/files/5d3112b6a9554f40b8b02637f140b1ef.txt"
}
```

GET 实际返回的 `url` 得到 200，内容为 `Hello FastAPI!` 和末尾换行，响应头包含 `Content-Disposition: attachment`、`X-Content-Type-Options: nosniff`。

类型不匹配返回 HTTP 415：

```json
{"detail": "Only .txt/text/plain and .json/application/json are allowed"}
```

超限返回 HTTP 413 和 `{"detail": "File exceeds 1 MiB"}`。失败校验不会保存文件；访问不存在的文件返回 404。

## 常见错误

- 提示缺少 multipart：安装本阶段 `requirements.txt`，注意包名是 `python-multipart`。
- 上传返回 422：使用 multipart 的 `file` 字段，不是 JSON，也不是普通字符串表单字段。
- `.txt` 返回 415：客户端可能推断为 `application/octet-stream`，显式指定 `type=text/plain`。
- 修改后缀仍然失败：扩展名和 MIME 只是第一步，内容必须符合 UTF-8 或 JSON 要求。
- 中文文本大小不是字符数：限制针对编码后的字节数。
- Windows 盘符路径没有原样出现在应用中：multipart 解析器可能先剥离路径。本例不依赖这种清洗，存储层仍拒绝路径字符并使用服务端随机名。
- 静态目录返回 404：只支持具体文件访问，不启用目录列表。
- 看到 500：检查目录权限、磁盘空间及服务端日志，不要向客户端暴露本地路径和异常细节。

## 小练习

1. 增加批量上传，先定义数量上限以及部分失败时的返回与清理规则。
2. 实现带用户权限检查的下载接口，对比公开 `StaticFiles` 挂载的访问模型。
3. 用合适的图片解析库验证真实图片，而不是只检查 `.png` 和 Content-Type。
4. 抽出对象存储适配器，让 API 返回短期有效的下载 URL。
