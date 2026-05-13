#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
Redis Monitor Extension
Monitor Redis connection pool and performance
"""
import asyncio
from typing import Any, Optional, Tuple

from crawlo.event import CrawlerEvent
from .monitor.base import BaseMonitorExtension


class RedisMonitorExtension(BaseMonitorExtension):
    """
    Redis Monitor Extension
    Monitor Redis connection pool status and performance
    """

    monitor_id = 'redis_monitor'
    config_key = 'REDIS_MONITOR_ENABLED'
    default_enabled = False

    def __init__(self, crawler: Any):
        super().__init__(crawler)

        self.interval = self.settings.get_int('REDIS_MONITOR_INTERVAL', 60)
        # 连接池使用趋势追踪
        self.pool_usage_history: list = []
        self.max_history_points = 50

        if self.enabled:
            self.logger.info(f"Redis monitor initialized. Interval: {self.interval}s")

    # ---- spider_closed 清理 ----

    def _on_spider_closed_cleanup(self) -> None:
        """清除趋势历史，防止跨周期数据累积"""
        self.pool_usage_history.clear()

    # ---- 监控循环 ----

    async def _monitor_loop(self) -> None:
        """Redis monitoring loop – monitor connection pool resource leaks"""
        while True:
            try:
                connections_used = self.crawler.stats.get_value('redis/connections_used', 0)
                pool_size = self.crawler.stats.get_value('redis/pool_size', 10)
                pool_usage = (connections_used / pool_size * 100) if pool_size > 0 else 0

                self.pool_usage_history.append(pool_usage)
                if len(self.pool_usage_history) > self.max_history_points:
                    self.pool_usage_history.pop(0)

                if len(self.pool_usage_history) >= 5:
                    trend_slope, is_increasing = self._calculate_pool_trend()
                    if is_increasing:
                        self.logger.warning(
                            f"Redis connection pool leak warning – usage continuously increasing: "
                            f"{trend_slope:+.2f}%/check, current: {pool_usage:.2f}%"
                        )

                await asyncio.sleep(self.interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Redis monitoring error: {e}")
                await asyncio.sleep(self.interval)

    def _calculate_pool_trend(self) -> Tuple[float, bool]:
        """Calculate connection pool usage trend (linear regression)"""
        recent_points = min(len(self.pool_usage_history), 10)
        recent_data = self.pool_usage_history[-recent_points:]

        n = len(recent_data)
        sum_x = sum(range(n))
        sum_y = sum(recent_data)
        sum_xy = sum(i * val for i, val in enumerate(recent_data))
        sum_x2 = sum(i * i for i in range(n))

        if n * sum_x2 - sum_x * sum_x == 0:
            return 0.0, False

        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
        return slope, slope > 0.5


def create_redis_monitor(crawler: Any) -> Optional[RedisMonitorExtension]:
    """便捷函数：创建 Redis 监控器（如果启用）"""
    if crawler.settings.get_bool('REDIS_MONITOR_ENABLED', False):
        return RedisMonitorExtension(crawler)
    return None
