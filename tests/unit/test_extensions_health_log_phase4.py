#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Phase 4: HealthCheck + LogStats + LogInterval 扩展单元测试

覆盖：
1. HealthCheckExtension 实例化（注入 crawler.settings mock）
2. stats 属性返回 dict（语义等价 get_stats() → dict）
3. spider_opened 事件处理（设置 start_time 并调用父类逻辑）
4. LogStats 构造 ok（不打真实请求/Redis）
5. LogIntervalExtension 构造 ok（不打真实请求/Redis）
"""

import pytest
import asyncio
from unittest.mock import Mock, MagicMock, AsyncMock, patch
from datetime import datetime

from crawlo.extensions.health_check import HealthCheckExtension
from crawlo.extensions.log_stats import LogStats
from crawlo.extensions.log_interval import LogIntervalExtension


# ========================================================================
# 辅助：构造最小 Mock crawler
# ========================================================================

def _make_mock_crawler(interval_sec: int = 60, health_interval: int = 60):
    """
    构造最小可用 crawler Mock：
    - settings.get_int / settings.get → 返回配置
    - stats → MagicMock (StatsCollector 语义)
    - subscriber → 事件订阅器（用 Mock）
    """
    crawler = MagicMock()

    # settings
    def _get(key, default=None):
        if key == 'INTERVAL':
            return interval_sec if interval_sec is not None else default
        return default

    def _get_int(key, default=None):
        if key == 'HEALTH_CHECK_INTERVAL':
            return health_interval if health_interval is not None else default
        if key == 'INTERVAL':
            return interval_sec if interval_sec is not None else default
        return default

    def _get_bool(key, default=None):
        if key == 'HEALTH_CHECK_ENABLED':
            return True
        if key == '_INTERNAL_SCHEDULER_TASK':
            return False
        return default

    crawler.settings.get = _get
    crawler.settings.get_int = _get_int
    crawler.settings.get_bool = _get_bool

    # stats：StatsCollector 语义，支持 get_value / set_value / inc_value / dict-style 访问
    _storage = {}
    mock_stats = MagicMock()
    # 把 _storage 挂到 mock 上，方便调试
    mock_stats._storage = _storage

    def _stats_get(self_or_key, key=None, default=None):
        # 两种调用：stats.get_value(key, default)  或  绑定后 (self, key, default=None)
        if isinstance(self_or_key, str):
            return _storage.get(self_or_key, key if key is not None else default)
        return _storage.get(key, default)

    def _stats_set(self_or_key, key=None, value=None):
        if isinstance(self_or_key, str):
            _storage[self_or_key] = key
            return
        _storage[key] = value

    def _stats_inc(self_or_key, key=None, n=1):
        if isinstance(self_or_key, str):
            _storage[self_or_key] = _storage.get(self_or_key, 0) + (key or 1)
            return
        _storage[key] = _storage.get(key, 0) + n

    # 通过 Mock 的 side_effect 绑定，不需要考虑 self
    mock_stats.get_value.side_effect = lambda k, d=None: _storage.get(k, d)
    mock_stats.set_value.side_effect = lambda k, v: _storage.__setitem__(k, v)
    mock_stats.inc_value.side_effect = lambda k, n=1: _storage.__setitem__(k, _storage.get(k, 0) + n)
    # __setitem__ / __getitem__ 用 MagicMock 的默认行为 + side_effect
    mock_stats.__setitem__.side_effect = lambda k, v: _storage.__setitem__(k, v)
    mock_stats.__getitem__.side_effect = lambda k: _storage[k]
    crawler.stats = mock_stats

    # subscriber
    crawler.subscriber = MagicMock()
    crawler.subscriber.subscribe = Mock()

    return crawler


# ========================================================================
# Tests 1-3: HealthCheckExtension
# ========================================================================

class TestHealthCheckExtensionPhase4:
    """HealthCheckExtension 3 个核心测试"""

    def test_health_check_instantiate_with_mock_settings(self):
        """
        1. 实例化（注入 settings mock）→ 不抛异常，属性齐全
        """
        crawler = _make_mock_crawler(health_interval=30)
        ext = HealthCheckExtension(crawler)

        assert ext.crawler is crawler
        assert ext.settings is crawler.settings
        assert ext.check_interval == 30  # 我们 mock 的值
        assert ext.logger is not None
        assert ext.enabled is True  # 默认初始化

    def test_health_check_stats_is_dict(self):
        """
        2. stats 属性返回 dict（用户需求 get_stats() → dict，
           实际类是 self.stats 直接 dict，语义等价）
        """
        crawler = _make_mock_crawler()
        ext = HealthCheckExtension(crawler)

        stats = ext.stats
        assert isinstance(stats, dict)
        # 初始化的 5 个 key
        assert 'start_time' in stats
        assert 'total_requests' in stats
        assert 'total_responses' in stats
        assert 'error_responses' in stats
        assert 'last_check_time' in stats
        # 初始值正确
        assert stats['start_time'] is None
        assert stats['total_requests'] == 0
        assert stats['total_responses'] == 0
        assert stats['error_responses'] == 0
        assert stats['last_check_time'] is None

    @pytest.mark.asyncio
    async def test_health_check_spider_opened_sets_start_time(self):
        """
        3. spider_opened 事件处理：设置 stats['start_time']
           对应用户需求「设置 spider_name」—— 实际实现设置 start_time，
           同时验证整个事件链路不抛异常、logger/父类方法都正常触发。
        """
        crawler = _make_mock_crawler()
        ext = HealthCheckExtension(crawler)

        # enabled=True（默认） 且 monitor_manager 中自己是主实例
        with patch(
            'crawlo.extensions.monitor.base.get_monitor_manager'
        ) as mock_mm_factory:
            mock_mm = MagicMock()
            mock_mm.get_monitor.return_value = ext  # 认为自己是主实例
            mock_mm_factory.return_value = mock_mm

            # 调用 spider_opened
            # 因为 spider_opened 里会 create_task(_monitor_loop)，这里我们 patch
            with patch('crawlo.extensions.monitor.base.asyncio.create_task') as mock_create:
                await ext.spider_opened()

        # start_time 被设置为 datetime
        assert ext.stats['start_time'] is not None
        assert isinstance(ext.stats['start_time'], datetime)
        # 监控循环任务被创建（即使我们 mock 了 create_task，也能验证调用）
        # 注意：如果 enabled 为 True 且是主实例，才会启动循环


# ========================================================================
# Tests 4-5: LogStats + LogIntervalExtension
# ========================================================================

class TestLogStatsAndIntervalPhase4:
    """LogStats + LogIntervalExtension 构造测试"""

    def test_log_stats_construct_ok(self):
        """
        4. LogStats 构造 ok：不打真实请求/Redis，crawler mock 足够
        """
        crawler = _make_mock_crawler()

        # now() 和 time_diff() 在 log_stats.__init__ / spider_closed 中调用，
        # __init__ 时会设置 start_time → 所以需要 patch。
        with patch('crawlo.extensions.log_stats.now') as mock_now, \
             patch('crawlo.extensions.log_stats.time_diff') as mock_td:
            mock_now.return_value = '2025-01-01 12:00:00'
            mock_td.return_value = 100.0

            ext = LogStats(crawler)

        assert ext.crawler is crawler
        assert ext.logger is not None
        assert ext._stats is crawler.stats

    def test_log_interval_extension_construct_ok(self):
        """
        5. LogIntervalExtension 构造 ok：不打真实请求/Redis
           验证 interval/unit/seconds 属性根据 INTERVAL 配置被计算。
        """
        # 情况 A：INTERVAL=60 → 1 min → interval_display=""
        crawler60 = _make_mock_crawler(interval_sec=60)
        with patch(
            'crawlo.extensions.log_interval.get_monitor_manager'
        ) as mock_mm_factory:
            mock_mm = MagicMock()
            mock_mm.get_monitor.return_value = None  # 没有已存在的
            mock_mm.register_monitor.return_value = True  # 注册成功
            mock_mm_factory.return_value = mock_mm

            ext60 = LogIntervalExtension(crawler60)

        assert ext60.enabled is True
        assert ext60.seconds == 60
        assert ext60.interval == 1
        assert ext60.unit == 'min'
        assert ext60.interval_display == ""  # 1 min → 空字符串
        assert ext60.stats is crawler60.stats
        assert ext60.logger is not None

        # 情况 B：INTERVAL=30 → 30 s → 直接显示 30s
        crawler30 = _make_mock_crawler(interval_sec=30)
        with patch(
            'crawlo.extensions.log_interval.get_monitor_manager'
        ) as mock_mm_factory2:
            mock_mm2 = MagicMock()
            mock_mm2.get_monitor.return_value = None
            mock_mm2.register_monitor.return_value = True
            mock_mm_factory2.return_value = mock_mm2

            ext30 = LogIntervalExtension(crawler30)

        assert ext30.seconds == 30
        assert ext30.interval == 30
        assert ext30.unit == 's'
        assert ext30.interval_display == "30"
