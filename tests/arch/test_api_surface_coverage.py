#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
架构守护测试 — API Surface 覆盖审计（P0-A1/A3）
=================================================

目的
----
`docs/reference/api-surface.md` 是 1.0 的 API 权威清单。本测试：

1. 遍历 crawlo 全部子包，收集公共导出（模块 __all__，缺省时取非下划线符号）；
2. 解析 api-surface.md，提取文档中记录的符号；
3. 断言每个模块的公共导出被文档覆盖 ≥ 95%（内部符号除外）。

规则
----
- 新增公共符号但没更新 api-surface.md → 本测试失败（覆盖率下降或新符号缺失）。
- 删除符号但没更新文档 → 文档存在性断言失败。
- 覆盖率阈值 95%：允许少量 internal 但未加下划线的历史符号不强制补文档。

用法
----
    python tests/arch/test_api_surface_coverage.py
    pytest tests/arch/test_api_surface_coverage.py -v
"""

import importlib
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SURFACE_DOC = ROOT / "docs" / "reference" / "api-surface.md"

# 明确标注 internal 的符号不参与覆盖率要求
INTERNAL_EXEMPT = {
    "_ack_message",
    "_make_standalone",
    "_make_distributed",
    "_make_auto",
    "_make_from_env",
    "_override_framework_initializer",
}

# 纯内部模块：符号不进入 1.0 兼容性承诺（文档第 16 节已标注 internal）。
INTERNAL_MODULES = {
    "crawlo.downloader.stealth_scripts",
    "crawlo.utils._compat",
}

# 已废弃兼容 shim：模块内容与新版模块完全一致（sys.modules 重定向），
# 覆盖情况以新模块为准，无需单独维护文档。
DEPRECATED_SHIM_MODULES = {
    "crawlo.crawler_process",
    "crawlo.framework",
    "crawlo.container",
}

# 文档中已记录、但模块无 __all__ 或导出机制特殊的符号（白名单）
DOCUMENTED_ALIASES = {
    "CrawlerState",
    "CrawlerMetrics",
    "get_logger",
    "get_framework_logger",
    "initialize_framework",
    "is_framework_ready",
}

COVERAGE_THRESHOLD = 0.95


def _iter_packages():
    """遍历 crawlo 下所有含 __init__.py 的包。"""
    pkg_root = ROOT / "crawlo"
    yield "crawlo"
    for init in sorted(pkg_root.rglob("__init__.py")):
        rel = init.relative_to(pkg_root)
        if len(rel.parts) == 1:
            continue  # 顶层已在上面处理
        parts = list(rel.parts[:-1])
        yield "crawlo." + ".".join(parts)


def _module_public_symbols(module_name):
    """返回模块的公共符号集合：优先 __all__，缺省取非下划线符号。"""
    try:
        mod = importlib.import_module(module_name)
    except Exception as exc:  # 可选依赖缺失等
        return None, f"import error: {type(exc).__name__}: {exc}"
    all_ = getattr(mod, "__all__", None)
    if all_ is not None:
        symbols = set(all_)
    else:
        symbols = {
            name for name in vars(mod) if not name.startswith("_")
        }
    return symbols, None


def _documented_symbols():
    """解析 api-surface.md，提取所有被记录的符号名。"""
    text = SURFACE_DOC.read_text(encoding="utf-8")
    symbols = set(DOCUMENTED_ALIASES)
    # 反引号包裹的标识符（函数签名、符号、类名）
    for m in re.finditer(r"`([A-Za-z_][A-Za-z0-9_]*)`", text):
        symbols.add(m.group(1))
    # 代码块中的函数签名：fetch(url, ...) / 类名（如 run_spider）
    for m in re.finditer(r"`([A-Za-z_][A-Za-z0-9_]*)\s*\(", text):
        symbols.add(m.group(1))
    return symbols


def test_surface_doc_exists():
    assert SURFACE_DOC.exists(), f"缺少 API Surface 文档: {SURFACE_DOC}"


def test_api_surface_coverage():
    """每个 crawlo 公共导出模块的公开符号被文档覆盖 ≥ 95%。"""
    documented = _documented_symbols()
    failures = []
    uncovered_total = 0
    public_total = 0

    for module_name in _iter_packages():
        if module_name in DEPRECATED_SHIM_MODULES or module_name in INTERNAL_MODULES:
            continue
        symbols, error = _module_public_symbols(module_name)
        if error:
            # 可选依赖模块允许跳过（如 crawlo.mcp 缺 mcp 包时）
            continue
        if not symbols:
            continue

        exempt = {s for s in symbols if s in INTERNAL_EXEMPT or s.startswith("_")}
        required = symbols - exempt
        if not required:
            continue
        missing = sorted(required - documented)
        coverage = len(required - set(missing)) / len(required)
        public_total += len(required)
        uncovered_total += len(missing)
        if coverage < COVERAGE_THRESHOLD or missing:
            failures.append(
                f"{module_name}: {coverage:.1%} 覆盖（{len(missing)}/{len(required)} 未记录）\n"
                f"    缺失符号: {missing}"
            )

    assert not failures, (
        "api-surface.md 覆盖率不足。新增/变更公共 API 时必须同步更新 "
        "docs/reference/api-surface.md。\n" + "\n".join(failures)
    )
    assert public_total > 0, "未收集到任何公共符号，审计失败"


def test_documented_symbols_exist():
    """文档记录的模块路径真实存在（防文档漂移）。"""
    import warnings

    text = SURFACE_DOC.read_text(encoding="utf-8")
    # 形如 crawlo.xxx.yyy 的模块路径（排除文档中形如 `crawlo/crawler.py` 的文件引用）
    paths = set(
        re.findall(r"`(crawlo(?:\.[a-z_][a-z0-9_]*)+)`", text)
    ) - {"crawlo.crawler.py"}
    missing = []
    for path in sorted(paths):
        try:
            with warnings.catch_warnings():
                # 废弃 shim 路径（container/crawler_process/framework）
                # 本身会发 DeprecationWarning，这里是路径存在性校验，属预期。
                warnings.simplefilter("ignore", DeprecationWarning)
                importlib.import_module(path)
        except Exception:
            missing.append(path)
    assert not missing, f"api-surface.md 引用了不存在的模块: {missing}"


if __name__ == "__main__":
    import sys

    result = pytest.main([__file__, "-v"])
    sys.exit(result)
