#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
Redis监控扩展
监控Redis连接池和性能
"""
import asyncio
from typing import Any, Optional

from crawlo.logging import get_logger
from crawlo.event import CrawlerEvent
from crawlo.utils.monitor_manager import monitor_manager


class RedisMonitorExtension:
    """
    Redis监控扩展
    监控Redis连接池状态和性能
    """

    def __init__(self, crawler: Any):
        self.task: Optional[asyncio.Task] = None
        self.crawler = crawler
        self.settings = crawler.settings
        self.logger = get_logger(self.__class__.__name__)
        
        # 获取配置参数
        self.interval = self.settings.get_int('REDIS_MONITOR_INTERVAL', 60)  # 默认60秒检查一次
        self.enabled = self.settings.get_bool('REDIS_MONITOR_ENABLED', False)
        
        # 监控管理器
        self.monitor_manager = monitor_manager
        
        # 连接池使用趋势追踪
        self.pool_usage_history = []  # 存储连接池使用率历史
        self.max_history_points = 50  # 最大历史记录点数
        
        if self.enabled:
            self.logger.info(f"Redis monitor initialized. Interval: {self.interval}s")

    @classmethod
    def create_instance(cls, crawler: Any) -> 'RedisMonitorExtension':
        # 只有当配置启用时才创建实例
        if not crawler.settings.get_bool('REDIS_MONITOR_ENABLED', False):
            from crawlo.exceptions import NotConfigured
            from crawlo.logging import get_logger
            logger = get_logger(cls.__name__)
            # 使用debug级别日志，避免在正常情况下产生错误日志
            logger.debug("RedisMonitorExtension: REDIS_MONITOR_ENABLED is False, skipping initialization")
            raise NotConfigured("RedisMonitorExtension: REDIS_MONITOR_ENABLED is False")
        
        # 检查是否已有Redis监控实例在运行
        existing_monitor = monitor_manager.get_monitor('redis_monitor')
        if existing_monitor is not None:
            # 如果已有实例在运行，返回一个不执行任何操作的实例
            o = cls(crawler)
            o.enabled = False  # 禁用此实例的实际监控功能
            return o
        
        o = cls(crawler)
        # 注册监控实例到管理器
        registered = monitor_manager.register_monitor('redis_monitor', o)
        if registered:
            # 只有在成功注册后才订阅事件
            crawler.subscriber.subscribe(o.spider_opened, event=CrawlerEvent.SPIDER_OPENED)
            crawler.subscriber.subscribe(o.spider_closed, event=CrawlerEvent.SPIDER_CLOSED)
        return o

    async def spider_opened(self) -> None:
        """爬虫启动时开始监控"""
        # 检查是否已经有一个监控实例在运行
        if not self.enabled or monitor_manager.get_monitor('redis_monitor') != self:
            # 如果此实例不是主要监控实例，则不启动监控
            return
            
        try:
            self.task = asyncio.create_task(self._monitor_loop())
            self.logger.info(f"Redis monitor started. Interval: {self.interval}s")
        except Exception as e:
            self.logger.error(f"Failed to start Redis monitor: {e}")

    async def spider_closed(self) -> None:
        """爬虫关闭时停止监控"""
        # 只有主要监控实例才处理关闭
        if monitor_manager.get_monitor('redis_monitor') == self:
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
                monitor_manager.unregister_monitor('redis_monitor')
                # 清空连接池使用历史数据以防止内存泄漏
                self.pool_usage_history.clear()
                self.logger.info("Redis monitor stopped.")
            else:
                # 是调度任务，暂停监控（保持实例）
                # 清空连接池使用历史数据以防止内存泄漏
                self.pool_usage_history.clear()
                self.logger.info("Redis monitor paused (will resume with next spider).")

    def _calculate_pool_trend(self) -> tuple:
        """计算连接池使用趋势
        Returns:
            tuple: (trend_slope, is_increasing) 趋势斜率和是否在增长
        """
        if len(self.pool_usage_history) < 3:
            return 0.0, False
        
        # 使用最后N个点计算趋势
        recent_points = min(len(self.pool_usage_history), 10)
        recent_data = self.pool_usage_history[-recent_points:]
        
        # 计算线性回归斜率
        n = len(recent_data)
        sum_x = sum(range(n))
        sum_y = sum(recent_data)
        sum_xy = sum(i * value for i, value in enumerate(recent_data))
        sum_x2 = sum(i * i for i in range(n))
        
        if n * sum_x2 - sum_x * sum_x == 0:
            return 0.0, False
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
        
        # 判断是否在增长（考虑噪音容忍度）
        is_increasing = slope > 0.5  # 0.5%/检查间隔的增长才认为是显著增长
        
        return slope, is_increasing

    async def _monitor_loop(self) -> None:
        """Redis监控循环 - 监控连接池资源泄露"""
        while True:
            try:
                # 获取Redis连接池使用率
                connections_used = self.crawler.stats.get_value('redis/connections_used', 0)
                pool_size = self.crawler.stats.get_value('redis/pool_size', 10)  # 默认10个连接
                pool_usage = (connections_used / pool_size * 100) if pool_size > 0 else 0
                
                # 记录到历史数据（始终记录，用于趋势分析）
                self.pool_usage_history.append(pool_usage)
                
                # 限制历史数据大小
                if len(self.pool_usage_history) > self.max_history_points:
                    self.pool_usage_history.pop(0)
                
                # 当有足够数据时，分析连接池趋势
                if len(self.pool_usage_history) >= 3:
                    trend_slope, is_increasing = self._calculate_pool_trend()
                    
                    # 只有发现资源泄露趋势才告警
                    if is_increasing and len(self.pool_usage_history) >= 5:
                        self.logger.warning(
                            f"Redis连接池泄露警告 - 使用率持续增长: {trend_slope:+.2f}%/检查, "
                            f"当前使用率: {pool_usage:.2f}%"
                        )
                
                await asyncio.sleep(self.interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Redis监控错误: {e}")
                await asyncio.sleep(self.interval)


def create_redis_monitor(crawler: Any) -> Optional[RedisMonitorExtension]:
    """
    便捷函数：创建Redis监控器（如果启用）
    
    Args:
        crawler: 爬虫实例
        
    Returns:
        RedisMonitorExtension实例或None
    """
    if crawler.settings.get_bool('REDIS_MONITOR_ENABLED', False):
        return RedisMonitorExtension(crawler)
    return None