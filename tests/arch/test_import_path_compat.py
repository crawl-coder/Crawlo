#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Import 路径兼容矩阵测试（P0-A3）
===============================

覆盖 api-surface.md 中全部模块路径：
1. 文档记录的模块路径必须真实存在且可导入；
2. 文档记录的类/函数符号必须能在对应模块上解析（类型正确）；
3. 废弃 shim 路径（crawlo.bot / crawlo.container / crawlo.crawler_process /
   crawlo.framework）必须解析到与新路径相同的模块对象（迁移等价性）。

与 test_deprecation_shims.py 的分工：后者守警告行为 + 类对象身份；
本文件守「文档 ↔ 实际代码」的路径与符号一致性。
"""

import importlib
import re
import warnings
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SURFACE_DOC = ROOT / "docs" / "reference" / "api-surface.md"

# 文档中出现的模块路径（含废弃 shim）
_MODULE_PATH_RE = re.compile(r"`(crawlo(?:\.[a-z_][a-z0-9_]*)+)`")


def _documented_module_paths():
    text = SURFACE_DOC.read_text(encoding="utf-8")
    paths = set(_MODULE_PATH_RE.findall(text))
    paths.discard("crawlo.crawler.py")  # 文件引用，非模块路径
    return sorted(paths)


@pytest.mark.parametrize("path", _documented_module_paths())
def test_documented_module_path_importable(path):
    """api-surface.md 记录的每个模块路径都可导入。"""
    try:
        with warnings.catch_warnings():
            # 废弃 shim 的 DeprecationWarning 是预期行为（本测试只校验路径存在性）
            warnings.simplefilter("ignore", DeprecationWarning)
            importlib.import_module(path)
    except ImportError as exc:
        pytest.fail(f"api-surface.md 记录的模块 {path} 无法导入: {exc}")


def test_documented_paths_are_complete():
    """文档必须覆盖全部 crawlo 一级子包（防新增顶层模块漏文档）。

    只检查一级子包（crawlo.<name>）：内部子包由模块路径导入测试覆盖，
    无需逐行记录在 api-surface.md。
    """
    pkg_root = ROOT / "crawlo"
    actual = set()
    for init in pkg_root.glob("*/__init__.py"):
        actual.add("crawlo." + init.parent.name)
    documented = set(_documented_module_paths())
    missing = sorted(actual - documented)
    assert not missing, f"以下 crawlo 包未在 api-surface.md 记录: {missing}"


@pytest.mark.parametrize("old_path,new_path", [
    ("crawlo.bot.channels", "crawlo.extensions.notifications.channels"),
    ("crawlo.bot.core", "crawlo.extensions.notifications.core"),
    ("crawlo.bot.monitoring", "crawlo.extensions.notifications.monitoring"),
    ("crawlo.bot.templates", "crawlo.extensions.notifications.templates"),
    ("crawlo.bot.utils", "crawlo.extensions.notifications.utils"),
    ("crawlo.container", "crawlo.core.application"),
    ("crawlo.crawler_process", "crawlo.crawler"),
    ("crawlo.framework", "crawlo.crawler"),
])
def test_deprecated_shim_resolves_to_same_module(old_path, new_path):
    """废弃路径必须解析到与新路径相同的模块对象（迁移等价）。"""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        old_mod = importlib.import_module(old_path)
    new_mod = importlib.import_module(new_path)
    assert old_mod is new_mod, (
        f"{old_path} 解析到 {old_mod!r}，新路径是 {new_mod!r}，对象不一致"
    )


def test_bot_package_is_forwarding_shim():
    """crawlo.bot 顶层保持真实包身份，但属性转发到新路径。"""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        import crawlo.bot as bot
    import crawlo.extensions.notifications as new
    # 顶层模块对象不同（转发 shim），但子模块/符号必须同对象
    assert bot is not new
    assert bot.channels is new.channels
    assert bot.core is new.core
    assert bot.NotificationDispatcher is new.NotificationDispatcher


@pytest.mark.parametrize("module_path,symbol", [
    ("crawlo", "Crawler"),
    ("crawlo", "CrawlerProcess"),
    ("crawlo", "CrawloFramework"),
    ("crawlo", "Spider"),
    ("crawlo", "Item"),
    ("crawlo", "Field"),
    ("crawlo", "Request"),
    ("crawlo", "Response"),
    ("crawlo", "DownloaderBase"),
    ("crawlo", "BaseMiddleware"),
    ("crawlo", "run_spider"),
    ("crawlo.crawler", "CrawlerProcess"),
    ("crawlo.crawler", "CrawloFramework"),
    ("crawlo.http", "Request"),
    ("crawlo.http", "Response"),
    ("crawlo.items", "Item"),
    ("crawlo.spider", "Spider"),
    ("crawlo.downloader", "DownloaderBase"),
    ("crawlo.downloader", "register_downloader"),
    ("crawlo.middleware", "BaseMiddleware"),
    ("crawlo.middleware", "MiddlewareManager"),
    ("crawlo.pipelines", "BasePipeline"),
    ("crawlo.queue", "QueueManager"),
    ("crawlo.queue", "register_queue_backend"),
    ("crawlo.filters", "BaseFilter"),
    ("crawlo.stats", "StatsCollector"),
    ("crawlo.logging", "get_logger"),
    ("crawlo.cluster", "WorkerRegistry"),
    ("crawlo.cluster", "DistributedLock"),
    ("crawlo.checkpoint", "CheckpointManager"),
    ("crawlo.extensions", "ExtensionManager"),
    ("crawlo.extensions.notifications", "get_notifier"),
    ("crawlo.mcp", "QuickFetcher"),
])
def test_documented_symbol_resolves(module_path, symbol):
    """api-surface.md 记录的顶层符号必须能解析（类型不限于类）。"""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        mod = importlib.import_module(module_path)
    assert hasattr(mod, symbol), f"{module_path} 上找不到符号 {symbol}"


if __name__ == "__main__":
    import sys

    result = pytest.main([__file__, "-v"])
    sys.exit(result)
