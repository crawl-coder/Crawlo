#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
Memory Monitor Extension
Monitor process memory usage and memory leak trends
"""
import asyncio
import psutil
from typing import Any, Optional

from .monitor.base import BaseMonitorExtension


class MemoryMonitorExtension(BaseMonitorExtension):
    """
    内存监控扩展
    监控进程内存使用情况和内存泄露趋势
    """

    monitor_id = 'memory_monitor'
    config_key = 'MEMORY_MONITOR_ENABLED'
    default_enabled = False

    def __init__(self, crawler: Any):
        super().__init__(crawler)

        self.interval = self.settings.get_int('MEMORY_MONITOR_INTERVAL', 60)
        self.warning_threshold = self.settings.get_float('MEMORY_WARNING_THRESHOLD', 80.0)
        self.critical_threshold = self.settings.get_float('MEMORY_CRITICAL_THRESHOLD', 90.0)
        self.min_trend_points = self.settings.get_int('MEMORY_MIN_TREND_POINTS', 3)
        self.leak_threshold_mb = self.settings.get_float('MEMORY_LEAK_THRESHOLD_MB', 5.0)
        self.stable_threshold_pct = self.settings.get_float('MEMORY_STABLE_THRESHOLD_PCT', 2.0)

        # 内存使用趋势追踪
        self.memory_history: list = []
        self.max_history_points = 100
        # 内存基准线管理
        self.initial_memory: Optional[int] = None
        self.baseline_memory: Optional[float] = None
        self.baseline_established: bool = False

        if self.enabled:
            self.logger.info(
                f"Memory monitor initialized. Interval: {self.interval}s, "
                f"Warning: {self.warning_threshold}%, Critical: {self.critical_threshold}%"
            )

    # ---- spider_closed 清理 ----

    def _on_spider_closed_cleanup(self) -> None:
        """清除历史数据并重置基准线，防止跨周期数据累积"""
        self.memory_history.clear()
        self.initial_memory = None
        self.baseline_memory = None
        self.baseline_established = False

    # ---- 监控循环 ----

    async def _monitor_loop(self) -> None:
        """内存监控循环"""
        while True:
            try:
                system_memory = psutil.virtual_memory()
                system_percent = system_memory.percent

                process = psutil.Process()
                process_memory_info = process.memory_info()
                process_rss = process_memory_info.rss
                process_vms = process_memory_info.vms
                process_percent = process.memory_percent()
                thread_count = process.num_threads()

                if self.initial_memory is None:
                    self.initial_memory = process_rss
                    self.logger.info(f"Initial memory recorded: {process_rss / 1024 / 1024:.2f}MB")

                self.memory_history.append({
                    'timestamp': asyncio.get_event_loop().time(),
                    'rss': process_rss, 'vms': process_vms,
                    'percent': process_percent, 'threads': thread_count,
                })
                if len(self.memory_history) > self.max_history_points:
                    self.memory_history.pop(0)

                self._establish_baseline(process_rss)

                trend_slope, is_increasing, trend_status = self._calculate_memory_trend()

                # 将内存指标写入 StatsCollector，供 Prometheus 等后端暴露
                try:
                    self.crawler.stats.set_value(
                        'memory_rss_mb', round(process_rss / 1024 / 1024, 2)
                    )
                    self.crawler.stats.set_value(
                        'memory_percent', round(process_percent, 2)
                    )
                    self.crawler.stats.set_value('thread_count', thread_count)
                except Exception:
                    pass

                if system_percent > 0 or process_percent > 0:
                    issues = self._detect_issues(process_percent, process_rss, is_increasing, trend_slope, thread_count)
                    self._log_memory_status(process_rss, process_vms, process_percent, thread_count,
                                            system_percent, trend_slope, trend_status, issues)

                await asyncio.sleep(self.interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in memory monitoring: {e}")
                await asyncio.sleep(self.interval)

    # ---- 内存分析辅助方法 ----

    def _establish_baseline(self, process_rss: int) -> None:
        """尝试建立内存基准线"""
        if self.baseline_established or len(self.memory_history) < 5:
            return
        recent_rss = [p['rss'] for p in self.memory_history[-5:]]
        avg_rss = sum(recent_rss) / len(recent_rss)
        if avg_rss > 0:
            fluctuation = (max(recent_rss) - min(recent_rss)) / avg_rss * 100
            if fluctuation < self.stable_threshold_pct:
                self.baseline_memory = avg_rss
                self.baseline_established = True
                self.logger.info(f"Memory baseline established: {self.baseline_memory / 1024 / 1024:.2f}MB")

    def _calculate_memory_trend(self) -> tuple:
        """计算内存使用趋势（线性回归）"""
        if len(self.memory_history) < self.min_trend_points:
            return 0.0, False, "INSUFFICIENT_DATA"

        recent_points = min(len(self.memory_history), 5)
        recent_data = self.memory_history[-recent_points:]

        n = len(recent_data)
        sum_x = sum(range(n))
        sum_y = sum(p['rss'] for p in recent_data)
        sum_xy = sum(i * p['rss'] for i, p in enumerate(recent_data))
        sum_x2 = sum(i * i for i in range(n))

        if n * sum_x2 - sum_x * sum_x == 0:
            return 0.0, False, "STABLE"

        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
        slope_mb = slope / (1024 * 1024)
        is_increasing = slope_mb > self.leak_threshold_mb

        if not is_increasing and abs(slope_mb) < self.stable_threshold_pct:
            trend_status = "STABLE"
        elif is_increasing:
            trend_status = "GROWING"
        else:
            trend_status = "DECREASING"

        return slope, is_increasing, trend_status

    def _detect_issues(self, process_percent: float, process_rss: int,
                       is_increasing: bool, trend_slope: float,
                       thread_count: int) -> list:
        """检测内存相关问题"""
        issues = []

        if process_percent > self.critical_threshold:
            issues.append(f"PROCESS CRITICAL ({process_percent:.2f}%)")
        elif process_percent > self.warning_threshold:
            issues.append(f"PROCESS WARNING ({process_percent:.2f}%)")

        if is_increasing and len(self.memory_history) >= self.min_trend_points:
            if self.baseline_established:
                baseline_increase = (process_rss - self.baseline_memory) / (1024 * 1024)  # type: ignore
                if baseline_increase > self.leak_threshold_mb:
                    avg_growth = (trend_slope / (1024 * 1024)) * self.interval
                    issues.append(f"MEMORY LEAK TREND ({avg_growth:.2f}MB/s)")
            else:
                initial_increase = (process_rss - self.initial_memory) / (1024 * 1024)  # type: ignore
                if initial_increase > 50:
                    self.logger.info(f"Initial memory growth: +{initial_increase:.2f}MB (establishing baseline)")

        if len(self.memory_history) > 1:
            initial_threads = self.memory_history[0]['threads']
            if thread_count > initial_threads * 2 and thread_count > 10:
                issues.append(f"THREAD LEAK ({initial_threads}->{thread_count})")

        return issues

    def _log_memory_status(self, process_rss: int, process_vms: int,
                           process_percent: float, thread_count: int,
                           system_percent: float, trend_slope: float,
                           trend_status: str, issues: list) -> None:
        """记录内存状态日志"""
        issue_status = f" [ISSUES: {', '.join(issues)}]" if issues else " [OK]"

        if trend_status == "GROWING":
            trend_desc = f"GROWING({trend_slope/(1024*1024):+.2f}MB/check)"
        elif trend_status == "DECREASING":
            trend_desc = f"DECREASING({trend_slope/(1024*1024):+.2f}MB/check)"
        else:
            trend_desc = "STABLE"

        baseline_info = ""
        if self.baseline_established and self.baseline_memory:
            baseline_diff = (process_rss - self.baseline_memory) / (1024 * 1024)
            baseline_info = f", Baseline: {self.baseline_memory / 1024 / 1024:.2f}MB ({baseline_diff:+.2f}MB)"

        self.logger.info(
            f"Project Memory Tracker{issue_status} - "
            f"Process: {process_percent:.2f}%, "
            f"RSS: {process_rss / 1024 / 1024:.2f}MB, "
            f"Trend: {trend_desc}{baseline_info}, "
            f"Threads: {thread_count}, "
            f"System: {system_percent:.2f}%"
        )

        critical_issues = [i for i in issues if 'CRITICAL' in i or 'LEAK' in i]
        warning_issues = [i for i in issues if 'WARNING' in i and 'CRITICAL' not in i]
        if critical_issues:
            self.logger.error(f"Critical Memory Issues: {', '.join(critical_issues)}")
        elif warning_issues:
            self.logger.warning(f"Memory Warnings: {', '.join(warning_issues)}")


def create_memory_monitor(crawler: Any) -> Optional[MemoryMonitorExtension]:
    """便捷函数：创建内存监控器（如果启用）"""
    if crawler.settings.get_bool('MEMORY_MONITOR_ENABLED', False):
        return MemoryMonitorExtension(crawler)
    return None
