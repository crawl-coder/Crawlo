#!/usr/bin/python
# -*- coding:UTF-8 -*-
import asyncio
from typing import Any, Optional

from crawlo.logging import get_logger
from crawlo.event import CrawlerEvent
from crawlo.utils.monitor.monitor_manager import monitor_manager


class LogIntervalExtension:

    def __init__(self, crawler: Any):
        # 检查是否在调度器模式下运行（用于定时任务模式）
        scheduler_enabled = crawler.settings.get('SCHEDULER_ENABLED', False)
        self.disabled = scheduler_enabled  # 在调度器启用时禁用日志扩展
        
        self.task: Optional[asyncio.Task] = None
        self.stats = crawler.stats
        self.item_count = 0
        self.response_count = 0
        self.seconds = crawler.settings.get('INTERVAL', 60)  # 默认60秒
        
        # 修复时间单位计算逻辑
        if self.seconds % 60 == 0:
            self.interval = int(self.seconds / 60)
            self.unit = 'min'
        else:
            self.interval = self.seconds
            self.unit = 's'
        
        # 处理单数情况
        if self.interval == 1 and self.unit == 'min':
            self.interval_display = ""
        else:
            self.interval_display = str(self.interval)

        self.logger = get_logger(self.__class__.__name__)
        
        # 监控管理器
        self.monitor_manager = monitor_manager
        
        if self.disabled:
            self.logger.debug("LogIntervalExtension disabled in scheduler mode")
            return
        
        self.logger.info(f"LogIntervalExtension initialized with interval: {self.seconds} seconds")
        
        # 添加调试信息（在logger初始化之后）
        self.logger.info(f"LogIntervalExtension: INTERVAL={self.seconds} seconds")

    @classmethod
    def create_instance(cls, crawler: Any) -> 'LogIntervalExtension':
        # 检查是否在调度器模式下运行
        scheduler_enabled = crawler.settings.get('SCHEDULER_ENABLED', False)
        if scheduler_enabled:
            # 在调度器模式下，禁用此扩展以避免重复日志
            o = cls(crawler)
            return o
        
        # 检查是否已有日志间隔监控实例在运行
        existing_monitor = monitor_manager.get_monitor('log_interval_monitor')
        if existing_monitor is not None:
            # 如果已有实例在运行，返回一个不执行任何操作的实例
            o = cls(crawler)
            o.disabled = True  # 禁用此实例的实际监控功能
            return o
        
        o = cls(crawler)
        # 注册监控实例到管理器
        registered = monitor_manager.register_monitor('log_interval_monitor', o)
        if registered:
            # 只有在成功注册后才订阅事件
            crawler.subscriber.subscribe(o.spider_opened, event=CrawlerEvent.SPIDER_OPENED)
            crawler.subscriber.subscribe(o.spider_closed, event=CrawlerEvent.SPIDER_CLOSED)
        return o

    async def spider_opened(self) -> None:
        # 检查是否已经有一个监控实例在运行
        if hasattr(self, 'disabled') and self.disabled or monitor_manager.get_monitor('log_interval_monitor') != self:
            self.logger.debug(f"Spider opened, LogIntervalExtension disabled, skipping task creation (instance: {id(self)})")
            return
        
        self.logger.info(f"Spider opened, starting interval logging task (instance: {id(self)})")
        if self.task is None or self.task.done():
            self.task = asyncio.create_task(self.interval_log())
            self.logger.info(f"Interval logging task started (instance: {id(self)})")
        else:
            self.logger.warning(f"Interval logging task already running, skipping (instance: {id(self)})")

    async def spider_closed(self, **kwargs) -> None:
        # 只有主要监控实例才处理关闭
        if monitor_manager.get_monitor('log_interval_monitor') == self:
            self.logger.info("Spider closed, stopping interval logging task")
            if self.task:
                self.task.cancel()
                try:
                    await self.task
                except asyncio.CancelledError:
                    pass
                self.task = None
            # 从监控管理器中注销
            monitor_manager.unregister_monitor('log_interval_monitor')

    async def _get_queue_size(self) -> int:
        """获取队列大小（待处理请求数）"""
        try:
            # 尝试从 crawler 获取 scheduler 的队列大小
            if hasattr(self.stats, 'crawler') and self.stats.crawler:
                crawler = self.stats.crawler
                if hasattr(crawler, 'scheduler') and crawler.scheduler:
                    scheduler = crawler.scheduler
                    if hasattr(scheduler, 'queue_manager') and scheduler.queue_manager:
                        queue_manager = scheduler.queue_manager
                        if hasattr(queue_manager, 'size'):
                            if asyncio.iscoroutinefunction(queue_manager.size):
                                return await queue_manager.size()
                            else:
                                return queue_manager.size()
            return 0
        except Exception as e:
            self.logger.debug(f"Failed to get queue size: {e}")
            return 0

    async def interval_log(self) -> None:
        iteration = 0
        while True:
            try:
                iteration += 1
                
                # 获取统计数据
                last_item_count = self.stats.get_value('item_successful_count', default=0)
                last_response_count = self.stats.get_value('response_received_count', default=0)
                item_rate = last_item_count - self.item_count
                response_rate = last_response_count - self.response_count
                
                # 获取队列大小
                queue_size = await self._get_queue_size()
                
                # 更新计数器
                self.item_count, self.response_count = last_item_count, last_response_count
                
                # 计算速率并输出日志
                if self.unit == 'min' and self.seconds > 0:
                    # 转换为每分钟速率
                    pages_per_min = response_rate * 60 / self.seconds if self.seconds > 0 else 0
                    items_per_min = item_rate * 60 / self.seconds if self.seconds > 0 else 0
                    self.logger.info(
                        f'Crawled {last_response_count} pages (at {pages_per_min:.0f} pages/min),'
                        f' Got {last_item_count} items (at {items_per_min:.0f} items/min),'
                        f' Queue: {queue_size} pending.'
                    )
                else:
                    # 使用原始单位
                    self.logger.info(
                        f'Crawled {last_response_count} pages (at {response_rate} pages/{self.interval_display}{self.unit}),'
                        f' Got {last_item_count} items (at {item_rate} items/{self.interval_display}{self.unit}),'
                        f' Queue: {queue_size} pending.'
                    )
                
                # 调试日志（合并为一条）
                self.logger.debug(
                    f"Interval log [{iteration}]: "
                    f"items={item_rate} (total={last_item_count}), "
                    f"responses={response_rate} (total={last_response_count}), "
                    f"queue={queue_size}, "
                    f"next_log_in={self.seconds}s"
                )
                
                await asyncio.sleep(self.seconds)
            except Exception as e:
                self.logger.error(f"Error in interval logging: {e}")
                await asyncio.sleep(self.seconds)  # 即使出错也继续执行