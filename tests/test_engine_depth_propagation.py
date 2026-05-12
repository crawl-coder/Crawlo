#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试 Engine 的 depth 自动传播机制

验证以下场景：
1. start_requests 的 Request depth 初始化为 1
2. 子 Request 的 depth 自动注入（parent_depth + 1）
3. DEPTH_PRIORITY=1 时详情页优先级更高（深度优先）
4. errback 产生的 Request 也能传播 depth
5. 用户手动设置 depth 时不被覆盖
6. DEPTH_PRIORITY=-1 时广度优先（列表页优先）
7. DEPTH_PRIORITY=0 时不按深度调整优先级
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from crawlo import Request, Item
from crawlo.core.engine import Engine
from crawlo.utils.request.request import set_request


# ============================================
# 测试 1: set_request 的 depth 初始化
# ============================================
class TestSetRequestDepth:
    """测试 set_request 函数的 depth 初始化逻辑"""

    def test_depth_not_set_should_initialize_to_1(self):
        """depth 未设置时应初始化为 1（向后兼容 start_requests）"""
        request = Request(url="http://example.com/page1")
        assert 'depth' not in request.meta
        
        set_request(request, priority=1)
        
        assert request.meta['depth'] == 1
        # priority = 0 - depth * DEPTH_PRIORITY = 0 - 1*1 = -1
        assert request.priority == -1

    def test_depth_already_set_should_not_override(self):
        """depth 已设置时不应被覆盖（框架层面已注入）"""
        request = Request(url="http://example.com/page1")
        request.meta['depth'] = 5  # 框架层面已设置
        
        set_request(request, priority=1)
        
        # depth 应保持为 5，不被重置为 1
        assert request.meta['depth'] == 5
        # priority = 0 - 5*1 = -5
        assert request.priority == -5

    def test_depth_with_priority_0_should_not_adjust(self):
        """DEPTH_PRIORITY=0 时不应调整优先级"""
        request = Request(url="http://example.com/page1")
        original_priority = request.priority  # 默认 0
        
        set_request(request, priority=0)
        
        assert request.meta['depth'] == 1
        # priority 不应被调整
        assert request.priority == original_priority

    def test_depth_with_negative_priority_bfs(self):
        """DEPTH_PRIORITY=-1 时应实现广度优先（深度越深 priority 越大）"""
        # depth=1 的请求
        req1 = Request(url="http://example.com/page1")
        req1.meta['depth'] = 1
        set_request(req1, priority=-1)
        # priority = 0 - 1*(-1) = 1
        
        # depth=2 的请求
        req2 = Request(url="http://example.com/page2")
        req2.meta['depth'] = 2
        set_request(req2, priority=-1)
        # priority = 0 - 2*(-1) = 2
        
        # 广度优先：depth 小的 priority 小，先出队
        assert req1.priority < req2.priority  # 1 < 2


# ============================================
# 测试 2: Engine._handle_spider_output 的 depth 传播
# ============================================
class TestEngineDepthPropagation:
    """测试 Engine 的 depth 自动传播机制"""

    @pytest.fixture
    def mock_engine(self):
        """创建模拟的 Engine 实例"""
        mock_crawler = MagicMock()
        mock_crawler.settings = {}
        mock_crawler.subscriber = MagicMock()
        mock_crawler.subscriber.notify = AsyncMock()
        
        engine = Engine(crawler=mock_crawler)
        engine.processor = MagicMock()
        engine.processor.enqueue = AsyncMock()
        engine.spider = MagicMock()
        engine.crawler = mock_crawler
        return engine

    @pytest.mark.asyncio
    async def test_start_request_depth_default_0(self, mock_engine):
        """start_requests 的请求（无 parent）depth 应为 0"""
        # 模拟 start_requests 的输出（没有 parent_request）
        async def mock_outputs():
            yield Request(url="http://example.com/list1")
            yield Request(url="http://example.com/list2")
        
        await mock_engine._handle_spider_output(mock_outputs(), parent_request=None)
        
        # 验证所有请求的 depth 都是 1（0 + 1）
        calls = mock_engine.processor.enqueue.call_args_list
        assert len(calls) == 2
        
        req1 = calls[0][0][0]
        req2 = calls[1][0][0]
        assert req1.meta['depth'] == 1
        assert req2.meta['depth'] == 1

    @pytest.mark.asyncio
    async def test_child_request_depth_inheritance(self, mock_engine):
        """子请求的 depth 应为 parent_depth + 1"""
        # 模拟一个 depth=3 的父请求
        parent_request = Request(url="http://example.com/parent")
        parent_request.meta['depth'] = 3
        
        async def mock_outputs():
            yield Request(url="http://example.com/child1")
            yield Request(url="http://example.com/child2")
            yield Request(url="http://example.com/child3")
        
        await mock_engine._handle_spider_output(mock_outputs(), parent_request=parent_request)
        
        # 验证所有子请求的 depth 都是 4（3 + 1）
        calls = mock_engine.processor.enqueue.call_args_list
        assert len(calls) == 3
        
        for call in calls:
            req = call[0][0]
            assert req.meta['depth'] == 4

    @pytest.mark.asyncio
    async def test_manual_depth_should_not_override(self, mock_engine):
        """用户手动设置的 depth 不应被框架覆盖"""
        parent_request = Request(url="http://example.com/parent")
        parent_request.meta['depth'] = 2
        
        async def mock_outputs():
            # 用户手动设置了 depth=10
            req = Request(url="http://example.com/custom")
            req.meta['depth'] = 10
            yield req
        
        await mock_engine._handle_spider_output(mock_outputs(), parent_request=parent_request)
        
        # 验证手动设置的 depth=10 未被覆盖
        call = mock_engine.processor.enqueue.call_args_list[0]
        req = call[0][0]
        assert req.meta['depth'] == 10

    @pytest.mark.asyncio
    async def test_item_output_should_not_have_depth(self, mock_engine):
        """Item 类型输出不应设置 depth"""
        parent_request = Request(url="http://example.com/parent")
        parent_request.meta['depth'] = 1
        
        async def mock_outputs():
            yield Item(title="test item")
            yield Request(url="http://example.com/child")
        
        await mock_engine._handle_spider_output(mock_outputs(), parent_request=parent_request)
        
        calls = mock_engine.processor.enqueue.call_args_list
        item = calls[0][0][0]
        req = calls[1][0][0]
        
        # Item 不应有 depth
        assert not hasattr(item, 'meta') or 'depth' not in item.meta
        # Request 应有 depth=2
        assert req.meta['depth'] == 2


