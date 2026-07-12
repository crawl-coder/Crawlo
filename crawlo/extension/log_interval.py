#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
Log Interval Extension
Periodic crawling statistics with backpressure monitoring
"""
import asyncio
from typing import Any, Optional, Tuple

from crawlo.logging import get_logger
from crawlo.event import CrawlerEvent
from .monitor.monitor_manager import get_monitor_manager


class LogIntervalExtension:

    def __init__(self, crawler: Any):
        self.enabled = True   # 始终启用，不受 SCHEDULER_ENABLED 影响
        self.task: Optional[asyncio.Task] = None
        self.stats = crawler.stats
        self.item_count = 0
        self.response_count = 0
        self.seconds = crawler.settings.get('INTERVAL', 60)

        # 修复时间单位计算逻辑
        if self.seconds % 60 == 0:
            self.interval = int(self.seconds / 60)
            self.unit = 'min'
        else:
            self.interval = self.seconds
            self.unit = 's'

        if self.interval == 1 and self.unit == 'min':
            self.interval_display = ""
        else:
            self.interval_display = str(self.interval)

        self.logger = get_logger(self.__class__.__name__)
        self.logger.info(f"LogIntervalExtension initialized: INTERVAL={self.seconds} seconds")

    @classmethod
    def create_instance(cls, crawler: Any) -> 'LogIntervalExtension':
        mm = get_monitor_manager()
        existing = mm.get_monitor('log_interval_monitor')
        if existing is not None:
            o = cls(crawler)
            o.enabled = False
            return o

        o = cls(crawler)
        registered = mm.register_monitor('log_interval_monitor', o)
        if registered:
            crawler.subscriber.subscribe(o.spider_opened, event=CrawlerEvent.SPIDER_OPENED)
            crawler.subscriber.subscribe(o.spider_closed, event=CrawlerEvent.SPIDER_CLOSED)
        return o

    async def spider_opened(self) -> None:
        if not self.enabled or get_monitor_manager().get_monitor('log_interval_monitor') != self:
            return
        if self.task is None or self.task.done():
            self.task = asyncio.create_task(self.interval_log())
            self.logger.debug(f"Interval logging task started (id={id(self)}).")

    async def spider_closed(self, **kwargs) -> None:
        mm = get_monitor_manager()
        if mm.get_monitor('log_interval_monitor') == self:
            self.logger.debug("Spider closed, stopping interval logging task")
            if self.task:
                self.task.cancel()
                try:
                    await self.task
                except asyncio.CancelledError:
                    pass
                self.task = None
            mm.unregister_monitor('log_interval_monitor')

    # ---- 队列/背压查询 ----

    async def _get_queue_size(self) -> int:
        """获取队列大小（pending requests）"""
        try:
            if hasattr(self.stats, 'crawler') and self.stats.crawler:
                crawler = self.stats.crawler
                if hasattr(crawler, 'engine') and crawler.engine:
                    engine = crawler.engine
                    if hasattr(engine, 'scheduler') and engine.scheduler:
                        scheduler = engine.scheduler
                        if hasattr(scheduler, 'queue_manager') and scheduler.queue_manager:
                            qm = scheduler.queue_manager
                            if hasattr(qm, 'size'):
                                if asyncio.iscoroutinefunction(qm.size):
                                    return await qm.size()
                                else:
                                    return qm.size()
            return 0
        except Exception as e:
            self.logger.debug(f"Failed to get queue size: {e}")
            return 0

    async def _get_backpressure_info(self) -> Tuple[bool, float, float, float, str]:
        """获取背压信息 → (is_active, delay, utilization, score, level)"""
        try:
            qm = self._resolve_queue_manager()
            if qm is None:
                return (False, 0.0, 0.0, 0.0, 'normal')

            queue_size, max_size, utilization = await self._get_queue_metrics(qm)

            # 优先智能背压
            smart_result = await self._get_smart_backpressure(qm, utilization)
            if smart_result is not None:
                return smart_result

            # 传统背压
            trad_result = await self._get_traditional_backpressure(qm, utilization, max_size)
            if trad_result is not None:
                return trad_result

            # 无背压控制器时的估算
            return self._estimate_backpressure(qm, utilization, max_size)
        except Exception as e:
            self.logger.debug(f"Failed to get backpressure info: {e}")
            return (False, 0.0, 0.0, 0.0, 'normal')

    def _resolve_queue_manager(self) -> Any:
        """解析 queue_manager 对象"""
        if not (hasattr(self.stats, 'crawler') and self.stats.crawler):
            return None
        crawler = self.stats.crawler
        if not (hasattr(crawler, 'engine') and crawler.engine):
            return None
        engine = crawler.engine
        if not (hasattr(engine, 'scheduler') and engine.scheduler):
            return None
        scheduler = engine.scheduler
        if not (hasattr(scheduler, 'queue_manager') and scheduler.queue_manager):
            return None
        return scheduler.queue_manager

    async def _get_queue_metrics(self, qm: Any) -> Tuple[int, int, float]:
        """获取队列大小和使用率"""
        queue_size = 0
        max_size = 0
        if hasattr(qm, 'size'):
            queue_size = await qm.size() if asyncio.iscoroutinefunction(qm.size) else qm.size()

        for attr in ('max_queue_size', 'max_size', '_max_size'):
            if hasattr(qm, attr):
                max_size = getattr(qm, attr)
                break
        if max_size == 0 and hasattr(qm, 'config') and hasattr(qm.config, 'max_queue_size'):
            max_size = qm.config.max_queue_size

        utilization = queue_size / max_size if max_size > 0 else 0
        return queue_size, max_size, utilization

    async def _get_smart_backpressure(self, qm: Any, utilization: float) -> Optional[Tuple]:
        """尝试获取智能背压信息，不支持则返回 None"""
        if not (hasattr(qm, '_intelligent_backpressure_enabled') and qm._intelligent_backpressure_enabled):
            return None
        if not (hasattr(qm, '_metrics_collector') and qm._metrics_collector):
            return None

        metrics = qm._metrics_collector.get_current_metrics()
        if not metrics:
            return None

        score = metrics.overall_score
        level = metrics.level
        is_active = score >= 50

        delay = 0.0
        if hasattr(qm, '_intelligent_calculator') and qm._intelligent_calculator:
            delay = await qm._intelligent_calculator.calculate_delay()

        return (is_active, delay, utilization, score, level)

    async def _get_traditional_backpressure(self, qm: Any, utilization: float, max_size: int) -> Optional[Tuple]:
        """尝试获取传统背压信息，不支持则返回 None"""
        if not (hasattr(qm, '_backpressure_controller') and qm._backpressure_controller):
            return None

        controller = qm._backpressure_controller
        is_active, delay = False, 0.0

        if hasattr(controller, '_strategy') and controller._strategy:
            strategy = controller._strategy
            if hasattr(strategy, 'should_apply'):
                try:
                    is_active = (
                        await strategy.should_apply(qm)
                        if asyncio.iscoroutinefunction(strategy.should_apply)
                        else strategy.should_apply(qm)
                    )
                except Exception as e:
                    self.logger.debug(f"Failed to check should_apply: {e}")
            if hasattr(strategy, 'calculate_delay'):
                try:
                    delay = (
                        await strategy.calculate_delay(qm)
                        if asyncio.iscoroutinefunction(strategy.calculate_delay)
                        else strategy.calculate_delay(qm)
                    )
                except Exception as e:
                    self.logger.debug(f"Failed to calculate delay: {e}")

        # 根据使用率补充估算
        if not is_active and utilization >= 0.5:
            is_active = True
            delay = max(delay, self._estimate_delay_from_utilization(utilization))

        level = self._utilization_level(utilization)
        return (is_active, delay, utilization, 0.0, level)

    def _estimate_backpressure(self, qm: Any, utilization: float, max_size: int) -> Tuple:
        """没有背压控制器时的简单估算"""
        threshold = getattr(qm, '_backpressure_threshold', 0.8)
        is_active = utilization >= threshold

        delay = 0.0
        if utilization >= 0.95:
            delay = 5.0
        elif utilization >= 0.9:
            delay = 2.0
        elif utilization >= threshold:
            delay = 0.5 * (1 + (utilization - threshold) / (0.95 - threshold) * 3)

        level = self._utilization_level(utilization)
        return (is_active, delay, utilization, 0.0, level)

    @staticmethod
    def _estimate_delay_from_utilization(utilization: float) -> float:
        if utilization >= 0.95:
            return 5.0
        elif utilization >= 0.9:
            return 2.0
        elif utilization >= 0.8:
            return 1.0
        return 0.5

    @staticmethod
    def _utilization_level(utilization: float) -> str:
        if utilization >= 0.85:
            return 'critical'
        elif utilization >= 0.7:
            return 'danger'
        elif utilization >= 0.5:
            return 'warning'
        return 'normal'

    # ---- 间隔日志循环 ----

    async def interval_log(self) -> None:
        iteration = 0
        while True:
            try:
                iteration += 1
                last_item_count = self.stats.get_value('item_successful_count', default=0)
                last_response_count = self.stats.get_value('response_received_count', default=0)
                item_rate = last_item_count - self.item_count
                response_rate = last_response_count - self.response_count

                queue_size = await self._get_queue_size()
                # 写入 StatsCollector，供 Prometheus 等后端暴露
                try:
                    self.stats.set_value('queue_size', queue_size)
                except Exception:
                    pass
                # 智能检测：爬虫闲置时静默跳过
                if item_rate == 0 and response_rate == 0 and queue_size == 0:
                    await asyncio.sleep(self.seconds)
                    continue

                bp_active, bp_delay, bp_util, bp_score, bp_level = await self._get_backpressure_info()
                self.item_count, self.response_count = last_item_count, last_response_count

                self._log_interval_stats(last_item_count, last_response_count,
                                         item_rate, response_rate, queue_size,
                                         bp_active, bp_delay, bp_util, bp_score, bp_level,
                                         iteration)
                await asyncio.sleep(self.seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in interval logging: {e}")
                await asyncio.sleep(self.seconds)

    def _log_interval_stats(self, last_item_count, last_response_count,
                            item_rate, response_rate, queue_size,
                            bp_active, bp_delay, bp_util, bp_score, bp_level,
                            iteration) -> None:
        """格式化并输出间隔统计日志"""
        if bp_active:
            bp_info = (f"BP: ON ({bp_delay:.2f}s, {bp_util:.0%}, score:{bp_score:.0f}, {bp_level})"
                       if bp_score > 0 else f"BP: ON ({bp_delay:.2f}s, {bp_util:.0%})")
        else:
            bp_info = f"BP: off ({bp_util:.0%})"

        if self.unit == 'min' and self.seconds > 0:
            pages_per_min = response_rate * 60 / self.seconds
            items_per_min = item_rate * 60 / self.seconds
            self.logger.info(
                f'Crawled {last_response_count} pages (at {pages_per_min:.0f} pages/min),'
                f' Got {last_item_count} items (at {items_per_min:.0f} items/min),'
                f' Queue: {queue_size} pending, {bp_info}'
            )
        else:
            self.logger.info(
                f'Crawled {last_response_count} pages (at {response_rate} pages/{self.interval_display}{self.unit}),'
                f' Got {last_item_count} items (at {item_rate} items/{self.interval_display}{self.unit}),'
                f' Queue: {queue_size} pending, {bp_info}'
            )

        # Debug 日志
        debug_info = (
            f"Interval log [{iteration}]: "
            f"items={item_rate} (total={last_item_count}), "
            f"responses={response_rate} (total={last_response_count}), "
            f"queue={queue_size}, backpressure={bp_active}, delay={bp_delay:.3f}s, util={bp_util:.1%}"
        )
        if bp_score > 0:
            debug_info += f", score={bp_score:.1f}, level={bp_level}"
        debug_info += f", next_log_in={self.seconds}s"
        self.logger.debug(debug_info)
