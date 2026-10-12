# 自动化测试与协作检查

## 检查范围

默认分支为 `Aivor`。`.github/workflows/tests.yml` 在向该分支推送、提交目标为该分支的 PR，或手动触发时运行。

- 使用 Python 3.12，检查阶段编号连续、必需文件非空和 README 八个固定章节。
- 自动发现阶段目录，每个阶段在独立 Linux 作业中安装自己的依赖、执行 `pip check` 和 pytest。
- Stage 25 额外运行 Windows 测试。当前共有 25 个 Linux 测试作业、1 个 Windows 测试作业。
- 测试失败不停止其他阶段；所有结果由稳定名称的 `CI Gate` 汇总。结构检查失败或测试跳过也不会视为通过。
- 各作业上传 JUnit XML 报告，保留 7 天。安装依赖失败时可能没有报告，应查看作业日志。

新增阶段时保持 `stageNN_topic` 命名和连续编号，并提供 `main.py`、`test_main.py`、`README.md`、`requirements.txt`，无需手工修改测试矩阵。

## 本地运行

先激活 Python 3.12 环境，在仓库根目录执行结构与工具测试：

```bash
python scripts/stages.py
python -m unittest discover -s tests_ci -v
```

只检查综合项目：

```bash
python -m pip install -r stage25_mini_api/requirements.txt
python scripts/stages.py --test --stage stage25_mini_api
```

可以重复传入 `--stage` 测试多个阶段。目录名拼错会直接报错，不会悄悄跳过。

全量运行前需要安装所有阶段的依赖。PowerShell 示例：

```powershell
Get-ChildItem -Directory stage* | Sort-Object Name | ForEach-Object {
    python -m pip install -r (Join-Path $_.FullName 'requirements.txt')
    if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed: $($_.Name)" }
}
python scripts/stages.py --test
```

本地脚本不自动安装依赖。共享环境便于学习，但不等同于 CI 的干净环境隔离；发生依赖冲突时可为单个阶段单独创建虚拟环境。脚本为每个阶段启动新进程、以阶段目录为工作目录运行测试，避免 `main`、`app` 等同名模块冲突。它还会移除继承的 `LAB_*` 业务环境变量，避免终端中的真实配置影响测试。

JUnit 报告默认写入被 Git 忽略的 `test-results/`，可用 `--report-dir` 指定其他位置。单阶段超时为 300 秒，失败后继续其他阶段，最终以非零退出码报告失败。

受限 Windows 环境如无法写入系统临时目录，可在已有虚拟环境下设置一个有权限的目录：

```powershell
$tempDir = Join-Path (Resolve-Path .venv).Path 'pytest-tmp'
New-Item -ItemType Directory -Force -Path $tempDir | Out-Null
$env:TEMP = $tempDir
$env:TMP = $tempDir
python scripts/stages.py --test
```

## PR 检查

1. 从 `Aivor` 创建工作分支，修改代码与对应文档。
2. 本地运行相关阶段测试及结构检查，提交并推送工作分支。
3. 创建目标为 `Aivor` 的 PR，填写验证结果与尚未验证的范围。
4. 检查 Files changed 和 Actions 日志，等 `CI Gate` 通过后再决定合并。

需要强制合并前检查时，可由仓库管理员在分支保护规则中要求 `CI Gate`。本项目的工作流不会自动改变仓库保护设置，也不会自动合并 PR。

## 安全与边界

Actions 只有仓库读取权限，checkout 不保留 Git 凭据；官方 Actions 固定完整 commit SHA。Dependabot 每周检查 Actions 更新，更新仍需测试和人工审阅。

测试不需要真实生产密钥或外部数据库。不要把 `.env`、数据库文件、访问令牌或敏感日志提交到仓库，也不要把敏感信息写入测试报告。

当前 CI 不构建 Docker 镜像、不启动 Gunicorn、不执行公网部署，也不代表已完成安全审计、压力测试或所有 Python 版本兼容验证。依赖使用版本范围而非锁文件；本地成功不能替代 CI 的全新依赖安装结果。Stage 05 的旧生命周期写法和部分 TestClient 依赖可能有弃用提示，警告与测试失败应分别判断。
