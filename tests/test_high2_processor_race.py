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
    """测试 Engine 使用 idle_async() 替代 idle()"""

    def test_exit_uses_idle_async(self):
        """Engine._exit() 应使用 processor.idle_async()"""
        from crawlo.core.engine import Engine
        source = textwrap.dedent(inspect.getsource(Engine._exit))
        tree = ast.parse(source)
        
        call_names = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    call_names.append(node.func.attr)
        
        # 应包含 idle_async，不应包含直接调用 idle（除了 scheduler.idle()）
        assert 'idle_async' in call_names, (
            "Engine._exit() should call processor.idle_async() instead of processor.idle()"
        )

    def test_should_exit_uses_idle_async(self):
        """Engine._should_exit() 应使用 processor.idle_async()"""
        from crawlo.core.engine import Engine
        source = textwrap.dedent(inspect.getsource(Engine._should_exit))
        tree = ast.parse(source)
        
        call_names = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    call_names.append(node.func.attr)
        
        # 应包含 idle_async
        assert 'idle_async' in call_names, (
            "Engine._should_exit() should call processor.idle_async()"
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
