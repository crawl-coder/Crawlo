#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
MySQL Monitor Extension
Monitor MySQL connection pool and execution performance
"""
import asyncio
from typing import Any, Optional, Dict, Tuple

from .monitor.base import BaseMonitorExtension
from crawlo.utils.db.mysql_connection_pool import MySQLConnectionPoolManager


class MySQLMonitorExtension(BaseMonitorExtension):
    """
    MySQL Monitor Extension
    Monitor MySQL connection pool status and SQL execution performance
    """

    monitor_id = 'mysql_monitor'
    config_key = 'MYSQL_MONITOR_ENABLED'
    default_enabled = False

    def __init__(self, crawler: Any):
        super().__init__(crawler)

        self.interval = self.settings.get_int('MYSQL_MONITOR_INTERVAL', 60)
        # 连接池使用趋势追踪
        self.pool_usage_history: list = []
        self.max_history_points = 50

        if self.enabled:
            self.logger.info(f"MySQL monitor initialized. Interval: {self.interval}s")

    # ---- spider_closed 清理 ----

    def _on_spider_closed_cleanup(self) -> None:
        """清除趋势历史，防止跨周期数据累积"""
        self.pool_usage_history.clear()

    # ---- 监控循环 ----

    async def _monitor_loop(self) -> None:
        """MySQL monitoring loop – monitor connection pool resource leaks and performance metrics"""
        while True:
            try:
                pool_usage = self.crawler.stats.get_value('mysql/pool_usage_percent', 0)
                self.pool_usage_history.append(pool_usage)
                if len(self.pool_usage_history) > self.max_history_points:
                    self.pool_usage_history.pop(0)

                if len(self.pool_usage_history) >= 5:
                    trend_slope, is_increasing = self._calculate_pool_trend()
                    if is_increasing:
                        self.logger.warning(
                            f"MySQL connection pool leak warning – usage continuously increasing: "
                            f"{trend_slope:+.2f}%/check, current: {pool_usage:.2f}%"
                        )

                self._collect_performance_metrics()
                await asyncio.sleep(self.interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"MySQL monitoring error: {e}")
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

    def _collect_performance_metrics(self) -> Dict[str, Any]:
        """Collect MySQL performance metrics (for resource leak analysis)"""
        stats = self.crawler.stats
        metrics = {
            'pool_usage': stats.get_value('mysql/pool_usage_percent', 0),
            'connection_acquire_time': stats.get_value('mysql/connection_acquire_time', 0),
            'sql_execution_time': stats.get_value('mysql/sql_execution_time', 0),
            'batch_execution_time': stats.get_value('mysql/batch_execution_time', 0),
            'insert_success': stats.get_value('mysql/insert_success', 0),
            'insert_failed': stats.get_value('mysql/insert_failed', 0),
            'rows_requested': stats.get_value('mysql/rows_requested', 0),
            'rows_affected': stats.get_value('mysql/rows_affected', 0),
            'rows_ignored': stats.get_value('mysql/rows_ignored_by_duplicate', 0),
            'retry_count': stats.get_value('mysql/retry_count', 0),
            'batch_retry_count': stats.get_value('mysql/batch_retry_count', 0),
            'batch_failure_count': stats.get_value('mysql/batch_failure_count', 0),
            'batch_insert_success': stats.get_value('mysql/batch_insert_success', 0),
        }

        total_ops = metrics['insert_success'] + metrics['insert_failed']
        metrics['failure_rate'] = (metrics['insert_failed'] / total_ops * 100) if total_ops > 0 else 0

        total_batches = metrics['batch_insert_success'] + metrics['batch_failure_count']
        metrics['retry_rate'] = (metrics['batch_retry_count'] / total_batches * 100) if total_batches > 0 else 0

        if metrics['failure_rate'] > 10:
            self.logger.warning(
                f"MySQL high failure rate – {metrics['failure_rate']:.1f}%, "
                f"success: {metrics['insert_success']}, failed: {metrics['insert_failed']}"
            )
        if metrics['retry_rate'] > 20:
            self.logger.warning(
                f"MySQL high retry rate – {metrics['retry_rate']:.1f}%, "
                f"retries: {metrics['batch_retry_count']}"
            )
        if metrics['connection_acquire_time'] > 5:
            self.logger.warning(
                f"MySQL connection acquire delay too high – {metrics['connection_acquire_time']:.2f}s, "
                f"pool usage: {metrics['pool_usage']:.1f}%"
            )

        self._check_detailed_pool_status()
        return metrics

    def _check_detailed_pool_status(self) -> None:
        """Check detailed MySQL connection pool status"""
        mysql_stats = MySQLConnectionPoolManager.get_pool_stats()
        all_pools = mysql_stats.get('pools', {})
        if not all_pools:
            return

        for pool_key, pool_info in all_pools.items():
            usage_pct = pool_info.get('usage_percent', 0)
            freesize = pool_info.get('freesize', 0)
            maxsize = pool_info.get('maxsize', 0)
            size = pool_info.get('size', 0)
            minsize = pool_info.get('minsize', 0)

            if usage_pct > 90:
                self.logger.warning(
                    f"MySQL pool [{pool_key}] usage too high – "
                    f"used: {pool_info.get('used',0)}/{maxsize} ({usage_pct:.1f}%), "
                    f"free: {freesize}, min: {minsize}"
                )
            if freesize == 0 and usage_pct >= 100:
                self.logger.warning(
                    f"MySQL pool [{pool_key}] exhausted – all {maxsize} connections in use"
                )
            if size < minsize:
                self.logger.warning(
                    f"MySQL pool [{pool_key}] below minimum – current: {size}, min: {minsize}"
                )


def create_mysql_monitor(crawler: Any) -> Optional[MySQLMonitorExtension]:
    """便捷函数：创建 MySQL 监控器（如果启用）"""
    if crawler.settings.get_bool('MYSQL_MONITOR_ENABLED', False):
        return MySQLMonitorExtension(crawler)
    return None
