#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
架构守护测试 — 代理配置文档一致性（v1.7.4 收口）

背景：v1.7.3→v1.7.4 评估发现 docs 中存在 6 组"有文档、无实现"的代理配置键
（PROXY_ENABLED / PROXY_WHITELIST / PROXY_SWITCH_THRESHOLD / PROXY_MODE /
PROXY_API_PARAMS / BROWSER_PROXY），导致用户按文档配置后不生效。

本测试锁定两条契约：
1. docs/ 中出现的每个 ``PROXY_*`` 配置键，必须在 crawlo 源码中存在读取点或定义；
2. 已清理的幻影配置键不得在 docs/ 与项目模板中复活。
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = ROOT / "docs"
SRC_DIR = ROOT / "crawlo"
TEMPLATES_DIR = ROOT / "crawlo" / "templates"

PROXY_KEY_RE = re.compile(r"\bPROXY_[A-Z][A-Z0-9_]*\b")

# 曾经被文档宣传、但从未实现的配置键 —— 一旦重新出现立即失败
PHANTOM_KEYS = {
    "PROXY_ENABLED",
    "PROXY_WHITELIST",
    "PROXY_SWITCH_THRESHOLD",
    "PROXY_MODE",
    "PROXY_API_PARAMS",
    "BROWSER_PROXY",
}


def _scan_text(path: Path) -> str:
    """读取文本；含 ``<!-- phantom-guard: ignore -->`` 标记的行视为
    "否定式说明"（如"不存在名为 X 的配置项"），不参与键收集与复活检测。"""
    text = path.read_text(encoding="utf-8")
    return "\n".join(
        line for line in text.splitlines() if "phantom-guard: ignore" not in line
    )


def _all_source_text() -> str:
    chunks = []
    for py in sorted(SRC_DIR.rglob("*.py")):
        if "__pycache__" in py.parts:
            continue
        try:
            chunks.append(py.read_text(encoding="utf-8"))
        except UnicodeDecodeError:
            continue
    return "\n".join(chunks)


def _documented_proxy_keys() -> set:
    keys = set()
    for md in sorted(DOCS_DIR.rglob("*.md")):
        keys |= set(PROXY_KEY_RE.findall(_scan_text(md)))
    return keys


def test_documented_proxy_keys_exist_in_source():
    """docs 中出现的每个 PROXY_* 键都必须在源码中有读取点/定义。"""
    source = _all_source_text()
    documented = _documented_proxy_keys()
    assert documented, "未在 docs 中找到任何 PROXY_* 配置键，扫描逻辑可能失效"
    missing = sorted(key for key in documented if key not in source)
    assert not missing, (
        f"以下配置键在文档中宣传但源码不存在（读取点/定义）：{missing}\n"
        "要么补实现，要么删除文档描述。"
    )


def test_phantom_proxy_keys_never_reappear():
    """已清理的幻影配置键禁止在 docs 与项目模板中复活。"""
    offenders = {}
    scan_targets = list(DOCS_DIR.rglob("*.md")) + list(TEMPLATES_DIR.rglob("*.tmpl"))
    for path in scan_targets:
        hits = PHANTOM_KEYS & set(PROXY_KEY_RE.findall(_scan_text(path)))
        if hits:
            offenders[str(path.relative_to(ROOT))] = sorted(hits)
    assert not offenders, f"幻影代理配置键再次出现：{offenders}"


def test_new_ttl_key_has_default_and_reader():
    """PROXY_FAILED_TTL 必须同时具备默认值定义与读取点。"""
    source = _all_source_text()
    assert "PROXY_FAILED_TTL" in source, "缺少 PROXY_FAILED_TTL 定义/读取点"
    default_settings = (SRC_DIR / "settings" / "default_settings.py").read_text(
        encoding="utf-8"
    )
    assert re.search(r"^PROXY_FAILED_TTL\s*=\s*\d+", default_settings, re.MULTILINE), (
        "default_settings.py 缺少 PROXY_FAILED_TTL 数值默认值"
    )
