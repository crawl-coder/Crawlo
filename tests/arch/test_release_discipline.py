#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
发布纪律守护测试（P0-A4）
========================

守护 crawlo release --dry-run 的发布就绪检查逻辑：
1. 当前状态（版本 + CHANGELOG + 发布说明齐全）必须通过检查；
2. 版本号缺失 / CHANGELOG 缺失 / 版本不匹配 / 发布说明缺失必须被拦截；
3. crawlo release 命令已注册。
"""

from pathlib import Path

from crawlo.commands import get_commands
from crawlo.commands.release import (
    CHANGELOG_FILE,
    RELEASES_DIR,
    VERSION_FILE,
    check_release_readiness,
    get_current_version,
)

ROOT = Path(__file__).resolve().parents[2]


def test_current_release_is_ready():
    """当前版本必须通过发布就绪检查（无失败项）。"""
    assert VERSION_FILE.exists(), "缺少 crawlo/__version__.py"
    assert CHANGELOG_FILE.exists(), "缺少 CHANGELOG.md"
    failures = check_release_readiness()
    assert not failures, (
        "当前版本发布就绪检查失败，请补齐:\n" + "\n".join(failures)
    )


def test_release_command_registered():
    """crawlo release 命令必须已注册。"""
    assert "release" in get_commands()


def test_changelog_has_current_version_entry():
    """CHANGELOG.md 必须包含当前版本条目（格式 ## [x.y.z] - YYYY-MM-DD）。"""
    import re

    version = get_current_version()
    text = CHANGELOG_FILE.read_text(encoding="utf-8")
    pattern = re.compile(
        rf"^## \[{re.escape(version)}\] - \d{{4}}-\d{{2}}-\d{{2}}",
        re.MULTILINE,
    )
    assert pattern.search(text), (
        f"CHANGELOG.md 缺少当前版本 {version} 的条目"
    )


def test_release_doc_exists_for_current_version():
    """docs/releases/v{x.y.z}.md 必须存在（发布说明）。"""
    version = get_current_version()
    doc = RELEASES_DIR / f"v{version}.md"
    assert doc.exists(), f"缺少发布说明 {doc}"


def test_missing_changelog_entry_is_detected(monkeypatch, tmp_path):
    """版本号在 CHANGELOG 中无条目时必须被拦截。"""
    import crawlo.commands.release as release_mod

    vf = tmp_path / "__version__.py"
    vf.write_text("__version__ = '9.9.9'\n", encoding="utf-8")
    cf = tmp_path / "CHANGELOG.md"
    cf.write_text("## [Unreleased]\n\nnothing\n", encoding="utf-8")
    rd = tmp_path / "releases"
    rd.mkdir()

    monkeypatch.setattr(release_mod, "VERSION_FILE", vf)
    monkeypatch.setattr(release_mod, "CHANGELOG_FILE", cf)
    monkeypatch.setattr(release_mod, "RELEASES_DIR", rd)

    failures = check_release_readiness()
    assert any("CHANGELOG.md 缺少当前版本条目" in f for f in failures), failures
    assert any("v9.9.9" in f for f in failures), failures
