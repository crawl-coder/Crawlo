#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
测试 HIGH-2: Processor 非原子状态检查竞态条件的修复

验证点：
1. Engine._exit() 使用 processor.idle_async() 而非 processor.idle()
2. Engine._should_exit() 使用 processor.idle_async() 而非 processor.idle()
3. Processor.idle_async() 使用锁保证原子性
"""
import asyncio
import inspect
import ast
import textwrap
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestEngineUsesIdleAsync:
    """测试 Engine 使用 idle_async() 替代 idle()

    Phase 4 更新：Engine._exit/_should_exit 已重构为通过 ``_check_components_idle``
    统一入口（单方法，不再在两处写 idle 检查）。语义上仍通过 processor.idle_async()
    做 Processor 空闲判定，此处验证两种方式之一：
        1. 方法体直接引用 idle_async；或
        2. 方法体调用了 _check_components_idle，且该方法内部引用 processor.idle_async
    """

    @staticmethod
    def _calls_idle_async_via(klass, method_name) -> str:
        """返回 idle_async 被引入的位置（direct / via_unified_gate / via_dispatcher / missing）

        P4 Week1 A3：Engine._exit / _should_exit 等已变成薄代理，转给 self._dispatcher.<target>，
        所以此处允许"薄代理 → dispatcher → idle_async / _check_components_idle"三跳。
        """
        import textwrap, inspect, ast
        from crawlo.core.engine_dispatch import RequestDispatcher

        method_src = textwrap.dedent(inspect.getsource(getattr(klass, method_name)))
        tree = ast.parse(method_src)
        direct_attrs = []
        dispatcher_targets = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                direct_attrs.append(node.func.attr)
                # 识别 self._dispatcher.<method>()
                if (isinstance(node.func.value, ast.Attribute)
                        and node.func.value.attr == '_dispatcher'):
                    dispatcher_targets.append(node.func.attr)
        if 'idle_async' in direct_attrs:
            return 'direct'
        if '_check_components_idle' in direct_attrs:
            gate_src = textwrap.dedent(inspect.getsource(klass._check_components_idle))
            gate_tree = ast.parse(gate_src)
            for node in ast.walk(gate_tree):
                if (isinstance(node, ast.Call)
                        and isinstance(node.func, ast.Attribute)
                        and node.func.attr == 'idle_async'):
                    return 'via_unified_gate'
        # P4 Week1 薄代理到 RequestDispatcher
        for target in dispatcher_targets:
            if not hasattr(RequestDispatcher, target):
                continue
            target_src = textwrap.dedent(inspect.getsource(getattr(RequestDispatcher, target)))
            target_tree = ast.parse(target_src)
            for node in ast.walk(target_tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                    if node.func.attr == 'idle_async':
                        return 'via_dispatcher'
                    # RequestDispatcher 内部统一入口叫 check_components_idle（无下划线），
                    # Engine 薄代理统一入口叫 _check_components_idle（私有前缀）。两种都要识别。
                    if node.func.attr in ('_check_components_idle', 'check_components_idle'):
                        # 间接再转：dispatcher 方法里又调用了自己的 check_components_idle
                        sub_gate = getattr(RequestDispatcher, node.func.attr, None)
                        if sub_gate is not None:
                            sub_src = textwrap.dedent(inspect.getsource(sub_gate))
                            sub_tree = ast.parse(sub_src)
                            for sub_node in ast.walk(sub_tree):
                                if (isinstance(sub_node, ast.Call)
                                        and isinstance(sub_node.func, ast.Attribute)
                                        and sub_node.func.attr == 'idle_async'):
                                    return 'via_dispatcher_gate'
        return 'missing'

    def test_exit_uses_idle_async(self):
        """Engine._exit() 语义上应调用 processor.idle_async()（直接或通过统一入口）"""
        from crawlo.core.engine import Engine
        how = self._calls_idle_async_via(Engine, '_exit')
        assert how != 'missing', (
            "Engine._exit() 未触达 processor.idle_async()："
            "既无直接调用，也未调用内部统一入口 _check_components_idle"
        )

    def test_should_exit_uses_idle_async(self):
        """Engine._should_exit() 语义上应调用 processor.idle_async()"""
        from crawlo.core.engine import Engine
        how = self._calls_idle_async_via(Engine, '_should_exit')
        assert how != 'missing', (
            "Engine._should_exit() 未触达 processor.idle_async()"
        )


class TestProcessorIdleAsyncAtomic:
    """测试 Processor.idle_async() 的原子性"""

    @pytest.mark.asyncio
    async def test_idle_async_uses_lock(self):
        """idle_async() 在锁内执行检查"""
        from crawlo.core.processor import Processor
        
        with patch.object(Processor, '__init__', lambda self, crawler: None):
            proc = Processor.__new__(Processor)
            proc._lock = MagicMock()
            proc._lock.__aenter__ = AsyncMock(return_value=None)
            proc._lock.__aexit__ = AsyncMock(return_value=None)
            proc._processing = {}
            proc.queue = MagicMock()
            proc.queue.empty = MagicMock(return_value=True)
            
            result = await proc.idle_async()
            
            # 验证锁被获取
            proc._lock.__aenter__.assert_called_once()
            proc._lock.__aexit__.assert_called_once()
            assert result is True

    @pytest.mark.asyncio
    async def test_idle_async_not_idle_when_processing(self):
        """正在处理项时 idle_async() 返回 False"""
        from crawlo.core.processor import Processor
        
        with patch.object(Processor, '__init__', lambda self, crawler: None):
            proc = Processor.__new__(Processor)
            proc._lock = MagicMock()
            proc._lock.__aenter__ = AsyncMock(return_value=None)
            proc._lock.__aexit__ = AsyncMock(return_value=None)
            proc._processing = {0: "some_item"}  # 有正在处理的项
            proc.queue = MagicMock()
            proc.queue.empty = MagicMock(return_value=True)
            
            result = await proc.idle_async()
            assert result is False

    @pytest.mark.asyncio
    async def test_idle_async_not_idle_when_queue_has_items(self):
        """队列非空时 idle_async() 返回 False"""
        from crawlo.core.processor import Processor
        
        with patch.object(Processor, '__init__', lambda self, crawler: None):
            proc = Processor.__new__(Processor)
            proc._lock = MagicMock()
            proc._lock.__aenter__ = AsyncMock(return_value=None)
            proc._lock.__aexit__ = AsyncMock(return_value=None)
            proc._processing = {}
            proc.queue = MagicMock()
            proc.queue.empty = MagicMock(return_value=False)
            
            result = await proc.idle_async()
            assert result is False
