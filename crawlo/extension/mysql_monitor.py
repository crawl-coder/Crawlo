#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
MySQL监控扩展
监控MySQL连接池和执行性能
"""
import asyncio
from typing import Any, Optional, Dict

from crawlo.logging import get_logger
from crawlo.event import CrawlerEvent
from crawlo.utils.monitor_manager import monitor_manager
from crawlo.utils.mysql_connection_pool import (
    AiomysqlConnectionPoolManager,
    AsyncmyConnectionPoolManager
)


class MySQLMonitorExtension:
    """
    MySQL监控扩展
    监控MySQL连接池状态和SQL执行性能
    """

    def __init__(self, crawler: Any):
        self.task: Optional[asyncio.Task] = None
        self.crawler = crawler
        self.settings = crawler.settings
        self.logger = get_logger(self.__class__.__name__)
        
        # 获取配置参数
        self.interval = self.settings.get_int('MYSQL_MONITOR_INTERVAL', 60)  # 默认60秒检查一次
        self.enabled = self.settings.get_bool('MYSQL_MONITOR_ENABLED', False)
        
        # 监控管理器
        self.monitor_manager = monitor_manager
        self.monitor_type = 'mysql_monitor'
        
        # 连接池使用趋势追踪
        self.pool_usage_history = []  # 存储连接池使用率历史
        self.max_history_points = 50  # 最大历史记录点数
        
        if self.enabled:
            self.logger.info(f"MySQL monitor initialized. Interval: {self.interval}s")

    @classmethod
    def create_instance(cls, crawler: Any) -> 'MySQLMonitorExtension':
        # 只有当配置启用时才创建实例
        if not crawler.settings.get_bool('MYSQL_MONITOR_ENABLED', False):
            from crawlo.exceptions import NotConfigured
            from crawlo.logging import get_logger
            logger = get_logger(cls.__name__)
            logger.info("MySQLMonitorExtension: MYSQL_MONITOR_ENABLED is False, skipping initialization")
            raise NotConfigured("MySQLMonitorExtension: MYSQL_MONITOR_ENABLED is False")
        
        # 检查是否已有MySQL监控实例在运行
        existing_monitor = monitor_manager.get_monitor('mysql_monitor')
        if existing_monitor is not None:
            # 如果已有实例在运行，返回一个不执行任何操作的实例
            o = cls(crawler)
            o.enabled = False  # 禁用此实例的实际监控功能
            return o
        
        o = cls(crawler)
        # 注册监控实例到管理器
        registered = monitor_manager.register_monitor('mysql_monitor', o)
        if registered:
            # 只有在成功注册后才订阅事件
            crawler.subscriber.subscribe(o.spider_opened, event=CrawlerEvent.SPIDER_OPENED)
            crawler.subscriber.subscribe(o.spider_closed, event=CrawlerEvent.SPIDER_CLOSED)
        return o

    async def spider_opened(self) -> None:
        """爬虫启动时开始监控"""
        # 检查是否已经有一个监控实例在运行
        if not self.enabled or monitor_manager.get_monitor('mysql_monitor') != self:
            # 如果此实例不是主要监控实例，则不启动监控
            return
            
        try:
            self.task = asyncio.create_task(self._monitor_loop())
            self.logger.info(f"MySQL monitor started. Interval: {self.interval}s")
        except Exception as e:
            self.logger.error(f"Failed to start MySQL monitor: {e}")

    async def spider_closed(self) -> None:
        """爬虫关闭时停止监控"""
        # 只有主要监控实例才处理关闭
        if monitor_manager.get_monitor('mysql_monitor') == self:
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
                monitor_manager.unregister_monitor('mysql_monitor')
                self.logger.info("MySQL monitor stopped.")
            else:
                # 是调度任务，暂停监控（保持实例）
                self.logger.info("MySQL monitor paused (will resume with next spider).")

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
        """MySQL监控循环 - 监控连接池资源泄露和性能指标"""
        while True:
            try:
                # 获取MySQL连接池使用率
                pool_usage = self.crawler.stats.get_value('mysql/pool_usage_percent', 0)
                
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
                            f"MySQL连接池泄露警告 - 使用率持续增长: {trend_slope:+.2f}%/检查, "
                            f"当前使用率: {pool_usage:.2f}%"
                        )
                
                # 获取其他性能指标（用于趋势分析，不输出日志）
                self._collect_performance_metrics()
                
                await asyncio.sleep(self.interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"MySQL监控错误: {e}")
                await asyncio.sleep(self.interval)

    def _collect_performance_metrics(self) -> Dict[str, Any]:
        """收集MySQL性能指标（用于资源泄露分析）"""
        stats = self.crawler.stats
        
        # 连接池相关指标
        metrics = {
            'pool_usage': stats.get_value('mysql/pool_usage_percent', 0),
            'connection_acquire_time': stats.get_value('mysql/connection_acquire_time', 0),
            
            # 执行性能指标
            'sql_execution_time': stats.get_value('mysql/sql_execution_time', 0),
            'batch_execution_time': stats.get_value('mysql/batch_execution_time', 0),
            
            # 操作计数
            'insert_success': stats.get_value('mysql/insert_success', 0),
            'insert_failed': stats.get_value('mysql/insert_failed', 0),
            'rows_requested': stats.get_value('mysql/rows_requested', 0),
            'rows_affected': stats.get_value('mysql/rows_affected', 0),
            'rows_ignored': stats.get_value('mysql/rows_ignored_by_duplicate', 0),
            
            # 重试和失败计数
            'retry_count': stats.get_value('mysql/retry_count', 0),
            'batch_retry_count': stats.get_value('mysql/batch_retry_count', 0),
            'batch_failure_count': stats.get_value('mysql/batch_failure_count', 0),
            'batch_insert_success': stats.get_value('mysql/batch_insert_success', 0),
        }
        
        # 计算失败率（如果有操作）
        total_operations = metrics['insert_success'] + metrics['insert_failed']
        if total_operations > 0:
            metrics['failure_rate'] = (metrics['insert_failed'] / total_operations) * 100
        else:
            metrics['failure_rate'] = 0
        
        # 计算重试率
        total_batches = metrics['batch_insert_success'] + metrics['batch_failure_count']
        if total_batches > 0:
            metrics['retry_rate'] = (metrics['batch_retry_count'] / total_batches) * 100
        else:
            metrics['retry_rate'] = 0
        
        # 检查异常指标（高失败率或高重试率）
        if metrics['failure_rate'] > 10:  # 失败率超过10%
            self.logger.warning(
                f"MySQL高失败率警告 - 失败率: {metrics['failure_rate']:.1f}%, "
                f"成功: {metrics['insert_success']}, 失败: {metrics['insert_failed']}"
            )
        
        if metrics['retry_rate'] > 20:  # 重试率超过20%
            self.logger.warning(
                f"MySQL高重试率警告 - 重试率: {metrics['retry_rate']:.1f}%, "
                f"重试次数: {metrics['batch_retry_count']}"
            )
        
        # 检查连接获取延迟（可能表示连接池紧张）
        if metrics['connection_acquire_time'] > 5:  # 超过5秒
            self.logger.warning(
                f"MySQL连接获取延迟过高 - 等待时间: {metrics['connection_acquire_time']:.2f}s, "
                f"连接池使用率: {metrics['pool_usage']:.1f}%"
            )
        
        # 获取详细的连接池状态
        self._check_detailed_pool_status()
        
        return metrics
    
    def _check_detailed_pool_status(self) -> None:
        """检查详细的连接池状态"""
        # 获取aiomysql连接池统计
        aiomysql_stats = AiomysqlConnectionPoolManager.get_pool_stats()
        asyncmy_stats = AsyncmyConnectionPoolManager.get_pool_stats()
        
        # 合并两个驱动的连接池信息
        all_pools = {}
        all_pools.update(aiomysql_stats.get('pools', {}))
        all_pools.update(asyncmy_stats.get('pools', {}))
        
        if not all_pools:
            return
        
        for pool_key, pool_info in all_pools.items():
            size = pool_info.get('size', 0)
            freesize = pool_info.get('freesize', 0)
            used = pool_info.get('used', 0)
            maxsize = pool_info.get('maxsize', 0)
            minsize = pool_info.get('minsize', 0)
            usage_percent = pool_info.get('usage_percent', 0)
            
            # 连接池使用率过高警告（超过90%）
            if usage_percent > 90:
                self.logger.warning(
                    f"MySQL连接池 [{pool_key}] 使用率过高 - "
                    f"已使用: {used}/{maxsize} ({usage_percent:.1f}%), "
                    f"空闲: {freesize}, 最小: {minsize}"
                )
            
            # 连接池耗尽警告（空闲为0且使用率达到100%）
            if freesize == 0 and usage_percent >= 100:
                self.logger.warning(
                    f"MySQL连接池 [{pool_key}] 已耗尽 - "
                    f"所有 {maxsize} 个连接都在使用中，无空闲连接可用"
                )
            
            # 连接数低于最小值（可能连接泄露）
            if size < minsize:
                self.logger.warning(
                    f"MySQL连接池 [{pool_key}] 连接数低于最小值 - "
                    f"当前: {size}, 最小: {minsize}, 可能连接泄露"
                )


def create_mysql_monitor(crawler: Any) -> Optional[MySQLMonitorExtension]:
    """
    便捷函数：创建MySQL监控器（如果启用）
    
    Args:
        crawler: 爬虫实例
        
    Returns:
        MySQLMonitorExtension实例或None
    """
    if crawler.settings.get_bool('MYSQL_MONITOR_ENABLED', False):
        return MySQLMonitorExtension(crawler)
    return None