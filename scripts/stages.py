"""用标准库检查阶段目录，并在独立子进程中执行各阶段测试。"""

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
STAGE_NAME = re.compile(r"stage([0-9]{2})_[a-z0-9_]+")
REQUIRED_FILES = ("main.py", "test_main.py", "README.md", "requirements.txt")
README_HEADINGS = ("本阶段学习目标", "核心概念", "运行命令", "测试命令", "示例请求", "预期返回", "常见错误", "小练习")


def discover_stages(root: Path) -> list[Path]:
    stages = sorted(path for path in root.iterdir() if path.is_dir() and path.name.startswith("stage"))
    if not stages:
        raise ValueError("No learning stages found")
    numbers = []
    for stage in stages:
        match = STAGE_NAME.fullmatch(stage.name)
        if match is None or stage.resolve().parent != root.resolve():
            raise ValueError(f"Invalid stage directory: {stage.name}")
        numbers.append(int(match[1]))
        for name in REQUIRED_FILES:
            path = stage / name
            if not path.is_file() or path.stat().st_size == 0:
                raise ValueError(f"Missing or empty file: {stage.name}/{name}")
        text = (stage / "README.md").read_text(encoding="utf-8")
        headings = {line[3:].strip() for line in text.splitlines() if line.startswith("## ")}
        missing = set(README_HEADINGS) - headings
        if missing:
            raise ValueError(f"Missing README headings in {stage.name}: {', '.join(sorted(missing))}")
    if numbers != list(range(1, len(numbers) + 1)):
        raise ValueError("Stage numbers must start at 01 and be unique and contiguous")
    return stages


def build_matrix(stages: list[Path]) -> dict:
    jobs = [{"stage": path.name, "os": "ubuntu-latest"} for path in stages]
    if any(path.name == "stage25_mini_api" for path in stages):
        jobs.append({"stage": "stage25_mini_api", "os": "windows-latest"})
    return {"include": jobs}


def run_tests(stages: list[Path], report_dir: Path) -> int:
    report_dir = report_dir.resolve()
    report_dir.mkdir(parents=True, exist_ok=True)
    # 不继承学习者终端中的业务配置，防止测试被真实密钥或数据库地址影响。
    environment = {name: value for name, value in os.environ.items() if not name.startswith("LAB_")}
    failures = []
    for stage in stages:
        print(f"\nTesting {stage.name}", flush=True)
        command = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "--tb=short",
                   f"--junitxml={report_dir / (stage.name + '.xml')}"]
        try:
            result = subprocess.run(command, cwd=stage, env=environment, timeout=300, check=False)
            failed = result.returncode != 0
        except subprocess.TimeoutExpired:
            print(f"Timed out: {stage.name}", file=sys.stderr)
            failed = True
        if failed:
            failures.append(stage.name)
    print(f"\nStages: {len(stages)}, passed: {len(stages) - len(failures)}, failed: {len(failures)}", flush=True)
    if failures:
        print("Failed stages: " + ", ".join(failures), file=sys.stderr)
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="检查学习阶段、生成 CI 矩阵或独立运行测试")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--matrix", action="store_true")
    modes.add_argument("--test", action="store_true")
    parser.add_argument("--stage", action="append", default=[], help="只测试指定目录，可重复使用")
    parser.add_argument("--report-dir", type=Path, default=ROOT / "test-results")
    args = parser.parse_args()
    if args.stage and not args.test:
        parser.error("--stage requires --test")
    try:
        stages = discover_stages(ROOT)
        if args.matrix:
            print(json.dumps(build_matrix(stages)))
        elif args.test:
            names = set(args.stage)
            unknown = names - {stage.name for stage in stages}
            if unknown:
                raise ValueError("Unknown stages: " + ", ".join(sorted(unknown)))
            return run_tests([stage for stage in stages if not names or stage.name in names], args.report_dir)
        else:
            print(f"Validated {len(stages)} stages")
    except (ValueError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
