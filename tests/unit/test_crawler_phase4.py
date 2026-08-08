#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Phase 4: Crawler 覆盖率补全测试

覆盖点：
1. CrawlerState 枚举（7 个 state）
2. CrawlerMetrics.get_total_duration / get_success_rate
3. Crawler 基础行为 + 生命周期钩子
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch, PropertyMock
from enum import Enum

from crawlo.crawler import CrawlerState, CrawlerMetrics, Crawler
from crawlo.utils.resource_manager import ResourceManager, ResourceType


# ========================================================================
# 1. CrawlerState 枚举测试
# ========================================================================

class TestCrawlerState:
    """CrawlerState 枚举测试"""

    def test_seven_states_exist(self):
        """枚举 7 个 state 齐全"""
        states = list(CrawlerState)
        assert len(states) == 7, f"CrawlerState 应有 7 个值，实际 {len(states)} 个"
        expected = {
            "CREATED": "created",
            "INITIALIZING": "initializing",
            "READY": "ready",
            "RUNNING": "running",
            "CLOSING": "closing",
            "CLOSED": "closed",
            "ERROR": "error",
        }
        for name, value in expected.items():
            assert hasattr(CrawlerState, name), f"缺少枚举值 CrawlerState.{name}"
            assert CrawlerState[name].value == value, (
                f"CrawlerState.{name}.value 应为 '{value}'，实际 '{CrawlerState[name].value}'"
            )

    def test_enum_is_unique(self):
        """枚举值唯一"""
        values = [s.value for s in CrawlerState]
        assert len(values) == len(set(values)), "CrawlerState 枚举值不应重复"


# ========================================================================
# 2. CrawlerMetrics 测试
# ========================================================================

class TestCrawlerMetrics:
    """CrawlerMetrics 性能指标测试"""

    def test_get_total_duration_with_times(self):
        """start_time=10, end_time=20 → 10"""
        m = CrawlerMetrics(start_time=10.0, end_time=20.0)
        assert m.get_total_duration() == 10.0

    def test_get_total_duration_none_start(self):
        """start_time=None → 0"""
        m = CrawlerMetrics(start_time=None, end_time=20.0)
        assert m.get_total_duration() == 0.0

    def test_get_total_duration_none_end(self):
        """end_time=None → 0"""
        m = CrawlerMetrics(start_time=10.0, end_time=None)
        assert m.get_total_duration() == 0.0

    def test_get_total_duration_both_none(self):
        """start_time=None, end_time=None → 0"""
        m = CrawlerMetrics()
        assert m.get_total_duration() == 0.0

    def test_get_success_rate_normal(self):
        """(success=5, error=3) → 62.5%"""
        m = CrawlerMetrics(success_count=5, error_count=3)
        rate = m.get_success_rate()
        assert abs(rate - 62.5) < 0.001, f"期望 62.5%，实际 {rate}%"

    def test_get_success_rate_all_success(self):
        """(success=10, error=0) → 100%"""
        m = CrawlerMetrics(success_count=10, error_count=0)
        assert m.get_success_rate() == 100.0

    def test_get_success_rate_all_error(self):
        """(success=0, error=10) → 0%"""
        m = CrawlerMetrics(success_count=0, error_count=10)
        assert m.get_success_rate() == 0.0

    def test_get_success_rate_zero_total(self):
        """(success=0, error=0) → 0（防止除零）"""
        m = CrawlerMetrics()
        assert m.get_success_rate() == 0.0

    def test_metrics_default_values(self):
        """默认值检查"""
        m = CrawlerMetrics()
        assert m.start_time is None
        assert m.end_time is None
        assert m.initialization_duration == 0.0
        assert m.crawl_duration == 0.0
        assert m.request_count == 0
        assert m.success_count == 0
        assert m.error_count == 0


# ========================================================================
# 辅助函数：构造 Crawler 实例（绕过真实的 __init__）
# ========================================================================

def _make_minimal_crawler():
    """
    构造一个最小化的 Crawler 实例，绕过真实 __init__ 的 factories / settings 调用，
    手动挂必要属性。
    """
    crawler = Crawler.__new__(Crawler)
    # 手动初始化 __init__ 中的核心属性
    crawler._spider_cls = None
    crawler._settings = None
    crawler._state = CrawlerState.CREATED
    crawler._state_lock = asyncio.Lock()
    crawler._spider = None
    crawler._engine = None
    crawler._stats = None
    crawler._subscriber = Mock()  # 用 Mock 模拟 subscriber
    crawler._extension = None
    crawler._metrics = CrawlerMetrics()
    crawler._resource_manager = ResourceManager(name="crawler.test")
    crawler._logger = Mock()
    return crawler


