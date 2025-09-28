#!/usr/bin/python
# -*- coding:UTF-8 -*-
import asyncio
import psutil
from typing import Any, Optional

from crawlo.utils.log import get_logger
from crawlo.utils.error_handler import ErrorHandler
from crawlo.event import spider_opened, spider_closed


class MemoryMonitorExtension:
    """
    内存监控扩展
    定期监控爬虫进程的内存使用情况，并在超出阈值时发出警告
    """

    def __init__(self, crawler: Any):
        self.task: Optional[asyncio.Task] = None
        self.process = psutil.Process()
        self.settings = crawler.settings
        self.logger = get_logger(self.__class__.__name__, crawler.settings.get('LOG_LEVEL'))
        self.error_handler = ErrorHandler(self.__class__.__name__, crawler.settings.get('LOG_LEVEL'))
        
        # 获取配置参数
        self.interval = self.settings.get_int('MEMORY_MONITOR_INTERVAL', 60)  # 默认60秒检查一次
        self.warning_threshold = self.settings.get_float('MEMORY_WARNING_THRESHOLD', 80.0)  # 默认80%警告阈值
        self.critical_threshold = self.settings.get_float('MEMORY_CRITICAL_THRESHOLD', 90.0)  # 默认90%严重阈值

    @classmethod
    def create_instance(cls, crawler: Any) -> 'MemoryMonitorExtension':
        # 只有当配置启用时才创建实例
        if not crawler.settings.get_bool('MEMORY_MONITOR_ENABLED', False):
            from crawlo.exceptions import NotConfigured
            raise NotConfigured("MemoryMonitorExtension: MEMORY_MONITOR_ENABLED is False")
        
        o = cls(crawler)
        crawler.subscriber.subscribe(o.spider_opened, event=spider_opened)
        crawler.subscriber.subscribe(o.spider_closed, event=spider_closed)
        return o

    async def spider_opened(self) -> None:
        """爬虫启动时开始监控"""
        try:
            self.task = asyncio.create_task(self._monitor_loop())
            self.logger.info(
                f"Memory monitor started. Interval: {self.interval}s, "
                f"Warning threshold: {self.warning_threshold}%, Critical threshold: {self.critical_threshold}%"
            )
        except Exception as e:
            self.error_handler.handle_error(
                e, 
                context="启动内存监控失败", 
                raise_error=False
            )

    async def spider_closed(self) -> None:
        """爬虫关闭时停止监控"""
        try:
            if self.task:
                self.task.cancel()
                try:
                    await self.task
                except asyncio.CancelledError:
                    pass
                self.task = None
                self.logger.info("Memory monitor stopped.")
        except Exception as e:
            self.error_handler.handle_error(
                e, 
                context="停止内存监控失败", 
                raise_error=False
            )

    async def _monitor_loop(self) -> None:
        """内存监控循环"""
        while True:
            try:
                # 获取内存使用信息
                memory_info = self.process.memory_info()
                memory_percent = self.process.memory_percent()
                
                # 记录内存使用情况
                self.logger.debug(
                    f"Memory usage: {memory_percent:.2f}% "
                    f"(RSS: {memory_info.rss / 1024 / 1024:.2f} MB, "
                    f"VMS: {memory_info.vms / 1024 / 1024:.2f} MB)"
                )
                
                # 检查是否超过阈值
                if memory_percent >= self.critical_threshold:
                    self.logger.critical(
                        f"Memory usage critical: {memory_percent:.2f}% "
                        f"(RSS: {memory_info.rss / 1024 / 1024:.2f} MB)"
                    )
                elif memory_percent >= self.warning_threshold:
                    self.logger.warning(
                        f"Memory usage high: {memory_percent:.2f}% "
                        f"(RSS: {memory_info.rss / 1024 / 1024:.2f} MB)"
                    )
                
                await asyncio.sleep(self.interval)
            except Exception as e:
                self.logger.error(f"Error in memory monitoring: {e}")
                await asyncio.sleep(self.interval)