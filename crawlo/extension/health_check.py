#!/usr/bin/python
# -*- coding:UTF-8 -*-
import asyncio
from typing import Any, Optional, Dict
from datetime import datetime, timedelta

from crawlo.utils.log import get_logger
from crawlo.event import spider_opened, spider_closed, response_received, request_scheduled


class HealthCheckExtension:
    """
    健康检查扩展
    监控爬虫的健康状态，包括响应时间、错误率等指标
    """

    def __init__(self, crawler: Any):
        self.settings = crawler.settings
        self.logger = get_logger(self.__class__.__name__, crawler.settings.get('LOG_LEVEL'))
        
        # 获取配置参数
        self.enabled = self.settings.get_bool('HEALTH_CHECK_ENABLED', True)
        self.check_interval = self.settings.get_int('HEALTH_CHECK_INTERVAL', 60)  # 默认60秒
        
        # 健康状态统计
        self.stats: Dict[str, Any] = {
            'start_time': None,
            'total_requests': 0,
            'total_responses': 0,
            'error_responses': 0,
            'last_check_time': None,
            'response_times': [],  # 存储最近的响应时间
        }
        
        self.task: Optional[asyncio.Task] = None

    @classmethod
    def create_instance(cls, crawler: Any) -> 'HealthCheckExtension':
        # 只有当配置启用时才创建实例
        if not crawler.settings.get_bool('HEALTH_CHECK_ENABLED', True):
            from crawlo.exceptions import NotConfigured
            raise NotConfigured("HealthCheckExtension: HEALTH_CHECK_ENABLED is False")
        
        o = cls(crawler)
        if o.enabled:
            crawler.subscriber.subscribe(o.spider_opened, event=spider_opened)
            crawler.subscriber.subscribe(o.spider_closed, event=spider_closed)
            crawler.subscriber.subscribe(o.response_received, event=response_received)
            crawler.subscriber.subscribe(o.request_scheduled, event=request_scheduled)
        return o

    async def spider_opened(self) -> None:
        """爬虫启动时初始化健康检查"""
        if not self.enabled:
            return
            
        self.stats['start_time'] = datetime.now()
        self.task = asyncio.create_task(self._health_check_loop())
        self.logger.info("Health check extension started.")

    async def spider_closed(self) -> None:
        """爬虫关闭时停止健康检查"""
        if not self.enabled:
            return
            
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        
        # 输出最终健康状态
        await self._check_health()
        self.logger.info("Health check extension stopped.")

    async def request_scheduled(self, request: Any, spider: Any) -> None:
        """记录调度的请求"""
        if not self.enabled:
            return
        self.stats['total_requests'] += 1

    async def response_received(self, response: Any, spider: Any) -> None:
        """记录接收到的响应"""
        if not self.enabled:
            return
            
        self.stats['total_responses'] += 1
        
        # 记录错误响应
        if hasattr(response, 'status_code') and response.status_code >= 400:
            self.stats['error_responses'] += 1

    async def _health_check_loop(self) -> None:
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
            
            # 计算基本统计信息
            runtime = (now_time - self.stats['start_time']).total_seconds() if self.stats['start_time'] else 0
            requests_per_second = self.stats['total_requests'] / runtime if runtime > 0 else 0
            responses_per_second = self.stats['total_responses'] / runtime if runtime > 0 else 0
            
            # 计算错误率
            error_rate = (
                self.stats['error_responses'] / self.stats['total_responses'] 
                if self.stats['total_responses'] > 0 else 0
            )
            
            # 输出健康报告
            health_report = {
                'runtime_seconds': round(runtime, 2),
                'total_requests': self.stats['total_requests'],
                'total_responses': self.stats['total_responses'],
                'requests_per_second': round(requests_per_second, 2),
                'responses_per_second': round(responses_per_second, 2),
                'error_responses': self.stats['error_responses'],
                'error_rate': f"{error_rate:.2%}",
            }
            
            # 根据错误率判断健康状态
            if error_rate > 0.1:  # 错误率超过10%
                self.logger.warning(f"Health check report: {health_report}")
            elif error_rate > 0.05:  # 错误率超过5%
                self.logger.info(f"Health check report: {health_report}")
            else:
                self.logger.debug(f"Health check report: {health_report}")
                
        except Exception as e:
            self.logger.error(f"Error in health check: {e}")