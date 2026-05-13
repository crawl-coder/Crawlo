#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
Health Check Extension
Monitor crawler health status including response time, error rates etc.
"""
import asyncio
from datetime import datetime
from typing import Any, Dict

from crawlo.event import CrawlerEvent
from .monitor.base import BaseMonitorExtension


class HealthCheckExtension(BaseMonitorExtension):
    """
    健康检查扩展
    监控爬虫的健康状态，包括响应时间、错误率等指标
    """

    monitor_id = 'health_check_monitor'
    config_key = 'HEALTH_CHECK_ENABLED'
    default_enabled = True
    extra_events = [
        ('response_received', CrawlerEvent.RESPONSE_RECEIVED),
        ('request_scheduled', CrawlerEvent.REQUEST_SCHEDULED),
    ]

    def __init__(self, crawler: Any):
        super().__init__(crawler)

        self.check_interval = self.settings.get_int('HEALTH_CHECK_INTERVAL', 60)
        self.stats: Dict[str, Any] = {
            'start_time': None,
            'total_requests': 0,
            'total_responses': 0,
            'error_responses': 0,
            'last_check_time': None,
        }

    # ---- spider_closed 清理 ----

    def _on_spider_closed_cleanup(self) -> None:
        """输出最终健康报告"""
        async def _log():
            await self._check_health()
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(_log())
            else:
                loop.run_until_complete(_log())
        except RuntimeError:
            pass  # 事件循环不可用时跳过

    # ---- 事件回调 ----

    async def spider_opened(self) -> None:
        """爬虫启动时记录起始时间"""
        if not self.enabled:
            return
        self.stats['start_time'] = datetime.now()
        await super().spider_opened()

    async def request_scheduled(self, request: Any, spider: Any) -> None:
        """记录调度的请求（排除重试）"""
        if not self.enabled:
            return
        if not request.meta.get('is_retry', False):
            self.stats['total_requests'] += 1

    async def response_received(self, response: Any, spider: Any) -> None:
        """记录接收到的响应"""
        if not self.enabled:
            return
        self.stats['total_responses'] += 1
        if hasattr(response, 'status') and response.status >= 400:
            self.stats['error_responses'] += 1

    # ---- 监控循环 ----

    async def _monitor_loop(self) -> None:
        """健康检查循环"""
        while True:
            try:
                await asyncio.sleep(self.check_interval)
                await self._check_health()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in health check loop: {e}")

    async def _check_health(self) -> None:
        """执行健康检查并输出报告"""
        try:
            now_time = datetime.now()
            self.stats['last_check_time'] = now_time

            runtime = (now_time - self.stats['start_time']).total_seconds() if self.stats['start_time'] else 0
            req_per_sec = self.stats['total_requests'] / runtime if runtime > 0 else 0
            resp_per_sec = self.stats['total_responses'] / runtime if runtime > 0 else 0
            error_rate = (
                self.stats['error_responses'] / self.stats['total_responses']
                if self.stats['total_responses'] > 0 else 0
            )

            report = {
                'runtime_seconds': round(runtime, 2),
                'total_requests': self.stats['total_requests'],
                'total_responses': self.stats['total_responses'],
                'requests_per_second': round(req_per_sec, 2),
                'responses_per_second': round(resp_per_sec, 2),
                'error_responses': self.stats['error_responses'],
                'error_rate': f"{error_rate:.2%}",
            }

            if error_rate > 0.1:
                self.logger.warning(f"Health check report: {report}")
            elif error_rate > 0.05:
                self.logger.info(f"Health check report: {report}")
            else:
                self.logger.debug(f"Health check report: {report}")
        except Exception as e:
            self.logger.error(f"Error in health check: {e}")
