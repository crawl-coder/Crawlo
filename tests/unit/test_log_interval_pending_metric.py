#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
LogIntervalExtension pending 指标测试
====================================

验证 Known Limitations 修复：
1. `queue/pending_count` 写入 StatsCollector（供 Prometheus 暴露为
   `crawlo_queue_pending_count` Gauge）；
2. 闲置（无 item/response/queue）但 pending > 0 时**不跳过**——
   pending 积压是最需要观测的信号，不能因"闲置"从指标中消失。
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from crawlo.extensions.log_interval import LogIntervalExtension


class _FakeStats:
    def __init__(self):
        self.values = {}

    def get_value(self, key, default=0):
        return self.values.get(key, default)

    def set_value(self, key, value):
        self.values[key] = value

    def inc_value(self, key, count=1):
        self.values[key] = self.values.get(key, 0) + count


def _make_extension(pending_count: int, queue_size: int):
    settings = MagicMock()
    settings.get.return_value = 1
    settings.get_int.return_value = 0
    crawler = MagicMock()
    crawler.settings = settings
    stats = _FakeStats()
    crawler.stats = stats

    ext = LogIntervalExtension.__new__(LogIntervalExtension)
    ext.crawler = crawler
    ext.stats = stats
    ext.seconds = 1
    ext.interval = 1
    ext.unit = 's'
    ext.interval_display = ''
    ext.item_count = 0
    ext.response_count = 0
    ext._backlog_alert_sent = False
    ext.logger = MagicMock()
    ext._write_p99_metrics = MagicMock()

    # mock 队列查询
    ext._get_queue_size = AsyncMock(return_value=queue_size)
    ext._get_pending_count = AsyncMock(return_value=pending_count)
    ext._get_backpressure_info = AsyncMock(return_value=(False, 0.0, 0.0, 0.0, 'normal'))
    return ext


@pytest.mark.asyncio
async def test_pending_count_written_to_stats():
    """pending_count 必须写入 queue/pending_count 指标。"""
    ext = _make_extension(pending_count=7, queue_size=3)

    # 第一轮后中断循环
    with patch(
        "crawlo.extensions.log_interval.asyncio.sleep",
        side_effect=[None, KeyboardInterrupt()],
    ):
        with pytest.raises(KeyboardInterrupt):
            await ext.interval_log()

    assert ext.stats.values.get('queue/pending_count') == 7, (
        f"期望 pending_count=7 写入指标，实际 {ext.stats.values}"
    )
    assert ext.stats.values.get('queue_size') == 3
    assert ext.stats.values.get('queue/backlog') == 3


@pytest.mark.asyncio
async def test_idle_with_pending_not_skipped():
    """闲置（无产出/队列空）但 pending > 0 时不得跳过，指标必须写入。"""
    ext = _make_extension(pending_count=5, queue_size=0)
    # 无 item/response 增量 → 若 pending==0 会跳过；pending=5 时必须继续
    with patch(
        "crawlo.extensions.log_interval.asyncio.sleep",
        side_effect=[None, KeyboardInterrupt()],
    ):
        with pytest.raises(KeyboardInterrupt):
            await ext.interval_log()

    assert ext.stats.values.get('queue/pending_count') == 5, (
        f"闲置但 pending>0 时应写入指标，实际 {ext.stats.values}"
    )


@pytest.mark.asyncio
async def test_prometheus_metric_name():
    """Prometheus 后端暴露的指标名必须为 crawlo_queue_pending_count。"""
    from crawlo.stats.prometheus_backend import _sanitize_metric_name

    assert _sanitize_metric_name('queue/pending_count', 'crawlo') == 'crawlo_queue_pending_count'
