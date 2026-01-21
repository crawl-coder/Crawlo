#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
MySQL监控扩展
监控MySQL连接池和执行性能
"""
import asyncio
from typing import Any, Optional

from crawlo.logging import get_logger
from crawlo.event import CrawlerEvent
from crawlo.utils.monitor_manager import monitor_manager


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
        """MySQL监控循环"""
        while True:
            try:
                # 获取MySQL相关的统计信息
                mysql_stats = {}
                
                # 从stats收集MySQL相关指标
                stats_keys = [
                    'mysql/pool_usage_percent',
                    'mysql/sql_execution_time',
                    'mysql/batch_execution_time',
                    'mysql/connection_acquire_time',
                    'mysql/insert_success',
                    'mysql/insert_failed',
                    'mysql/batch_insert_success',
                    'mysql/batch_insert_failed',
                    'mysql/retry_count',
                    'mysql/batch_retry_count',
                    'mysql/pool_repaired',  # 连接池修复次数
                    'mysql/pool_health_checks',  # 健康检查次数
                    'mysql/rows_affected',  # 影响行数
                    'mysql/rows_requested',  # 请求行数
                    'mysql/rows_ignored_by_duplicate',  # 因重复被忽略的行数
                    'mysql/batch_failure_count',  # 批量执行失败次数
                    'mysql/sql_execution_count',  # SQL执行次数
                    'mysql/batch_execution_count',  # 批量执行次数
                    'mysql/connection_acquire_time_count'  # 连接获取次数
                ]
                
                for key in stats_keys:
                    value = self.crawler.stats.get_value(key, 0)
                    mysql_stats[key] = value
                
                # 计算平均值指标
                sql_execution_count = mysql_stats.get('mysql/sql_execution_count', 1)
                batch_execution_count = mysql_stats.get('mysql/batch_execution_count', 1)
                acquire_count = mysql_stats.get('mysql/connection_acquire_time_count', 1)
                
                avg_sql_time = mysql_stats.get('mysql/sql_execution_time', 0) / max(sql_execution_count, 1)
                avg_batch_time = mysql_stats.get('mysql/batch_execution_time', 0) / max(batch_execution_count, 1)
                avg_acquire_time = mysql_stats.get('mysql/connection_acquire_time', 0) / max(acquire_count, 1)
                
                # 记录连接池使用率到历史数据
                current_pool_usage = mysql_stats.get('mysql/pool_usage_percent', 0)
                self.pool_usage_history.append(current_pool_usage)
                
                # 限制历史数据大小
                if len(self.pool_usage_history) > self.max_history_points:
                    self.pool_usage_history.pop(0)
                
                # 计算连接池使用趋势
                trend_slope, is_increasing = self._calculate_pool_trend()
                
                # 记录MySQL资源使用情况
                if any(v > 0 for k, v in mysql_stats.items() if not k.endswith('_success') and not k.endswith('_failed')):
                    # 检查连接池健康状况
                    pool_usage_avg = mysql_stats.get('mysql/pool_usage_percent', 0)
                    retry_count = mysql_stats.get('mysql/retry_count', 0)
                    batch_retry_count = mysql_stats.get('mysql/batch_retry_count', 0)
                    pool_repaired = mysql_stats.get('mysql/pool_repaired', 0)
                    failed_ops = mysql_stats.get('mysql/insert_failed', 0) + mysql_stats.get('mysql/batch_insert_failed', 0)
                    total_ops = mysql_stats.get('mysql/insert_success', 0) + mysql_stats.get('mysql/batch_insert_success', 0) + failed_ops
                    
                    # 判断是否存在资源问题
                    issues = []
                    if pool_usage_avg > 80:  # 连接池使用率过高
                        issues.append(f"HIGH POOL USAGE ({pool_usage_avg:.2f}%)")
                    if retry_count > 0 or batch_retry_count > 0:  # 出现重试
                        issues.append(f"RETRY NEEDED ({retry_count}+{batch_retry_count})")
                    if pool_repaired > 0:  # 连接池被修复
                        issues.append(f"POOL REPAIRED ({pool_repaired})")
                    if failed_ops > 0 and total_ops > 0 and (failed_ops / total_ops) > 0.1:  # 失败率超过10%
                        issues.append(f"HIGH FAILURE RATE ({failed_ops}/{total_ops})")
                    if is_increasing and len(self.pool_usage_history) >= 3:  # 连接池使用率持续增长
                        issues.append(f"POOL USAGE GROWING ({trend_slope:+.2f}%/check)")
                    
                    issue_status = f" [ISSUES: {', '.join(issues)}]" if issues else " [OK]"
                    
                    # 计算增长趋势描述
                    trend_desc = "STABLE" if not is_increasing else f"GROWING({trend_slope:+.2f}%/check)"
                    
                    self.logger.info(
                        f"MySQL Connection Pool Tracker{issue_status} - "
                        f"Pool usage: {pool_usage_avg:.2f}%, "
                        f"Trend: {trend_desc}, "
                        f"Avg SQL time: {avg_sql_time:.3f}s, "
                        f"Avg batch time: {avg_batch_time:.3f}s, "
                        f"Retries: {retry_count}(SQL)+{batch_retry_count}(Batch), "
                        f"Repaired: {pool_repaired}, "
                        f"Failures: {failed_ops}/{total_ops}"
                    )
                    
                    # 如果有严重问题，记录警告
                    critical_issues = [issue for issue in issues if 'HIGH' in issue or 'GROWING' in issue or 'POOL REPAIRED' in issue]
                    if critical_issues:
                        self.logger.warning(f"MySQL Critical Resource Issues: {', '.join(critical_issues)}")
                
                await asyncio.sleep(self.interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in MySQL monitoring: {e}")
                await asyncio.sleep(self.interval)


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