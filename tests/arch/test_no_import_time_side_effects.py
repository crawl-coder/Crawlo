#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Phase 4 验收测试：import 期零副作用
==================================

验收标准（FRAMEWORK_REFACTOR_PLAN.md）：
    **facade 懒加载**：import crawlo 不触发 ``ApplicationContext`` 自动创建。

背景
----
Phase 4 Step 2 把 ``_DEFAULT_SPIDER_REGISTRY`` 改为 proxy 转发到 ctx，
SpiderMeta 在 import 期会触发注册（写 proxy）。proxy 必须在 ctx 未就绪时
回退到进程级 ``_fallback``，**不得**调用 ``get_global_context(create_if_missing=True)``
导致 ctx 在 import 阶段就被创建——否则：
1. 用户 ``import crawlo`` 即创建 ctx，违背"惰性初始化"原则；
2. 测试隔离困难（每次 import 都污染全局状态）；
3. Phase 5 的循环依赖治理会因 import 期副作用而难以收紧契约。

本测试用子进程在干净 Python 解释器中执行 import 序列，检查
``crawlo.core.application._global_context`` 是否仍为 None。
"""
import subprocess
import sys
import textwrap

import pytest


def _run_isolated_check(code: str) -> subprocess.CompletedProcess:
    """在全新子进程中执行 code，返回 CompletedProcess。

    子进程不继承当前测试会话已 import 的模块状态，保证 import 期副作用可被观测。
    """
    return subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=30,
    )


# import 序列：覆盖常用入口 + 触发 SpiderMeta 元类的 spider 模块
_IMPORT_MODULES = """
import crawlo
import crawlo.spider
import crawlo.spider.spider
import crawlo.core.application
import crawlo.core.engine
import crawlo.core.scheduling.task_scheduler
import crawlo.core.processor
import crawlo.queue.queue_manager
import crawlo.crawler
import crawlo.crawler_process
import crawlo.framework
import crawlo.commands.run
"""


class TestNoImportTimeSideEffects:
    """Phase 4 验收：import 期不得触发 ApplicationContext 创建。"""

    def test_import_crawlo_does_not_create_context(self):
        """import crawlo + 常用子模块后，``_global_context`` 必须仍为 None。"""
        code = textwrap.dedent(_IMPORT_MODULES) + textwrap.dedent(
            """
            from crawlo.core import application as app_mod
            import sys

            ctx = app_mod._global_context
            if ctx is not None:
                print(f"FAIL: _global_context is not None: {ctx!r}", file=sys.stderr)
                sys.exit(1)
            print("OK: _global_context is None after import")
            """
        )
        result = _run_isolated_check(code)
        assert result.returncode == 0, (
            f"import 期触发了 ctx 创建（应保持 None）。\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
        assert "OK: _global_context is None after import" in result.stdout

    def test_spider_meta_registration_does_not_create_context(self):
        """定义 Spider 子类（触发 SpiderMeta.__new__）不得创建 ctx。

        SpiderMeta 写 ``_DEFAULT_SPIDER_REGISTRY[name] = cls``，proxy 必须回退到
        ``_fallback`` 而非触发 ``get_global_context(create_if_missing=True)``。
        """
        code = textwrap.dedent(_IMPORT_MODULES) + textwrap.dedent(
            """
            from crawlo.spider import Spider
            from crawlo.core import application as app_mod
            import sys

            class _ProbeSpider(Spider):
                name = 'phase4_probe_spider'
                def parse(self, response):
                    pass

            ctx = app_mod._global_context
            if ctx is not None:
                print(f"FAIL: SpiderMeta registration created ctx: {ctx!r}", file=sys.stderr)
                sys.exit(1)

            # 校验 proxy 的 fallback 机制：spider 应注册到 fallback（ctx 未就绪）
            from crawlo.spider.spider import _DEFAULT_SPIDER_REGISTRY
            target = _DEFAULT_SPIDER_REGISTRY._target()
            if 'phase4_probe_spider' not in target:
                print(f"FAIL: probe spider not in fallback registry: {target!r}", file=sys.stderr)
                sys.exit(1)

            print("OK: SpiderMeta registration did not create ctx, fallback used")
            """
        )
        result = _run_isolated_check(code)
        assert result.returncode == 0, (
            f"SpiderMeta 注册触发了 ctx 创建。\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
        assert "OK: SpiderMeta registration did not create ctx, fallback used" in result.stdout

    def test_proxy_syncs_fallback_to_ctx_on_first_access(self):
        """首次 ``get_global_context(create_if_missing=True)`` 后，
        fallback 中累积的注册项应自动同步到 ctx.registries.spider_registry。"""
        code = textwrap.dedent(_IMPORT_MODULES) + textwrap.dedent(
            """
            from crawlo.spider import Spider
            from crawlo.core import application as app_mod
            from crawlo.spider.spider import _DEFAULT_SPIDER_REGISTRY
            import sys

            class _SyncProbeSpider(Spider):
                name = 'phase4_sync_probe'
                def parse(self, response):
                    pass

            # ctx 尚未创建，probe 在 fallback 中
            assert app_mod._global_context is None, "ctx should not exist yet"

            # 首次显式创建 ctx → 触发 fallback → ctx 同步
            ctx = app_mod.get_global_context()
            reg = ctx.registries.spider_registry
            if 'phase4_sync_probe' not in reg:
                print(f"FAIL: fallback not synced to ctx: {reg!r}", file=sys.stderr)
                sys.exit(1)

            # fallback 应已清空（同步完成后）
            if _DEFAULT_SPIDER_REGISTRY._fallback:
                print(f"FAIL: fallback not cleared after sync: {_DEFAULT_SPIDER_REGISTRY._fallback!r}", file=sys.stderr)
                sys.exit(1)

            print("OK: fallback synced to ctx on first get_global_context()")
            """
        )
        result = _run_isolated_check(code)
        assert result.returncode == 0, (
            f"fallback → ctx 同步失败。\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
        assert "OK: fallback synced to ctx on first get_global_context()" in result.stdout