# ============================================
# 测试 3: errback 的 depth 传播
# ============================================
class TestErrbackDepthPropagation:
    """测试 errback 返回值的 depth 传播"""

    @pytest.fixture
    def mock_engine(self):
        """创建模拟的 Engine 实例"""
        mock_crawler = MagicMock()
        mock_crawler.settings = {}
        mock_crawler.subscriber = MagicMock()
        mock_crawler.subscriber.notify = AsyncMock()
        
        engine = Engine(crawler=mock_crawler)
        engine.processor = MagicMock()
        engine.processor.enqueue = AsyncMock()
        engine.spider = MagicMock()
        engine.crawler = mock_crawler
        return engine

    @pytest.mark.asyncio
    async def test_errback_single_request_depth(self, mock_engine):
        """errback 返回单个 Request 时应传播 depth"""
        parent_request = Request(url="http://example.com/failed")
        parent_request.meta['depth'] = 3
        
        # errback 返回一个重试请求
        retry_request = Request(url="http://example.com/retry")
        
        await mock_engine._handle_errback_output(retry_request, parent_request=parent_request)
        
        call = mock_engine.processor.enqueue.call_args_list[0]
        req = call[0][0]
        # depth 应为 parent_depth + 1 = 4
        assert req.meta['depth'] == 4

    @pytest.mark.asyncio
    async def test_errback_list_requests_depth(self, mock_engine):
        """errback 返回 Request 列表时应传播 depth"""
        parent_request = Request(url="http://example.com/failed")
        parent_request.meta['depth'] = 2
        
        retry_requests = [
            Request(url="http://example.com/retry1"),
            Request(url="http://example.com/retry2"),
        ]
        
        await mock_engine._handle_errback_output(retry_requests, parent_request=parent_request)
        
        calls = mock_engine.processor.enqueue.call_args_list
        assert len(calls) == 2
        
        for call in calls:
            req = call[0][0]
            assert req.meta['depth'] == 3  # 2 + 1

    @pytest.mark.asyncio
    async def test_errback_async_generator_depth(self, mock_engine):
        """errback 返回异步生成器时应传播 depth"""
        parent_request = Request(url="http://example.com/failed")
        parent_request.meta['depth'] = 1
        
        async def errback_gen():
            yield Request(url="http://example.com/retry1")
            yield Request(url="http://example.com/retry2")
        
        await mock_engine._handle_errback_output(errback_gen(), parent_request=parent_request)
        
        calls = mock_engine.processor.enqueue.call_args_list
        assert len(calls) == 2
        
        for call in calls:
            req = call[0][0]
            assert req.meta['depth'] == 2  # 1 + 1


