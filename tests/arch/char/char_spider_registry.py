#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Characterization Test — Spider 注册表行为
========================================

Phase 1 已完成：SpiderMeta 注册冲突延迟到解析时。
Phase 4 Step 2 已完成：ctx 为唯一数据源，_DEFAULT_SPIDER_REGISTRY 改为 proxy。

当前行为：
1. 重复定义同名 Spider 时，不 raise，后注册覆盖先注册 + warnings.warn(SpiderNameConflictWarning)
2. get_spider_by_name 命中冲突时 raise AmbiguousSpiderError（含候选类全路径）
3. register_spider(name, cls, override=True) 可显式消除歧义
4. _DEFAULT_SPIDER_REGISTRY 是 proxy，转发到 ctx.registries.spider_registry；
   注册 Spider 立即反映到 ctx，无需手动同步（双数据源 bug 已消除）。
"""
import warnings

import pytest

from crawlo.spider.exceptions import AmbiguousSpiderError, SpiderNameConflictWarning
from crawlo.spider.spider import (
    Spider,
    _DEFAULT_SPIDER_REGISTRY,
    _SPIDER_CONFLICTS,
    get_global_spider_registry,
    get_spider_by_name,
    register_spider,
    reset_spider_registry,
)


@pytest.fixture
def isolated_registry():
    """保存并清空注册表+冲突表，测试后恢复，保证测试隔离。"""
    saved_reg = dict(_DEFAULT_SPIDER_REGISTRY)
    saved_conflicts = dict(_SPIDER_CONFLICTS)
    _DEFAULT_SPIDER_REGISTRY.clear()
    _SPIDER_CONFLICTS.clear()
    yield _DEFAULT_SPIDER_REGISTRY
    _DEFAULT_SPIDER_REGISTRY.clear()
    _DEFAULT_SPIDER_REGISTRY.update(saved_reg)
    _SPIDER_CONFLICTS.clear()
    _SPIDER_CONFLICTS.update(saved_conflicts)


class TestSpiderRegistryBaseline:
    """Spider 注册表行为测试（Phase 1 后）。"""

    def test_import_same_name_warns_not_raises(self, isolated_registry):
        """重复定义同名 Spider 时，不 raise，仅发出 SpiderNameConflictWarning。"""
        class FirstSpider(Spider):
            name = 'char_dup_name'

            def parse(self, response):
                pass

        assert 'char_dup_name' in isolated_registry

        # 第二个同名 Spider 不应 raise，应发出 warning
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            class SecondSpider(Spider):
                name = 'char_dup_name'

                def parse(self, response):
                    pass

        # 验证发出了 SpiderNameConflictWarning
        conflict_warnings = [w for w in caught if issubclass(w.category, SpiderNameConflictWarning)]
        assert len(conflict_warnings) >= 1, "应发出 SpiderNameConflictWarning"

        # 后注册覆盖先注册
        assert isolated_registry['char_dup_name'] is SecondSpider

    def test_get_spider_by_name_raises_ambiguous(self, isolated_registry):
        """冲突的 name 通过 get_spider_by_name 解析时抛 AmbiguousSpiderError。"""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", SpiderNameConflictWarning)

            class FirstSpider(Spider):
                name = 'char_amb_name'

                def parse(self, response):
                    pass

            class SecondSpider(Spider):
                name = 'char_amb_name'

                def parse(self, response):
                    pass

        # get_spider_by_name 应抛 AmbiguousSpiderError
        with pytest.raises(AmbiguousSpiderError) as exc_info:
            get_spider_by_name('char_amb_name')

        # 错误信息应包含候选类全路径
        err = exc_info.value
        assert 'char_amb_name' in str(err)
        assert len(err.candidates) >= 2
        # 候选类路径应包含完整模块路径
        for candidate in err.candidates:
            assert '.' in candidate

    def test_register_spider_resolves_conflict(self, isolated_registry):
        """register_spider 清除冲突记录，get_spider_by_name 正常返回。"""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", SpiderNameConflictWarning)

            class FirstSpider(Spider):
                name = 'char_resolve_name'

                def parse(self, response):
                    pass

            class SecondSpider(Spider):
                name = 'char_resolve_name'

                def parse(self, response):
                    pass

        # 冲突存在
        with pytest.raises(AmbiguousSpiderError):
            get_spider_by_name('char_resolve_name')

        # 显式注册消除歧义
        register_spider('char_resolve_name', FirstSpider, override=True)

        # 冲突已清除，正常返回
        result = get_spider_by_name('char_resolve_name')
        assert result is FirstSpider

    def test_registry_double_data_source_sync(self, isolated_registry):
        """Phase 4 Step 2 验收：ctx 为唯一数据源，proxy 转发，无需手动同步。

        新行为（替代原"双数据源 bug 基线"）：
        - 注册 Spider 立即反映到 ctx.registries.spider_registry（无需 get_global_spider_registry() 同步）
        - _DEFAULT_SPIDER_REGISTRY 是 proxy，dict(proxy) 与 ctx.registries.spider_registry 内容一致
        - get_global_spider_registry() 返回的副本与 ctx.registries.spider_registry 内容一致
        """
        import crawlo.core.application as app_mod
        from crawlo.core.application import get_global_context, reset_global_context

        # 保存原始全局上下文，测试后恢复
        saved_ctx = app_mod._global_context
        reset_global_context()
        try:
            class SyncSpider(Spider):
                name = 'char_sync_name'

                def parse(self, response):
                    pass

            ctx = get_global_context()

            # 新行为：注册立即反映到 ctx，无需手动同步
            assert 'char_sync_name' in ctx.registries.spider_registry, (
                "Phase 4 Step 2：注册 Spider 应立即反映到 ctx.registries.spider_registry（proxy 转发）"
            )
            assert ctx.registries.spider_registry.get('char_sync_name') is SyncSpider

            # proxy 转发：dict(_DEFAULT_SPIDER_REGISTRY) 与 ctx.registries.spider_registry 内容一致
            proxy_view = dict(isolated_registry)
            assert 'char_sync_name' in proxy_view
            assert proxy_view['char_sync_name'] is SyncSpider

            # get_global_spider_registry() 返回副本，内容一致
            reg_copy = get_global_spider_registry()
            assert 'char_sync_name' in reg_copy
            assert reg_copy['char_sync_name'] is SyncSpider
        finally:
            app_mod._global_context = saved_ctx
