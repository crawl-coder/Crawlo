#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
内存监控扩展
监控进程内存使用情况
"""
import asyncio
import psutil
from typing import Any, Optional

from crawlo.logging import get_logger
from crawlo.event import CrawlerEvent
from crawlo.utils.monitor_manager import monitor_manager


class MemoryMonitorExtension:
    """
    内存监控扩展
    监控进程内存使用情况和内存泄露趋势
    """

    def __init__(self, crawler: Any):
        self.task: Optional[asyncio.Task] = None
        self.crawler = crawler
        self.settings = crawler.settings
        self.logger = get_logger(self.__class__.__name__)
        
        # 获取配置参数
        self.interval = self.settings.get_int('MEMORY_MONITOR_INTERVAL', 30)  # 默认30秒检查一次
        self.warning_threshold = self.settings.get_float('MEMORY_WARNING_THRESHOLD', 70.0)  # 默认70%
        self.critical_threshold = self.settings.get_float('MEMORY_CRITICAL_THRESHOLD', 85.0)  # 默认85%
        self.enabled = self.settings.get_bool('MEMORY_MONITOR_ENABLED', False)
        
        # 监控管理器
        self.monitor_manager = monitor_manager
        
        # 内存使用趋势追踪
        self.memory_history = []  # 存储内存使用历史
        self.max_history_points = 100  # 最大历史记录点数
        
        if self.enabled:
            self.logger.info(f"Memory monitor initialized. Interval: {self.interval}s, Warning: {self.warning_threshold}%, Critical: {self.critical_threshold}%")

    @classmethod
    def create_instance(cls, crawler: Any) -> 'MemoryMonitorExtension':
        # 只有当配置启用时才创建实例
        if not crawler.settings.get_bool('MEMORY_MONITOR_ENABLED', False):
            from crawlo.exceptions import NotConfigured
            from crawlo.logging import get_logger
            logger = get_logger(cls.__name__)
            # 使用debug级别日志，避免在正常情况下产生错误日志
            logger.debug("MemoryMonitorExtension: MEMORY_MONITOR_ENABLED is False, skipping initialization")
            raise NotConfigured("MemoryMonitorExtension: MEMORY_MONITOR_ENABLED is False")
        
        # 检查是否已有内存监控实例在运行
        existing_monitor = monitor_manager.get_monitor('memory_monitor')
        if existing_monitor is not None:
            # 如果已有实例在运行，返回一个不执行任何操作的实例
            o = cls(crawler)
            o.enabled = False  # 禁用此实例的实际监控功能
            return o
        
        o = cls(crawler)
        # 注册监控实例到管理器
        registered = monitor_manager.register_monitor('memory_monitor', o)
        if registered:
            # 只有在成功注册后才订阅事件
            crawler.subscriber.subscribe(o.spider_opened, event=CrawlerEvent.SPIDER_OPENED)
            crawler.subscriber.subscribe(o.spider_closed, event=CrawlerEvent.SPIDER_CLOSED)
        return o

    async def spider_opened(self) -> None:
        """爬虫启动时开始监控"""
        # 检查是否已经有一个监控实例在运行
        if not self.enabled or monitor_manager.get_monitor('memory_monitor') != self:
            # 如果此实例不是主要监控实例，则不启动监控
            return
            
        try:
            self.task = asyncio.create_task(self._monitor_loop())
            self.logger.info(f"Memory monitor started. Interval: {self.interval}s")
        except Exception as e:
            self.logger.error(f"Failed to start memory monitor: {e}")

    async def spider_closed(self) -> None:
        """爬虫关闭时停止监控"""
        # 只有主要监控实例才处理关闭
        if monitor_manager.get_monitor('memory_monitor') == self:
            if self.task:
                self.task.cancel()
                try:
                    await self.task
                except asyncio.CancelledError:
                    pass
                self.task = None
            
            # 检查是否在调度器模式下运行
            # 使用内部标识来判断是否是调度任务
            is_scheduler_mode = self.settings.get_bool('_INTERNAL_SCHEDULER_TASK', False)
            
            if not is_scheduler_mode:
                # 不是调度任务，注销监控实例
                monitor_manager.unregister_monitor('memory_monitor')
                # 清空内存历史数据以防止内存泄漏
                self.memory_history.clear()
                self.logger.info("Memory monitor stopped.")
            else:
                # 是调度任务，暂停监控（保持实例）
                # 清空内存历史数据以防止内存泄漏
                self.memory_history.clear()
                self.logger.info("Memory monitor paused (will resume with next spider).")

    def _calculate_memory_trend(self) -> tuple:
        """计算内存使用趋势
        Returns:
            tuple: (trend_slope, is_increasing) 趋势斜率和是否在增长
        """
        if len(self.memory_history) < 3:
            return 0.0, False
        
        # 使用最后N个点计算趋势
        recent_points = min(len(self.memory_history), 10)
        recent_data = self.memory_history[-recent_points:]
        
        # 计算线性回归斜率
        n = len(recent_data)
        sum_x = sum(range(n))
        sum_y = sum([point['rss'] for point in recent_data])
        sum_xy = sum(i * point['rss'] for i, point in enumerate(recent_data))
        sum_x2 = sum(i * i for i in range(n))
        
        if n * sum_x2 - sum_x * sum_x == 0:
            return 0.0, False
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
        
        # 判断是否在增长（考虑噪音容忍度）
        is_increasing = slope > 2.0 * 1024 * 1024  # 2.0MB/检查间隔的增长才认为是显著增长
        
        return slope, is_increasing

    async def _monitor_loop(self) -> None:
        """内存监控循环"""
        while True:
            try:
                # 获取系统内存信息（概览）
                system_memory = psutil.virtual_memory()
                system_percent = system_memory.percent
                
                # 获取当前进程内存信息
                process = psutil.Process()
                process_memory_info = process.memory_info()
                process_rss = process_memory_info.rss  # Resident Set Size (物理内存)
                process_vms = process_memory_info.vms  # Virtual Memory Size (虚拟内存)
                
                # 获取进程内存百分比
                process_percent = process.memory_percent()
                
                # 获取进程线程数（可能表明并发问题）
                thread_count = process.num_threads()
                
                # 记录到历史数据
                self.memory_history.append({
                    'timestamp': asyncio.get_event_loop().time(),
                    'rss': process_rss,
                    'vms': process_vms,
                    'percent': process_percent,
                    'threads': thread_count
                })
                
                # 限制历史数据大小
                if len(self.memory_history) > self.max_history_points:
                    self.memory_history.pop(0)
                
                # 计算内存趋势
                trend_slope, is_increasing = self._calculate_memory_trend()
                
                # 记录内存使用情况
                if system_percent > 0 or process_percent > 0:
                    # 分析潜在问题
                    issues = []
                    
                    # 检查进程内存使用率
                    if process_percent > self.critical_threshold:
                        issues.append(f"PROCESS CRITICAL ({process_percent:.2f}%)")
                    elif process_percent > self.warning_threshold:
                        issues.append(f"PROCESS WARNING ({process_percent:.2f}%)")
                    
                    # 检查内存泄露趋势
                    if is_increasing and len(self.memory_history) >= 3:
                        avg_growth_mb = (trend_slope / (1024 * 1024)) * self.interval  # MB/秒
                        issues.append(f"MEMORY LEAK TREND ({avg_growth_mb:.2f}MB/s)")
                    
                    # 检查线程数是否异常增长
                    if len(self.memory_history) > 1:
                        initial_threads = self.memory_history[0]['threads']
                        current_threads = thread_count
                        if current_threads > initial_threads * 2 and current_threads > 10:  # 线程数翻倍且超过10个
                            issues.append(f"THREAD LEAK ({initial_threads}->{current_threads})")
                    
                    issue_status = f" [ISSUES: {', '.join(issues)}]" if issues else " [OK]"
                    
                    # 计算增长趋势描述
                    trend_desc = "STABLE" if not is_increasing else f"GROWING({trend_slope/(1024*1024):+.2f}MB/check)"
                    
                    self.logger.info(
                        f"Project Memory Tracker{issue_status} - "
                        f"Process: {process_percent:.2f}%, "
                        f"RSS: {process_rss / 1024 / 1024:.2f}MB, "
                        f"Trend: {trend_desc}, "
                        f"Threads: {thread_count}, "
                        f"System: {system_percent:.2f}%"
                    )
                    
                    # 如果有严重问题，记录警告或错误
                    critical_issues = [issue for issue in issues if 'CRITICAL' in issue or 'LEAK' in issue]
                    warning_issues = [issue for issue in issues if 'WARNING' in issue and 'CRITICAL' not in issue]
                    
                    if critical_issues:
                        self.logger.error(f"Critical Memory Issues: {', '.join(critical_issues)}")
                    elif warning_issues:
                        self.logger.warning(f"Memory Warnings: {', '.join(warning_issues)}")
                
                await asyncio.sleep(self.interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in memory monitoring: {e}")
                await asyncio.sleep(self.interval)


def create_memory_monitor(crawler: Any) -> Optional[MemoryMonitorExtension]:
    """
    便捷函数：创建内存监控器（如果启用）
    
    Args:
        crawler: 爬虫实例
        
    Returns:
        MemoryMonitorExtension实例或None
    """
    if crawler.settings.get_bool('MEMORY_MONITOR_ENABLED', False):
        return MemoryMonitorExtension(crawler)
    return None