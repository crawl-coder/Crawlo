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
        """Redis监控循环"""
        while True:
            try:
                # 获取Redis相关的统计信息
                redis_stats = {}
                
                # 从stats收集Redis相关指标
                stats_keys = [
                    'redis/requests',
                    'redis/errors',
                    'redis/response_time',
                    'redis/connections_used',
                    'redis/connections_available',
                    'redis/hits',
                    'redis/misses',
                    'redis/queue_length',  # 队列长度
                    'redis/pool_size',  # 连接池大小
                    'redis/pool_free',  # 连接池空闲连接数
                    'redis/timeout_errors',  # 超时错误
                    'redis/connection_errors',  # 连接错误
                    'redis/request_processing_time',  # 请求处理时间
                    'redis/request_queue_time'  # 请求排队时间
                ]
                
                for key in stats_keys:
                    value = self.crawler.stats.get_value(key, 0)
                    redis_stats[key] = value
                
                # 计算平均值指标
                request_count = redis_stats.get('redis/requests', 1)
                response_time_total = redis_stats.get('redis/response_time', 0)
                processing_time_total = redis_stats.get('redis/request_processing_time', 0)
                
                avg_response_time = response_time_total / max(request_count, 1)
                avg_processing_time = processing_time_total / max(request_count, 1)
                
                # 计算命中率
                hits = redis_stats.get('redis/hits', 0)
                misses = redis_stats.get('redis/misses', 0)
                total_requests = hits + misses
                hit_rate = (hits / total_requests * 100) if total_requests > 0 else 0
                
                # 记录连接池使用率到历史数据
                connections_used = redis_stats.get('redis/connections_used', 0)
                pool_size = redis_stats.get('redis/pool_size', 1)
                pool_usage = (connections_used / pool_size * 100) if pool_size > 0 else 0
                self.pool_usage_history.append(pool_usage)
                
                # 限制历史数据大小
                if len(self.pool_usage_history) > self.max_history_points:
                    self.pool_usage_history.pop(0)
                
                # 计算连接池使用趋势
                trend_slope, is_increasing = self._calculate_pool_trend()
                
                # 记录Redis资源使用情况
                if any(v > 0 for k, v in redis_stats.items() if not k.startswith('redis/avg_')):
                    # 检查Redis连接池健康状况
                    connections_used = redis_stats.get('redis/connections_used', 0)
                    pool_size = redis_stats.get('redis/pool_size', 1)
                    pool_usage = (connections_used / pool_size * 100) if pool_size > 0 else 0
                    
                    errors = redis_stats.get('redis/errors', 0)
                    timeout_errors = redis_stats.get('redis/timeout_errors', 0)
                    connection_errors = redis_stats.get('redis/connection_errors', 0)
                    total_ops = redis_stats.get('redis/requests', 0)
                    
                    # 判断是否存在资源问题
                    issues = []
                    if pool_usage > 80:  # 连接池使用率过高
                        issues.append(f"HIGH POOL USAGE ({pool_usage:.2f}%)")
                    if errors > 0 and total_ops > 0 and (errors / total_ops) > 0.05:  # 错误率超过5%
                        issues.append(f"HIGH ERROR RATE ({errors}/{total_ops})")
                    if timeout_errors > 0:  # 出现超时
                        issues.append(f"TIMEOUT ERRORS ({timeout_errors})")
                    if connection_errors > 0:  # 出现连接错误
                        issues.append(f"CONNECTION ERRORS ({connection_errors})")
                    if is_increasing and len(self.pool_usage_history) >= 3:  # 连接池使用率持续增长
                        issues.append(f"POOL USAGE GROWING ({trend_slope:+.2f}%/check)")
                    
                    issue_status = f" [ISSUES: {', '.join(issues)}]" if issues else " [OK]"
                    
                    # 计算增长趋势描述
                    trend_desc = "STABLE" if not is_increasing else f"GROWING({trend_slope:+.2f}%/check)"
                    
                    self.logger.info(
                        f"Redis Connection Pool Tracker{issue_status} - "
                        f"Pool usage: {pool_usage:.2f}%, "
                        f"Trend: {trend_desc}, "
                        f"Avg response time: {avg_response_time:.3f}s, "
                        f"Avg processing time: {avg_processing_time:.3f}s, "
                        f"Hit rate: {hit_rate:.2f}%, "
                        f"Errors: {errors}, "
                        f"Timeouts: {timeout_errors}, "
                        f"Connections: {connections_used}/{pool_size}"
                    )
                    
                    # 如果有严重问题，记录警告
                    critical_issues = [issue for issue in issues if 'HIGH' in issue or 'GROWING' in issue]
                    if critical_issues:
                        self.logger.warning(f"Redis Critical Resource Issues: {', '.join(critical_issues)}")
                
                await asyncio.sleep(self.interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in Redis monitoring: {e}")
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