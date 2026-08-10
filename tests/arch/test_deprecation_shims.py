#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Deprecation shim 契约测试（P0-A2）
=================================

覆盖 DEPRECATION.md「进行中」的全部条目：
1. 旧路径导入会发出 DeprecationWarning（仅 shim 自身；其余测试由全局
   ``filterwarnings = error::DeprecationWarning`` 强制不得出现未预期警告）；
2. 旧路径返回的对象与新路径**同一对象**（sys.modules 重定向 / meta-path
   finder 保证，混用新旧路径时 isinstance / is 不得失效）；
3. 顶层推荐路径（crawlo.* / crawlo.crawler / crawlo.core.application）不受影响。
"""

import importlib
import subprocess
import sys
import textwrap
import warnings
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

# 本文件测试对象就是废弃 shim，旧路径导入的 DeprecationWarning 为预期；
# 警告行为本身由子进程隔离断言（_import_old_path）。
pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")


def _import_old_path(path):
    """在子进程中导入旧路径并断言：成功 + 触发 DeprecationWarning。"""
    code = textwrap.dedent(f"""
        import importlib, sys, warnings
        sys.path.insert(0, {str(ROOT)!r})
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter('always')
            mod = importlib.import_module({path!r})
        caught = [x.category.__name__ for x in w]
        assert caught, f"import {{{path!r}}} 未触发 DeprecationWarning"
        assert all(c == 'DeprecationWarning' for c in caught)
        print("OK", {path!r})
    """)
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=ROOT,
    )
    assert result.returncode == 0, f"旧路径导入失败: {path}\n{result.stdout}\n{result.stderr}"
    assert "OK" in result.stdout


@pytest.mark.parametrize("old_path", [
    "crawlo.bot",
    "crawlo.bot.channels",
    "crawlo.bot.core",
    "crawlo.bot.monitoring",
    "crawlo.bot.templates",
    "crawlo.bot.utils",
    "crawlo.crawler_process",
    "crawlo.framework",
    "crawlo.container",
])
def test_old_path_emits_deprecation_warning(old_path):
    """所有废弃路径导入必须发出 DeprecationWarning 且不报错。"""
    _import_old_path(old_path)


def test_bot_submodule_identity():
    """crawlo.bot.* 子模块/类对象与新路径完全一致（防止重复类副本）。"""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        import crawlo.bot.channels.dingtalk as old_dingtalk
        import crawlo.bot.core.models as old_models
        import crawlo.bot.core.notifier as old_notifier
        import crawlo.bot.templates.manager as old_templates
        import crawlo.bot.utils.deduplicator as old_dedup

    import crawlo.extensions.notifications.channels.dingtalk as new_dingtalk
    import crawlo.extensions.notifications.core.models as new_models
    import crawlo.extensions.notifications.core.notifier as new_notifier
    import crawlo.extensions.notifications.templates.manager as new_templates
    import crawlo.extensions.notifications.utils.deduplicator as new_dedup

    assert old_dingtalk is new_dingtalk
    assert old_models is new_models
    assert old_notifier is new_notifier
    assert old_templates is new_templates
    assert old_dedup is new_dedup

    # 类对象身份一致（isinstance 不失效）
    from crawlo.bot.channels.dingtalk import DingTalkChannel as OldChannel
    from crawlo.extensions.notifications.channels.dingtalk import DingTalkChannel as NewChannel
    from crawlo.bot.utils.deduplicator import MessageDeduplicator as OldDedup
    from crawlo.extensions.notifications.utils.deduplicator import MessageDeduplicator as NewDedup
    assert OldChannel is NewChannel
    assert OldDedup is NewDedup


def test_crawler_process_identity():
    """crawlo.crawler_process / crawlo.framework 与 crawlo.crawler 同一类对象。"""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        from crawlo.crawler_process import CrawlerProcess as OldCP
        from crawlo.framework import CrawloFramework as OldFW
    from crawlo.crawler import CrawlerProcess as NewCP, CrawloFramework as NewFW
    assert OldCP is NewCP
    assert OldFW is NewFW


def test_container_identity():
    """crawlo.container 与 crawlo.core.application 同一模块对象。"""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        import crawlo.container as old_container
    import crawlo.core.application as new_app
    assert old_container is new_app
    assert old_container.default_container is new_app.default_container


def test_top_level_recommended_paths_clean():
    """推荐路径导入不产生任何 DeprecationWarning（子进程严格模式）。"""
    code = textwrap.dedent("""
        import sys
        sys.path.insert(0, %r)
        import warnings
        warnings.simplefilter("error", DeprecationWarning)
        import crawlo
        import crawlo.crawler
        import crawlo.core.application
        import crawlo.extensions.notifications
        print("OK")
    """ % str(ROOT))
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=ROOT,
    )
    assert result.returncode == 0, f"推荐路径产生 DeprecationWarning:\n{result.stderr}"
    assert "OK" in result.stdout
