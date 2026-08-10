#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
命令行入口：crawlo release [--dry-run]

发布纪律检查（P0-A4）：
    1. 版本号：crawlo/__version__.py 必须是合法 semver（MAJOR.MINOR.PATCH）；
    2. CHANGELOG.md：必须存在，且包含当前版本的条目（格式 ## [x.y.z] - YYYY-MM-DD）；
    3. 发布说明：docs/releases/v{x.y.z}.md 必须存在；
    4. Git tag：若已打 tag，tag 必须与版本号一致；
    5. 测试（非 --dry-run）：全量测试套件必须通过。

用法：
    crawlo release --dry-run      # 只检查发布就绪度，不跑测试（CI 用）
    crawlo release                # 检查 + 跑全量测试
    python -m crawlo.commands.release --dry-run
"""

import re
import subprocess  # nosec B404  # 固定命令数组 + shell=False，无注入面
import sys
from pathlib import Path

from crawlo.logging import get_logger

logger = get_logger(__name__)

ROOT = Path(__file__).resolve().parents[2]
VERSION_FILE = ROOT / "crawlo" / "__version__.py"
CHANGELOG_FILE = ROOT / "CHANGELOG.md"
RELEASES_DIR = ROOT / "docs" / "releases"

SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")
CHANGELOG_ENTRY_RE = re.compile(
    r"^## \[(\d+\.\d+\.\d+)\] - \d{4}-\d{2}-\d{2}",
    re.MULTILINE,
)


def get_current_version() -> str:
    """读取 crawlo/__version__.py 中的版本号。"""
    text = VERSION_FILE.read_text(encoding="utf-8")
    match = re.search(r"__version__\s*=\s*['\"]([^'\"]+)['\"]", text)
    if not match:
        raise RuntimeError(f"无法从 {VERSION_FILE} 解析版本号")
    return match.group(1)


def check_release_readiness(run_tests: bool = False) -> list:
    """执行发布就绪检查，返回失败信息列表（空列表 = 全部通过）。"""
    failures = []

    # 1. semver
    version = get_current_version()
    if not SEMVER_RE.match(version):
        failures.append(
            f"版本号 {version!r} 不是合法 semver（期望 MAJOR.MINOR.PATCH）"
        )

    # 2. CHANGELOG 存在 + 包含当前版本条目
    if not CHANGELOG_FILE.exists():
        failures.append(f"缺少 CHANGELOG.md（{CHANGELOG_FILE}）")
    else:
        text = CHANGELOG_FILE.read_text(encoding="utf-8")
        entries = CHANGELOG_ENTRY_RE.findall(text)
        if version not in entries:
            failures.append(
                f"CHANGELOG.md 缺少当前版本条目 [ {version} ] "
                f"（期望格式: ## [{version}] - YYYY-MM-DD）"
            )
        # 不允许同一版本出现两次
        duplicates = {v for v in entries if entries.count(v) > 1}
        if duplicates:
            failures.append(f"CHANGELOG.md 版本条目重复: {sorted(duplicates)}")

    # 3. 发布说明
    release_doc = RELEASES_DIR / f"v{version}.md"
    if not release_doc.exists():
        failures.append(f"缺少发布说明 docs/releases/v{version}.md")

    # 4. Git tag 一致性（仅当存在 tag 时校验）
    try:
        result = subprocess.run(  # nosec B607, B603
            ["git", "describe", "--tags", "--exact-match", "--abbrev=0"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            tag = result.stdout.strip()
            expected = f"v{version}"
            if tag != expected:
                failures.append(
                    f"当前 HEAD 的 git tag {tag!r} 与版本号 {expected!r} 不一致"
                )
    except (subprocess.SubprocessError, FileNotFoundError):
        # 非 git 环境（如 sdist 内）跳过 tag 检查
        logger.debug("git tag 检查跳过（非 git 环境）")

    # 5. 全量测试（仅非 --dry-run）
    if run_tests and not failures:
        logger.info("运行全量测试套件（发布前验证）...")
        result = subprocess.run(  # nosec B607, B603
            [sys.executable, "-m", "pytest", "tests/", "-q"],
            cwd=ROOT,
            timeout=1800,
        )
        if result.returncode != 0:
            failures.append("全量测试未通过")

    return failures


def main(args):
    dry_run = "--dry-run" in args

    failures = check_release_readiness(run_tests=not dry_run)

    if not failures:
        version = get_current_version()
        print(f"OK: Crawlo {version} 发布就绪"
              + ("（dry-run，未跑测试）" if dry_run else "（全量测试已通过）"))
        return 0

    print(f"发布就绪检查失败（{len(failures)} 项）：", file=sys.stderr)
    for failure in failures:
        print(f"  - {failure}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
