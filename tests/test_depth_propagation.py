#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试框架级 depth 自动传播功能
覆盖三个修改点：
1. engine._handle_spider_output — depth 自动传播
2. engine._handle_errback_output — depth 传播到 errback 输出
3. utils.request.request.set_request — 不再自增 depth，向后兼容
4. DEPTH_PRIORITY 正/负值与深度优先/广度优先的对应关系
"""

import asyncio
import sys
import os
import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo import Request, Item
from crawlo.network.request import RequestPriority
from crawlo.utils.request.request import set_request
from crawlo.exceptions import OutputError


# ============================================================
# 1. set_request 测试
# ============================================================

class TestSetRequest:
    """测试 set_request 不再自增 depth，向后兼容 start_requests"""

    def test_depth_not_set_defaults_to_1(self):
        """未设置 depth 的请求（start_requests），set_request 将 depth 默认设为 1"""
        request = Request(url="https://example.com")
        assert 'depth' not in request.meta
        set_request(request, priority=1)
        assert request.meta['depth'] == 1

    def test_depth_already_set_not_overwritten(self):
        """已有 depth 的请求（框架传播），set_request 不再自增"""
        request = Request(url="https://example.com", meta={'depth': 3})
        set_request(request, priority=1)
        assert request.meta['depth'] == 3  # 不再是 3+1=4

    def test_depth_priority_positive_deepens_priority(self):
        """DEPTH_PRIORITY > 0：深度越深 → 内部 priority 越小 → 深度优先"""
        # depth=1, priority=0（用户传入）→ 内部 -0 = 0, 调整后 0 - 1*1 = -1
        r1 = Request(url="https://list.com")
        set_request(r1, priority=1)
        assert r1.priority == -1  # 0 - 1*1

        # depth=2, priority=0 → 调整后 0 - 2*1 = -2
        r2 = Request(url="https://detail.com", meta={'depth': 2})
        set_request(r2, priority=1)
        assert r2.priority == -2  # 更小，先出队 → 深度优先

        # depth=3
        r3 = Request(url="https://sub.com", meta={'depth': 3})
        set_request(r3, priority=1)
        assert r3.priority == -3

    def test_depth_priority_negative_breadth_first(self):
        """DEPTH_PRIORITY < 0：深度越深 → 内部 priority 越大 → 广度优先"""
        # depth=1, priority=0 → 0 - 1*(-1) = 1
        r1 = Request(url="https://list.com")
        set_request(r1, priority=-1)
        assert r1.priority == 1

        # depth=2, priority=0 → 0 - 2*(-1) = 2
        r2 = Request(url="https://detail.com", meta={'depth': 2})
        set_request(r2, priority=-1)
        assert r2.priority == 2  # 更大，后出队 → 广度优先

    def test_depth_priority_zero_no_adjustment(self):
        """DEPTH_PRIORITY = 0：不按深度调整优先级"""
        r1 = Request(url="https://a.com")
        set_request(r1, priority=0)
        assert r1.priority == 0  # 无调整

        r2 = Request(url="https://b.com", meta={'depth': 5})
        set_request(r2, priority=0)
        assert r2.priority == 0  # 仍然无调整

    def test_user_priority_negated_then_adjusted(self):
        """用户设置 priority 后，先取反再根据 depth 调整"""
        # 用户传入 priority=100 → 内部 -100
        # depth=2, DEPTH_PRIORITY=1 → -100 - 2*1 = -102
        r = Request(url="https://example.com", priority=100, meta={'depth': 2})
        set_request(r, priority=1)
        assert r.priority == -102  # (-100) - 2*1

    def test_user_priority_high_before_depth_adjustment(self):
        """高优先级请求在 depth 调整后仍然优先"""
        # 列表页: priority=0(用户), depth=1, DEPTH_PRIORITY=1 → 内部 0 - 1 = -1
        # 详情页: priority=100(用户), depth=2, DEPTH_PRIORITY=1 → 内部 -100 - 2 = -102
        list_req = Request(url="https://list.com", priority=0)
        set_request(list_req, priority=1)

        detail_req = Request(url="https://detail.com", priority=100, meta={'depth': 2})
        set_request(detail_req, priority=1)

        assert detail_req.priority < list_req.priority  # -102 < -1，详情页先出队


# ============================================================
# 2. _handle_spider_output depth 传播测试
# ============================================================

class TestHandleSpiderOutputDepthPropagation:
    """测试 engine._handle_spider_output 自动传播 depth"""

    @pytest.fixture
    def engine_mock(self):
        """创建最小化的 Engine mock"""
        from crawlo.core.engine import Engine

        engine = Mock(spec=Engine)
        engine.processor = Mock()
        engine.processor.enqueue = AsyncMock()
        engine.crawler = Mock()
        engine.spider = Mock()
        engine._create_background_task = Mock()

        # 绑定真实方法
        from crawlo.core.engine import Engine as RealEngine
        engine._handle_spider_output = RealEngine._handle_spider_output.__get__(engine, Engine)

        return engine

    @pytest.mark.asyncio
    async def test_depth_propagation_from_parent_request(self, engine_mock):
        """子 Request 自动继承父请求的 depth + 1"""
        parent = Request(url="https://list.com", meta={'depth': 1})

        async def outputs():
            yield Request(url="https://detail.com")

        await engine_mock._handle_spider_output(outputs(), parent_request=parent)

        # 验证 processor.enqueue 被调用
        engine_mock.processor.enqueue.assert_called_once()
        child_request = engine_mock.processor.enqueue.call_args[0][0]
        assert child_request.meta['depth'] == 2  # parent_depth(1) + 1

    @pytest.mark.asyncio
    async def test_depth_propagation_no_parent(self, engine_mock):
        """没有 parent_request 时，depth 默认为 0+1=1"""
        async def outputs():
            yield Request(url="https://start.com")

        await engine_mock._handle_spider_output(outputs(), parent_request=None)

        child_request = engine_mock.processor.enqueue.call_args[0][0]
        assert child_request.meta['depth'] == 1

    @pytest.mark.asyncio
    async def test_depth_propagation_deep_chain(self, engine_mock):
        """多层级 depth 传播：depth=3 → 子请求 depth=4"""
        parent = Request(url="https://deep.com", meta={'depth': 3})

        async def outputs():
            yield Request(url="https://deeper.com")

        await engine_mock._handle_spider_output(outputs(), parent_request=parent)

        child_request = engine_mock.processor.enqueue.call_args[0][0]
        assert child_request.meta['depth'] == 4

    @pytest.mark.asyncio
    async def test_depth_not_overwritten_if_manual_set(self, engine_mock):
        """子请求手动设置 depth 时，框架不覆盖"""
        parent = Request(url="https://list.com", meta={'depth': 1})

        async def outputs():
            yield Request(url="https://detail.com", meta={'depth': 10})

        await engine_mock._handle_spider_output(outputs(), parent_request=parent)

        child_request = engine_mock.processor.enqueue.call_args[0][0]
        assert child_request.meta['depth'] == 10  # 手动设置的值，不被覆盖

    @pytest.mark.asyncio
    async def test_depth_propagation_parent_meta_missing_depth(self, engine_mock):
        """父请求 meta 中没有 depth 时，默认从 0 开始"""
        parent = Request(url="https://list.com")  # meta 中无 depth

        async def outputs():
            yield Request(url="https://detail.com")

        await engine_mock._handle_spider_output(outputs(), parent_request=parent)

        child_request = engine_mock.processor.enqueue.call_args[0][0]
        assert child_request.meta['depth'] == 1  # 0 + 1

    @pytest.mark.asyncio
    async def test_item_not_affected_by_depth_propagation(self, engine_mock):
        """Item 输出不受 depth 传播影响"""
        parent = Request(url="https://list.com", meta={'depth': 2})

        item = Item(title="test")

        async def outputs():
            yield item

        await engine_mock._handle_spider_output(outputs(), parent_request=parent)

        engine_mock.processor.enqueue.assert_called_once_with(item)

    @pytest.mark.asyncio
    async def test_mixed_outputs_request_and_item(self, engine_mock):
        """混合输出 Request 和 Item，只有 Request 传播 depth"""
        parent = Request(url="https://list.com", meta={'depth': 1})

        item = Item(title="test")
        req = Request(url="https://detail.com")

        async def outputs():
            yield item
            yield req

        await engine_mock._handle_spider_output(outputs(), parent_request=parent)

        assert engine_mock.processor.enqueue.call_count == 2
        # 第二次调用是 Request，depth 应为 2
        request_call = engine_mock.processor.enqueue.call_args_list[1]
        assert request_call[0][0].meta['depth'] == 2

    @pytest.mark.asyncio
    async def test_exception_output_raises(self, engine_mock):
        """Exception 输出应抛出异常"""
        parent = Request(url="https://list.com", meta={'depth': 1})

        async def outputs():
            yield ValueError("test error")

        with pytest.raises(ValueError, match="test error"):
            await engine_mock._handle_spider_output(outputs(), parent_request=parent)

    @pytest.mark.asyncio
    async def test_invalid_output_raises_output_error(self, engine_mock):
        """非法输出类型应抛出 OutputError"""
        parent = Request(url="https://list.com", meta={'depth': 1})

        async def outputs():
            yield "invalid string"

        with pytest.raises(OutputError):
            await engine_mock._handle_spider_output(outputs(), parent_request=parent)

    @pytest.mark.asyncio
    async def test_processor_none_returns_early(self):
        """processor 为 None 时提前返回，不处理输出"""
        from crawlo.core.engine import Engine

        engine = Mock(spec=Engine)
        engine.processor = None
        engine._handle_spider_output = Engine._handle_spider_output.__get__(engine, Engine)

        parent = Request(url="https://list.com", meta={'depth': 1})

        async def outputs():
            yield Request(url="https://detail.com")

        # 不应抛出异常
        await engine._handle_spider_output(outputs(), parent_request=parent)

    @pytest.mark.asyncio
    async def test_multiple_requests_each_get_depth(self, engine_mock):
        """多个子请求都正确传播 depth"""
        parent = Request(url="https://list.com", meta={'depth': 2})

        async def outputs():
            yield Request(url="https://detail1.com")
            yield Request(url="https://detail2.com")
            yield Request(url="https://detail3.com")

        await engine_mock._handle_spider_output(outputs(), parent_request=parent)

        assert engine_mock.processor.enqueue.call_count == 3
        for call in engine_mock.processor.enqueue.call_args_list:
            req = call[0][0]
            assert req.meta['depth'] == 3  # parent_depth(2) + 1


# ============================================================
# 3. _handle_errback_output depth 传播测试
# ============================================================

class TestHandleErrbackOutputDepthPropagation:
    """测试 engine._handle_errback_output 传递 depth"""

    @pytest.fixture
    def engine_mock(self):
        """创建最小化的 Engine mock"""
        from crawlo.core.engine import Engine

        engine = Mock(spec=Engine)
        engine.processor = Mock()
        engine.processor.enqueue = AsyncMock()
        engine.crawler = Mock()
        engine.spider = Mock()
        engine._create_background_task = Mock()

        # 绑定真实方法
        engine._handle_spider_output = Engine._handle_spider_output.__get__(engine, Engine)
        engine._handle_errback_output = Engine._handle_errback_output.__get__(engine, Engine)

        return engine

    @pytest.mark.asyncio
    async def test_errback_single_request_propagates_depth(self, engine_mock):
        """errback 返回单个 Request 时传播 depth"""
        parent = Request(url="https://list.com", meta={'depth': 2})

        retry_request = Request(url="https://list.com/retry")

        await engine_mock._handle_errback_output(retry_request, parent_request=parent)

        engine_mock.processor.enqueue.assert_called_once()
        req = engine_mock.processor.enqueue.call_args[0][0]
        assert req.meta['depth'] == 3  # parent_depth(2) + 1

    @pytest.mark.asyncio
    async def test_errback_list_propagates_depth(self, engine_mock):
        """errback 返回列表时每个 Request 都传播 depth"""
        parent = Request(url="https://list.com", meta={'depth': 1})

        requests = [
            Request(url="https://retry1.com"),
            Request(url="https://retry2.com"),
        ]

        await engine_mock._handle_errback_output(requests, parent_request=parent)

        assert engine_mock.processor.enqueue.call_count == 2
        for call in engine_mock.processor.enqueue.call_args_list:
            req = call[0][0]
            assert req.meta['depth'] == 2

    @pytest.mark.asyncio
    async def test_errback_no_parent_depth_defaults_to_1(self, engine_mock):
        """errback 没有 parent_request 时 depth 默认为 1"""
        retry_request = Request(url="https://retry.com")

        await engine_mock._handle_errback_output(retry_request, parent_request=None)

        req = engine_mock.processor.enqueue.call_args[0][0]
        assert req.meta['depth'] == 1

    @pytest.mark.asyncio
    async def test_errback_item_no_depth(self, engine_mock):
        """errback 返回 Item 时不设置 depth"""
        parent = Request(url="https://list.com", meta={'depth': 2})
        item = Item(title="error_item")

        await engine_mock._handle_errback_output(item, parent_request=parent)

        engine_mock.processor.enqueue.assert_called_once_with(item)

    @pytest.mark.asyncio
    async def test_errback_coroutine_propagates_depth(self, engine_mock):
        """errback 返回协程时也能传播 depth"""
        parent = Request(url="https://list.com", meta={'depth': 3})

        async def async_errback():
            return Request(url="https://retry.com")

        await engine_mock._handle_errback_output(async_errback(), parent_request=parent)

        req = engine_mock.processor.enqueue.call_args[0][0]
        assert req.meta['depth'] == 4

    @pytest.mark.asyncio
    async def test_errback_async_gen_propagates_depth(self, engine_mock):
        """errback 返回异步生成器时传播 depth"""
        parent = Request(url="https://list.com", meta={'depth': 1})

        async def gen():
            yield Request(url="https://retry1.com")
            yield Request(url="https://retry2.com")

        await engine_mock._handle_errback_output(gen(), parent_request=parent)

        assert engine_mock.processor.enqueue.call_count == 2
        for call in engine_mock.processor.enqueue.call_args_list:
            req = call[0][0]
            assert req.meta['depth'] == 2


# ============================================================
# 4. 端到端优先级行为测试
# ============================================================

class TestDepthPriorityBehavior:
    """测试 DEPTH_PRIORITY 与 depth 传播配合后的完整优先级行为"""

    def test_depth_first_with_positive_depth_priority(self):
        """
        DEPTH_PRIORITY = 1（深度优先/先详后列）
        
        列表页: depth=1, 用户priority=0 → 内部 0 - 1*1 = -1
        详情页: depth=2, 用户priority=0 → 内部 0 - 2*1 = -2
        -2 < -1 → 详情页先出队 ✅
        """
        list_req = Request(url="https://list.com", priority=0)
        set_request(list_req, priority=1)

        detail_req = Request(url="https://detail.com", priority=0, meta={'depth': 2})
        set_request(detail_req, priority=1)

        assert detail_req < list_req  # 详情页优先级更高（内部值更小）

    def test_breadth_first_with_negative_depth_priority(self):
        """
        DEPTH_PRIORITY = -1（广度优先/先列后详）
        
        列表页: depth=1, 用户priority=0 → 内部 0 - 1*(-1) = 1
        详情页: depth=2, 用户priority=0 → 内部 0 - 2*(-1) = 2
        1 < 2 → 列表页先出队 ✅
        """
        list_req = Request(url="https://list.com", priority=0)
        set_request(list_req, priority=-1)

        detail_req = Request(url="https://detail.com", priority=0, meta={'depth': 2})
        set_request(detail_req, priority=-1)

        assert list_req < detail_req  # 列表页优先级更高（内部值更小）

    def test_priority_enum_high_overrides_depth(self):
        """
        用户用 RequestPriority.HIGH 设置详情页优先级时
        详情页即使在 depth 调整后仍然优先于列表页
        
        详情页: 用户priority=100 → 内部 -100, depth=2, DEPTH_PRIORITY=1 → -100-2 = -102
        列表页: 用户priority=0 → 内部 0, depth=1, DEPTH_PRIORITY=1 → 0-1 = -1
        -102 < -1 → 详情页先出队 ✅
        """
        list_req = Request(url="https://list.com", priority=0)
        set_request(list_req, priority=1)

        detail_req = Request(url="https://detail.com", priority=RequestPriority.HIGH, meta={'depth': 2})
        set_request(detail_req, priority=1)

        assert detail_req < list_req

    def test_sorting_order_depth_first(self):
        """验证多个请求在深度优先模式下的出队排序"""
        DEPTH_PRIORITY = 1
        requests = []

        # 3 个列表页（depth=1），各产生 2 个详情页（depth=2）
        for i in range(3):
            list_req = Request(url=f"https://list{i}.com", priority=0)
            set_request(list_req, priority=DEPTH_PRIORITY)
            requests.append(list_req)

            for j in range(2):
                detail_req = Request(url=f"https://list{i}/detail{j}.com", priority=0, meta={'depth': 2})
                set_request(detail_req, priority=DEPTH_PRIORITY)
                requests.append(detail_req)

        # 按内部 priority 排序（min-heap 行为）
        sorted_requests = sorted(requests)

        # 所有详情页（priority=-2）应排在列表页（priority=-1）之前
        detail_count = 0
        list_count = 0
        for req in sorted_requests[:6]:  # 前 6 个应该是 6 个详情页
            if req.meta['depth'] == 2:
                detail_count += 1
            else:
                list_count += 1

        assert detail_count == 6  # 所有详情页先出队
        assert list_count == 0

    def test_sorting_order_breadth_first(self):
        """验证多个请求在广度优先模式下的出队排序"""
        DEPTH_PRIORITY = -1
        requests = []

        for i in range(3):
            list_req = Request(url=f"https://list{i}.com", priority=0)
            set_request(list_req, priority=DEPTH_PRIORITY)
            requests.append(list_req)

            for j in range(2):
                detail_req = Request(url=f"https://list{i}/detail{j}.com", priority=0, meta={'depth': 2})
                set_request(detail_req, priority=DEPTH_PRIORITY)
                requests.append(detail_req)

        sorted_requests = sorted(requests)

        # 所有列表页（priority=1）应排在详情页（priority=2）之前
        list_count = 0
        detail_count = 0
        for req in sorted_requests[:3]:
            if req.meta['depth'] == 1:
                list_count += 1
            else:
                detail_count += 1

        assert list_count == 3  # 所有列表页先出队
        assert detail_count == 0

    def test_request_priority_negation(self):
        """验证 Request 构造函数将用户 priority 取反存储"""
        # 用户传入 priority=500 → 内部存储 -500
        r = Request(url="https://example.com", priority=500)
        assert r.priority == -500

        # 用户传入 priority=0 → 内部存储 0
        r2 = Request(url="https://example.com", priority=0)
        assert r2.priority == 0

        # 用户传入 priority=-100 → 内部存储 100
        r3 = Request(url="https://example.com", priority=-100)
        assert r3.priority == 100

    def test_priority_enum_values(self):
        """验证 RequestPriority 枚举值的正确映射"""
        assert RequestPriority.URGENT == 200     # 用户传入 → 内部 -200 → 最先出队
        assert RequestPriority.HIGH == 100       # 用户传入 → 内部 -100 → 第二出队
        assert RequestPriority.NORMAL == 0       # 用户传入 → 内部 0 → 正常
        assert RequestPriority.LOW == -100       # 用户传入 → 内部 100 → 较后出队
        assert RequestPriority.BACKGROUND == -200  # 用户传入 → 内部 200 → 最后出队

    def test_urgent_always_first_with_depth(self):
        """
        即使 depth 较深，URGENT 优先级的请求仍然最优先出队
        
        URGENT + depth=5: 内部 -200 - 5*1 = -205
        NORMAL + depth=1: 内部 0 - 1*1 = -1
        -205 < -1 → URGENT 仍然优先
        """
        normal_list = Request(url="https://list.com", priority=0)
        set_request(normal_list, priority=1)

        urgent_deep = Request(url="https://urgent.com", priority=RequestPriority.URGENT, meta={'depth': 5})
        set_request(urgent_deep, priority=1)

        assert urgent_deep < normal_list


# ============================================================
# 5. set_request 向后兼容性测试
# ============================================================

class TestSetRequestBackwardCompatibility:
    """确保 set_request 修改后向后兼容"""

    def test_start_requests_without_depth(self):
        """start_requests 产生的请求没有 depth，set_request 应设为 1"""
        req = Request(url="https://start.com")
        assert 'depth' not in req.meta
        set_request(req, priority=1)
        assert req.meta['depth'] == 1

    def test_start_requests_priority_adjustment(self):
        """start_requests 的优先级正确调整"""
        req = Request(url="https://start.com", priority=0)
        set_request(req, priority=1)
        # depth=1, 内部 priority=0, 调整后 0 - 1*1 = -1
        assert req.priority == -1

    def test_framework_propagated_depth_not_doubled(self):
        """框架传播的 depth 不被 set_request 重复自增"""
        # 旧逻辑: depth = depth + 1 = 2+1 = 3 ❌
        # 新逻辑: depth 不变 = 2 ✅
        req = Request(url="https://detail.com", meta={'depth': 2})
        set_request(req, priority=1)
        assert req.meta['depth'] == 2  # 不再自增

    def test_depth_zero_in_meta_treated_as_set(self):
        """meta 中 depth=0 视为已设置，不会被默认值覆盖"""
        req = Request(url="https://root.com", meta={'depth': 0})
        set_request(req, priority=1)
        assert req.meta['depth'] == 0  # 保持 0，不设为 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
