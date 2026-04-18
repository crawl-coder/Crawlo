#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
测试 HIGH-4: Engine._fetch 协程结果丢失的修复

验证点：
1. async def + yield (异步生成器) → 正确处理
2. def + yield (同步生成器) → 正确处理
3. async def + return (协程返回单个值) → 不再丢失数据
4. async def + return None (协程返回None) → 返回 None
5. def + return Request (同步返回单个值) → 正确包装
6. def + return list (同步返回列表) → 正确处理
7. callback 返回 None → 返回 None
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from crawlo import Request, Item
from crawlo.items.base import Field


# 创建一个带字段的测试 Item 子类
class TestItem(Item):
    title = Field()
    url = Field()
    key = Field()


def _make_engine():
    """创建一个测试用 Engine 实例"""
    from crawlo.core.engine import Engine
    with patch.object(Engine, '__init__', lambda self, crawler: None):
        eng = Engine.__new__(Engine)
        eng.spider = MagicMock()
        eng.downloader = AsyncMock()
        eng.logger = MagicMock()
        return eng


def _make_response():
    """创建测试用 Response"""
    response = MagicMock()
    response.meta = {}
    response.url = "http://example.com"
    return response


class TestFetchAsyncGenerator:
    """测试异步生成器回调（最常见的正确用法）"""

    @pytest.mark.asyncio
    async def test_async_gen_callback(self):
        """async def + yield 应正确处理"""
        engine = _make_engine()
        response = _make_response()

        async def callback(resp):
            yield Request(url="http://example.com/1")
            yield TestItem(title="value")

        request = MagicMock()
        request.callback = callback

        result = await engine._fetch(request)
        # 验证返回了异步生成器
        assert result is not None
        items = []
        async for item in result:
            items.append(item)
        assert len(items) == 2
        assert isinstance(items[0], Request)
        assert isinstance(items[1], Item)


class TestFetchSyncGenerator:
    """测试同步生成器回调"""

    @pytest.mark.asyncio
    async def test_sync_gen_callback(self):
        """def + yield 应正确处理"""
        engine = _make_engine()
        response = _make_response()

        def callback(resp):
            yield Request(url="http://example.com/1")
            yield TestItem(title="value")

        request = MagicMock()
        request.callback = callback

        result = await engine._fetch(request)
        assert result is not None
        items = []
        async for item in result:
            items.append(item)
        assert len(items) == 2


class TestFetchCoroutineResult:
    """测试协程回调（async def 不使用 yield）- 核心修复点"""

    @pytest.mark.asyncio
    async def test_async_return_request(self):
        """async def + return Request 不再丢失数据"""
        engine = _make_engine()

        async def callback(resp):
            return Request(url="http://example.com/page")

        request = MagicMock()
        request.callback = callback

        result = await engine._fetch(request)
        assert result is not None, "协程返回的 Request 不应丢失"
        items = []
        async for item in result:
            items.append(item)
        assert len(items) == 1
        assert isinstance(items[0], Request)
        assert items[0].url == "http://example.com/page"

    @pytest.mark.asyncio
    async def test_async_return_item(self):
        """async def + return Item 不再丢失数据"""
        engine = _make_engine()

        async def callback(resp):
            return TestItem(title="test")

        request = MagicMock()
        request.callback = callback

        result = await engine._fetch(request)
        assert result is not None, "协程返回的 Item 不应丢失"
        items = []
        async for item in result:
            items.append(item)
        assert len(items) == 1
        assert isinstance(items[0], Item)

    @pytest.mark.asyncio
    async def test_async_return_none(self):
        """async def + return None 返回 None"""
        engine = _make_engine()

        async def callback(resp):
            return None

        request = MagicMock()
        request.callback = callback

        result = await engine._fetch(request)
        assert result is None

    @pytest.mark.asyncio
    async def test_async_return_list(self):
        """async def + return [Request, Item] 正确处理"""
        engine = _make_engine()

        async def callback(resp):
            return [
                Request(url="http://example.com/1"),
                TestItem(key="val"),
            ]

        request = MagicMock()
        request.callback = callback

        result = await engine._fetch(request)
        assert result is not None
        items = []
        async for item in result:
            items.append(item)
        assert len(items) == 2
        assert isinstance(items[0], Request)
        assert isinstance(items[1], Item)


class TestFetchSyncReturnValue:
    """测试同步函数返回非生成器值"""

    @pytest.mark.asyncio
    async def test_sync_return_request(self):
        """def + return Request 正确包装"""
        engine = _make_engine()

        def callback(resp):
            return Request(url="http://example.com/page")

        request = MagicMock()
        request.callback = callback

        result = await engine._fetch(request)
        assert result is not None
        items = []
        async for item in result:
            items.append(item)
        assert len(items) == 1
        assert isinstance(items[0], Request)

    @pytest.mark.asyncio
    async def test_sync_return_list(self):
        """def + return [Request, Item] 正确处理"""
        engine = _make_engine()

        def callback(resp):
            return [Request(url="http://example.com/1"), TestItem(key="val")]

        request = MagicMock()
        request.callback = callback

        result = await engine._fetch(request)
        assert result is not None
        items = []
        async for item in result:
            items.append(item)
        assert len(items) == 2


class TestFetchNoneCallback:
    """测试回调返回 None"""

    @pytest.mark.asyncio
    async def test_callback_returns_none(self):
        """callback 返回 None 应返回 None"""
        engine = _make_engine()

        def callback(resp):
            return None

        request = MagicMock()
        request.callback = callback

        result = await engine._fetch(request)
        assert result is None

    @pytest.mark.asyncio
    async def test_no_callback_uses_parse(self):
        """无 callback 时使用 spider.parse"""
        engine = _make_engine()
        
        async def parse(resp):
            yield Request(url="http://example.com/parsed")

        engine.spider.parse = parse
        request = MagicMock()
        request.callback = None

        result = await engine._fetch(request)
        assert result is not None
        items = []
        async for item in result:
            items.append(item)
        assert len(items) == 1


class TestFetchSpiderNone:
    """测试 spider 为 None 的情况"""

    @pytest.mark.asyncio
    async def test_spider_none_returns_none(self):
        """spider 为 None 时返回 None"""
        engine = _make_engine()
        engine.spider = None

        request = MagicMock()
        request.callback = None

        result = await engine._fetch(request)
        assert result is None