# ============================================
# 测试 4: 集成测试 - 模拟 ofweek 场景
# ============================================
class TestOfWeekScenario:
    """模拟 ofweek 爬虫的 depth 传播和优先级调整"""

    def test_list_page_vs_detail_page_priority_dfs(self):
        """
        DEPTH_PRIORITY=1（深度优先）场景：
        - 列表页 depth=1，priority = 0 - 1*1 = -1
        - 详情页 depth=2，priority = 0 - 2*1 = -2
        - 详情页 priority 更小，应先出队
        """
        # 模拟 500 个列表页请求
        list_pages = []
        for i in range(500):
            req = Request(url=f"http://example.com/list-{i}")
            req.meta['depth'] = 1
            set_request(req, priority=1)
            list_pages.append(req)
        
        # 模拟从第一个列表页解析出的 20 个详情页
        detail_pages = []
        for i in range(20):
            req = Request(url=f"http://example.com/detail-{i}")
            req.meta['depth'] = 2
            set_request(req, priority=1)
            detail_pages.append(req)
        
        # 验证详情页 priority 更小（-2 < -1）
        assert list_pages[0].priority == -1
        assert detail_pages[0].priority == -2
        assert detail_pages[0].priority < list_pages[0].priority

    def test_list_page_vs_detail_page_priority_bfs(self):
        """
        DEPTH_PRIORITY=-1（广度优先）场景：
        - 列表页 depth=1，priority = 0 - 1*(-1) = 1
        - 详情页 depth=2，priority = 0 - 2*(-1) = 2
        - 列表页 priority 更小，应先出队
        """
        list_req = Request(url="http://example.com/list")
        list_req.meta['depth'] = 1
        set_request(list_req, priority=-1)
        
        detail_req = Request(url="http://example.com/detail")
        detail_req.meta['depth'] = 2
        set_request(detail_req, priority=-1)
        
        # 验证列表页 priority 更小（1 < 2）
        assert list_req.priority == 1
        assert detail_req.priority == 2
        assert list_req.priority < detail_req.priority

    def test_multi_level_depth_propagation(self):
        """
        多级 depth 传播测试：
        - 列表页 depth=1
        - 详情页 depth=2
        - 评论页 depth=3
        """
        # 列表页
        list_req = Request(url="http://example.com/list")
        list_req.meta['depth'] = 1
        set_request(list_req, priority=1)
        
        # 详情页
        detail_req = Request(url="http://example.com/detail")
        detail_req.meta['depth'] = 2
        set_request(detail_req, priority=1)
        
        # 评论页
        comment_req = Request(url="http://example.com/comment")
        comment_req.meta['depth'] = 3
        set_request(comment_req, priority=1)
        
        # 验证优先级顺序：评论页 < 详情页 < 列表页
        assert comment_req.priority < detail_req.priority < list_req.priority
        # -3 < -2 < -1


# ============================================
# 测试 5: 边界情况测试
# ============================================
class TestEdgeCases:
    """测试边界情况"""

    @pytest.mark.asyncio
    async def test_none_parent_request(self):
        """parent_request=None 时 depth 应为 1"""
        mock_crawler = MagicMock()
        mock_crawler.settings = {}
        mock_crawler.subscriber = MagicMock()
        mock_crawler.subscriber.notify = AsyncMock()
        
        engine = Engine(crawler=mock_crawler)
        engine.processor = MagicMock()
        engine.processor.enqueue = AsyncMock()
        engine.spider = MagicMock()
        engine.crawler = mock_crawler
        
        async def mock_outputs():
            yield Request(url="http://example.com/start")
        
        await engine._handle_spider_output(mock_outputs(), parent_request=None)
        
        call = engine.processor.enqueue.call_args_list[0]
        req = call[0][0]
        assert req.meta['depth'] == 1  # 0 + 1

    @pytest.mark.asyncio
    async def test_parent_request_without_meta(self):
        """parent_request 没有 meta 属性时应视为 depth=0"""
        mock_crawler = MagicMock()
        mock_crawler.settings = {}
        mock_crawler.subscriber = MagicMock()
        mock_crawler.subscriber.notify = AsyncMock()
        
        engine = Engine(crawler=mock_crawler)
        engine.processor = MagicMock()
        engine.processor.enqueue = AsyncMock()
        engine.spider = MagicMock()
        engine.crawler = mock_crawler
        
        # 创建一个没有 meta 的 mock 对象
        parent_request = MagicMock(spec=[])  # 空 spec，没有 meta
        
        async def mock_outputs():
            yield Request(url="http://example.com/child")
        
        await engine._handle_spider_output(mock_outputs(), parent_request=parent_request)
        
        call = engine.processor.enqueue.call_args_list[0]
        req = call[0][0]
        assert req.meta['depth'] == 1  # 0 + 1

    def test_depth_with_large_value(self):
        """depth 很大时 priority 应正确计算"""
        req = Request(url="http://example.com/deep")
        req.meta['depth'] = 100
        set_request(req, priority=1)
        
        # priority = 0 - 100*1 = -100
        assert req.priority == -100

    def test_depth_zero_edge_case(self):
        """depth=0 的边界情况（虽然不应该出现）"""
        req = Request(url="http://example.com/zero")
        req.meta['depth'] = 0
        set_request(req, priority=1)
        
        # priority = 0 - 0*1 = 0
        assert req.priority == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