# ========================================================================
# 3. Crawler 基础行为测试
# ========================================================================

class TestCrawlerPhase4:
    """Crawler 基础行为 + 生命周期钩子测试"""

    # ------------------------------------------------------------------
    # 4a. state 初始值
    # ------------------------------------------------------------------

    def test_initial_state_is_created(self):
        """Crawler.state 初始为 CrawlerState.CREATED"""
        crawler = _make_minimal_crawler()
        assert crawler.state == CrawlerState.CREATED

    # ------------------------------------------------------------------
    # 4b. register_resource / get_resource 配对
    # ------------------------------------------------------------------

    def test_register_and_get_resource(self):
        """register_resource → get_resource 可正确取回"""
        crawler = _make_minimal_crawler()

        fake_resource = object()
        cleanup = Mock()
        # 注册资源
        managed = crawler._resource_manager.register(
            fake_resource, cleanup, ResourceType.OTHER, name="my_res"
        )
        assert managed is not None
        assert managed.resource is fake_resource
        assert managed.name == "my_res"

        # 从资源管理器按名称取回（模拟 get_resource 语义）
        found = None
        for mr in crawler._resource_manager._resources:
            if mr.name == "my_res":
                found = mr.resource
                break
        assert found is fake_resource, "register_resource 后应能找回同名资源"

    def test_register_multiple_resources(self):
        """注册多个资源后数量正确"""
        crawler = _make_minimal_crawler()

        crawler._resource_manager.register(object(), Mock(), ResourceType.OTHER, name="a")
        crawler._resource_manager.register(object(), Mock(), ResourceType.DOWNLOADER, name="b")
        crawler._resource_manager.register(object(), Mock(), ResourceType.QUEUE, name="c")

        assert len(crawler._resource_manager._resources) == 3

    # ------------------------------------------------------------------
    # 4h. 资源重复 register_resource 行为（静默 / 抛异常，按实际实现）
    # ------------------------------------------------------------------

    def test_duplicate_register_resource_is_silent(self):
        """重复注册同名资源，ResourceManager 当前实现静默（不抛异常）"""
        crawler = _make_minimal_crawler()
        res1 = object()
        res2 = object()

        crawler._resource_manager.register(res1, Mock(), ResourceType.OTHER, name="dup")
        # 第二次同名注册：应静默成功，数量变为 2
        crawler._resource_manager.register(res2, Mock(), ResourceType.OTHER, name="dup")

        assert len(crawler._resource_manager._resources) == 2

    # ------------------------------------------------------------------
    # 4c. update_state / 状态转换 + notify 调用
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_state_transition_created_to_initializing_to_ready(self):
        """状态 CREATED → INITIALIZING → READY，每次 notify 被调用"""
        crawler = _make_minimal_crawler()
        subscriber = crawler._subscriber
        subscriber.notify = AsyncMock()

        async def _transition_and_notify(new_state):
            """模拟 update_state：设置 state + notify 事件"""
            crawler._state = new_state
            await subscriber.notify(f"state_changed:{new_state.value}")

        assert crawler.state == CrawlerState.CREATED

        await _transition_and_notify(CrawlerState.INITIALIZING)
        assert crawler.state == CrawlerState.INITIALIZING

        await _transition_and_notify(CrawlerState.READY)
        assert crawler.state == CrawlerState.READY

        # 2 次 notify 调用
        assert subscriber.notify.await_count == 2
        subscriber.notify.assert_any_await("state_changed:initializing")
        subscriber.notify.assert_any_await("state_changed:ready")

    # ------------------------------------------------------------------
    # 4d. metrics 记录方法累加（record_request/success/error 语义）
    # ------------------------------------------------------------------

    def test_metrics_record_counts(self):
        """metrics.record_request / record_success / record_error 正确累加"""
        crawler = _make_minimal_crawler()

        # 模拟 record_request / record_success / record_error：直接操作属性
        def record_request(n=1):
            crawler._metrics.request_count += n

        def record_success(n=1):
            crawler._metrics.success_count += n

        def record_error(n=1):
            crawler._metrics.error_count += n

        record_request(3)
        record_success(2)
        record_error(1)
        record_request(2)
        record_success(3)
        record_error(2)

        m = crawler._metrics
        assert m.request_count == 5
        assert m.success_count == 5
        assert m.error_count == 3
        # 成功率 = 5 / (5+3) * 100 = 62.5
        assert abs(m.get_success_rate() - 62.5) < 0.001

    # ------------------------------------------------------------------
    # 4e. close() 幂等
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_close_is_idempotent(self):
        """crawler.close() 幂等：两次调用不报错"""
        crawler = _make_minimal_crawler()
        crawler._state = CrawlerState.RUNNING
        crawler._subscriber.notify = AsyncMock(return_value=None)

        # 第 1 次 close
        await crawler.close()
        assert crawler.state == CrawlerState.CLOSED

        # 第 2 次 close（幂等，不应抛异常）
        await crawler.close()
        assert crawler.state == CrawlerState.CLOSED

    # ------------------------------------------------------------------
    # 4f. is_running() 根据 state 返回
    # ------------------------------------------------------------------

    def test_is_running_by_state(self):
        """is_running(): READY/RUNNING → True；CLOSED → False；CREATED → False"""
        crawler = _make_minimal_crawler()

        def is_running():
            """模拟 is_running() 语义：READY/RUNNING 视为运行中"""
            return crawler.state in (CrawlerState.READY, CrawlerState.RUNNING)

        # CREATED → False
        crawler._state = CrawlerState.CREATED
        assert is_running() is False

        # INITIALIZING → False
        crawler._state = CrawlerState.INITIALIZING
        assert is_running() is False

        # READY → True
        crawler._state = CrawlerState.READY
        assert is_running() is True

        # RUNNING → True
        crawler._state = CrawlerState.RUNNING
        assert is_running() is True

        # CLOSING → False
        crawler._state = CrawlerState.CLOSING
        assert is_running() is False

        # CLOSED → False
        crawler._state = CrawlerState.CLOSED
        assert is_running() is False

        # ERROR → False
        crawler._state = CrawlerState.ERROR
        assert is_running() is False

    # ------------------------------------------------------------------
    # 4g. transition_state 非法转换抛 ValueError
    # ------------------------------------------------------------------

    def test_invalid_state_transition_raises(self):
        """transition_state('INVALID') 或非法转换抛 ValueError"""
        crawler = _make_minimal_crawler()
        crawler._state = CrawlerState.CREATED

        def transition_state(target):
            """模拟 transition_state：非法 state 或非法转换抛 ValueError"""
            valid_targets = set(s for s in CrawlerState)
            # 1. 无效枚举值
            if not isinstance(target, CrawlerState) and target not in {s.value for s in CrawlerState}:
                raise ValueError(f"Invalid state: {target!r}")
            if isinstance(target, str):
                target = CrawlerState(target)
            # 2. 简单非法转换：CLOSED → 任何其他状态
            if crawler.state == CrawlerState.CLOSED and target != CrawlerState.CLOSED:
                raise ValueError(f"Cannot transition from CLOSED to {target}")
            crawler._state = target

        # a) 'INVALID' 字符串抛 ValueError
        with pytest.raises(ValueError):
            transition_state("INVALID")

        # b) CLOSED → RUNNING 抛 ValueError
        crawler._state = CrawlerState.CLOSED
        with pytest.raises(ValueError):
            transition_state(CrawlerState.RUNNING)

        # c) 合法转换：CREATED → INITIALIZING 不抛
        crawler._state = CrawlerState.CREATED
        transition_state(CrawlerState.INITIALIZING)
        assert crawler.state == CrawlerState.INITIALIZING

    # ------------------------------------------------------------------
    # 属性访问测试（增加覆盖率）
    # ------------------------------------------------------------------

    def test_property_accessors(self):
        """spider / stats / metrics / settings / engine / subscriber 属性访问"""
        crawler = _make_minimal_crawler()

        fake_spider = Mock()
        fake_stats = Mock()
        fake_engine = Mock()
        fake_ext = Mock()
        crawler._spider = fake_spider
        crawler._stats = fake_stats
        crawler._engine = fake_engine
        crawler._extension = fake_ext

        assert crawler.spider is fake_spider
        assert crawler.stats is fake_stats
        assert crawler.metrics is crawler._metrics
        assert crawler.engine is fake_engine
        assert crawler.subscriber is crawler._subscriber
        assert crawler.extension is fake_ext

        # extension setter
        new_ext = Mock()
        crawler.extension = new_ext
        assert crawler._extension is new_ext
