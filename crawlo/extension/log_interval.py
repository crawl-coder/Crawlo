#!/usr/bin/python
# -*- coding:UTF-8 -*-
import asyncio
from typing import Any, Optional

from crawlo.logging import get_logger
from crawlo.event import CrawlerEvent
from crawlo.utils.monitor.monitor_manager import monitor_manager


class LogIntervalExtension:

    def __init__(self, crawler: Any):
        # 始终启用间隔日志监控，不受 SCHEDULER_ENABLED 影响
        # 定时任务模式和普通模式都应该正常工作
        # 通过智能检测（爬虫空闲时跳过）来避免等待阶段的无意义日志
        self.disabled = False
        
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
        
        self.logger.info(f"LogIntervalExtension initialized: INTERVAL={self.seconds} seconds")

    @classmethod
    def create_instance(cls, crawler: Any) -> 'LogIntervalExtension':
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
        
        if self.task is None or self.task.done():
            self.task = asyncio.create_task(self.interval_log())
            self.logger.info(f"Interval logging task started (instance: {id(self)})")
        else:
            self.logger.warning(f"Interval logging task already running, skipping (instance: {id(self)})")

    async def spider_closed(self, **kwargs) -> None:
        # 只有主要监控实例才处理关闭
        if monitor_manager.get_monitor('log_interval_monitor') == self:
            self.logger.debug("Spider closed, stopping interval logging task")
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
            # scheduler 在 crawler.engine 中
            if hasattr(self.stats, 'crawler') and self.stats.crawler:
                crawler = self.stats.crawler
                if hasattr(crawler, 'engine') and crawler.engine:
                    engine = crawler.engine
                    if hasattr(engine, 'scheduler') and engine.scheduler:
                        scheduler = engine.scheduler
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

    async def _get_backpressure_info(self) -> tuple:
        """
        获取背压信息
        
        Returns:
            tuple: (is_active, delay, utilization)
                - is_active: 背压是否激活
                - delay: 当前背压延迟（秒）
                - utilization: 队列使用率（0-1）
        """
        try:
            if hasattr(self.stats, 'crawler') and self.stats.crawler:
                crawler = self.stats.crawler
                if hasattr(crawler, 'engine') and crawler.engine:
                    engine = crawler.engine
                    if hasattr(engine, 'scheduler') and engine.scheduler:
                        scheduler = engine.scheduler
                        if hasattr(scheduler, 'queue_manager') and scheduler.queue_manager:
                            queue_manager = scheduler.queue_manager
                            
                            # 获取队列大小和最大大小
                            queue_size = 0
                            max_size = 0
                            
                            if hasattr(queue_manager, 'size'):
                                if asyncio.iscoroutinefunction(queue_manager.size):
                                    queue_size = await queue_manager.size()
                                else:
                                    queue_size = queue_manager.size()
                            
                            # 尝试获取最大队列大小（支持多种属性名）
                            if hasattr(queue_manager, 'max_queue_size'):
                                max_size = queue_manager.max_queue_size
                            elif hasattr(queue_manager, 'max_size'):
                                max_size = queue_manager.max_size
                            elif hasattr(queue_manager, '_max_size'):
                                max_size = queue_manager._max_size
                            elif hasattr(queue_manager, 'config') and hasattr(queue_manager.config, 'max_queue_size'):
                                max_size = queue_manager.config.max_queue_size
                            
                            # 计算使用率
                            utilization = queue_size / max_size if max_size > 0 else 0
                            
                            # 检查背压控制器
                            if hasattr(queue_manager, '_backpressure_controller') and queue_manager._backpressure_controller:
                                controller = queue_manager._backpressure_controller
                                
                                # 获取背压状态
                                is_active = False
                                delay = 0.0
                                
                                if hasattr(controller, '_strategy') and controller._strategy:
                                    strategy = controller._strategy
                                    
                                    # 检查是否应该应用背压
                                    if hasattr(strategy, 'should_apply'):
                                        try:
                                            if asyncio.iscoroutinefunction(strategy.should_apply):
                                                is_active = await strategy.should_apply(queue_manager)
                                            else:
                                                is_active = strategy.should_apply(queue_manager)
                                        except Exception as e:
                                            self.logger.debug(f"Failed to check should_apply: {e}")
                                    
                                    # 获取延迟
                                    if hasattr(strategy, 'calculate_delay'):
                                        try:
                                            if asyncio.iscoroutinefunction(strategy.calculate_delay):
                                                delay = await strategy.calculate_delay(queue_manager)
                                            else:
                                                delay = strategy.calculate_delay(queue_manager)
                                        except Exception as e:
                                            self.logger.debug(f"Failed to calculate delay: {e}")
                                
                                # 如果没有成功获取到状态，根据使用率估算
                                if not is_active and utilization >= 0.5:
                                    is_active = True
                                    # 根据使用率估算延迟
                                    if utilization >= 0.95:
                                        delay = max(delay, 5.0)
                                    elif utilization >= 0.9:
                                        delay = max(delay, 2.0)
                                    elif utilization >= 0.8:
                                        delay = max(delay, 1.0)
                                    else:
                                        delay = max(delay, 0.5)
                                
                                return (is_active, delay, utilization)
                            
                            # 如果没有背压控制器，根据使用率估算
                            threshold = getattr(queue_manager, '_backpressure_threshold', 0.8)
                            is_active = utilization >= threshold
                            
                            # 简单估算延迟
                            if utilization >= 0.95:
                                delay = 5.0
                            elif utilization >= 0.9:
                                delay = 2.0
                            elif utilization >= threshold:
                                delay = 0.5 * (1 + (utilization - threshold) / (0.95 - threshold) * 3)
                            else:
                                delay = 0.0
                            
                            return (is_active, delay, utilization)
            
            return (False, 0.0, 0.0)
        except Exception as e:
            self.logger.debug(f"Failed to get backpressure info: {e}")
            return (False, 0.0, 0.0)

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
                
                # 智能检测：如果爬虫已停止（无新数据且队列为空），跳过日志输出
                queue_size = await self._get_queue_size()
                if item_rate == 0 and response_rate == 0 and queue_size == 0:
                    # 爬虫可能已停止，静默跳过，不打印日志
                    await asyncio.sleep(self.seconds)
                    continue
                
                # 获取队列大小和背压信息
                bp_active, bp_delay, bp_util = await self._get_backpressure_info()
                
                # 更新计数器
                self.item_count, self.response_count = last_item_count, last_response_count
                
                # 构建背压信息字符串
                if bp_active:
                    bp_info = f"BP: ON ({bp_delay:.2f}s, {bp_util:.0%})"
                else:
                    bp_info = f"BP: off ({bp_util:.0%})"
                
                # 计算速率并输出日志
                if self.unit == 'min' and self.seconds > 0:
                    # 转换为每分钟速率
                    pages_per_min = response_rate * 60 / self.seconds if self.seconds > 0 else 0
                    items_per_min = item_rate * 60 / self.seconds if self.seconds > 0 else 0
                    self.logger.info(
                        f'Crawled {last_response_count} pages (at {pages_per_min:.0f} pages/min),'
                        f' Got {last_item_count} items (at {items_per_min:.0f} items/min),'
                        f' Queue: {queue_size} pending, {bp_info}'
                    )
                else:
                    # 使用原始单位
                    self.logger.info(
                        f'Crawled {last_response_count} pages (at {response_rate} pages/{self.interval_display}{self.unit}),'
                        f' Got {last_item_count} items (at {item_rate} items/{self.interval_display}{self.unit}),'
                        f' Queue: {queue_size} pending, {bp_info}'
                    )
                
                # 调试日志（合并为一条）
                self.logger.debug(
                    f"Interval log [{iteration}]: "
                    f"items={item_rate} (total={last_item_count}), "
                    f"responses={response_rate} (total={last_response_count}), "
                    f"queue={queue_size}, "
                    f"backpressure={bp_active}, delay={bp_delay:.3f}s, util={bp_util:.1%}, "
                    f"next_log_in={self.seconds}s"
                )
                
                await asyncio.sleep(self.seconds)
            except Exception as e:
                self.logger.error(f"Error in interval logging: {e}")
                await asyncio.sleep(self.seconds)  # 即使出错也继续执行