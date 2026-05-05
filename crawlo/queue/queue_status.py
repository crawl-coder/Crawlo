#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
队列状态查询 Mixin

提供 QueueManager 的状态查询和监控方法。
"""

from typing import Dict, Any
from crawlo.queue.queue_types import QueueType


class QueueStatusMixin:
    """队列状态查询混入类"""

    def get_status(self) -> Dict[str, Any]:
        """Get queue status information"""
        status = {
            "type": self._queue_type.value if self._queue_type else "unknown",  # type: ignore
            "health": self._health_status,  # type: ignore
            "config": self._get_queue_info(),
            "initialized": self._queue is not None  # type: ignore
        }

        # 添加性能统计信息
        performance_stats = {}
        if hasattr(self, '_backpressure_controller') and self._backpressure_controller:  # type: ignore
            performance_stats.update(self._backpressure_controller.get_stats())  # type: ignore

        status['performance'] = performance_stats
        return status

    def get_queue_stats(self) -> Dict[str, Any]:
        """
        获取队列性能统计信息

        Returns:
            dict: 队列性能统计信息
        """
        import asyncio

        stats = {
            'queue_type': self._queue_type.value if self._queue_type else 'unknown',  # type: ignore
            'health_status': self._health_status,  # type: ignore
            'current_queue_size': 0,
            'max_queue_size': self.config.max_queue_size,  # type: ignore
            'backpressure_status': {},
            'priority_calculator_stats': {}
        }

        # 获取队列大小
        try:
            if self._queue:  # type: ignore
                if hasattr(self._queue, 'qsize'):  # type: ignore
                    if asyncio.iscoroutinefunction(self._queue.qsize):  # type: ignore
                        # 异步获取队列大小
                        async def get_size():
                            return await self._queue.qsize()  # type: ignore
                        # 注意：这里不能直接调用异步函数，需要在适当上下文中使用
                        stats['current_queue_size'] = 'async_required'  # 需要在异步上下文中获取
                    else:
                        stats['current_queue_size'] = self._queue.qsize()  # type: ignore
                elif hasattr(self._queue, '__len__'):  # type: ignore
                    stats['current_queue_size'] = len(self._queue)  # type: ignore
        except Exception:
            stats['current_queue_size'] = 'error'

        # 获取背压控制器状态
        if hasattr(self, '_backpressure_controller') and self._backpressure_controller:  # type: ignore
            stats['backpressure_status'] = self._backpressure_controller.get_stats()  # type: ignore

        # 获取优先级计算器统计信息
        if hasattr(self, '_priority_calculator'):  # type: ignore
            stats['priority_calculator_stats'] = {
                'domain_count': len(getattr(self._priority_calculator, 'domain_stats', {})),  # type: ignore
                'url_count': len(getattr(self._priority_calculator, 'url_stats', {})),  # type: ignore
                'response_time_count': len(getattr(self._priority_calculator, 'response_times', {})),  # type: ignore
                'error_count': len(getattr(self._priority_calculator, 'error_counts', {})),  # type: ignore
                'crawl_frequency_count': len(getattr(self._priority_calculator, 'crawl_frequency', {}))  # type: ignore
            }

        # 如果队列是Redis队列，获取其统计信息
        if self._queue_type == QueueType.REDIS and hasattr(self._queue, 'get_stats'):  # type: ignore
            try:
                redis_stats = self._queue.get_stats()  # type: ignore
                stats['redis_queue_stats'] = redis_stats
            except Exception:
                stats['redis_queue_stats'] = 'error'

        # 添加背压控制器的详细状态
        if hasattr(self, '_backpressure_controller'):  # type: ignore
            back_pressure_stats = {
                'back_pressure_status': {
                    'enabled': True,
                    'current_threshold': self._backpressure_controller.backpressure_ratio,  # type: ignore
                    'max_concurrency': self._backpressure_controller.concurrency_limit,  # type: ignore
                    'current_concurrency': self._backpressure_controller.current_concurrency,  # type: ignore
                    'last_adjustment_time': getattr(self._backpressure_controller, 'last_check_time', 0),  # type: ignore
                    'pressure_level': 'high' if self._backpressure_controller.backpressure_active else 'normal'  # type: ignore
                }
            }
            stats.update(back_pressure_stats)

        # 添加优先级计算器的详细统计信息
        if hasattr(self, '_priority_calculator'):  # type: ignore
            intelligent_stats = {
                'priority_calculator_stats_detail': {
                    'domain_frequencies': dict(getattr(self._priority_calculator, 'domain_stats', {})),  # type: ignore
                    'url_patterns': dict(getattr(self._priority_calculator, 'url_stats', {})),  # type: ignore
                    'crawl_depths': {},  # 爬取深度统计（如果有的话）
                    'response_times': dict(getattr(self._priority_calculator, 'response_times', {})),  # type: ignore
                    'error_counts': dict(getattr(self._priority_calculator, 'error_counts', {})),  # type: ignore
                    'content_type_preferences': dict(getattr(self._priority_calculator, 'content_type_preferences', {}))  # type: ignore
                }
            }
            stats.update(intelligent_stats)

        return stats

    def _get_queue_info(self) -> Dict[str, Any]:
        """Get queue configuration information"""
        info = {
            "queue_name": self.config.queue_name,  # type: ignore
            "max_queue_size": self.config.max_queue_size  # type: ignore
        }

        if self._queue_type == QueueType.REDIS:  # type: ignore
            info.update({
                "redis_url": self.config.redis_url,  # type: ignore
                "max_retries": self.config.max_retries,  # type: ignore
                "timeout": self.config.timeout  # type: ignore
            })

        return info
