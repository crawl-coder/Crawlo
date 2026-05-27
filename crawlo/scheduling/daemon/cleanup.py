"""
资源清理模块
负责调度器停止时的资源清理逻辑
"""

import asyncio
import logging
from typing import Any, Optional

from crawlo.logging import get_logger


class ResourceCleanup:
    """资源清理器"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or get_logger("SchedulerCleanup")
    
    async def cleanup_all(self, resource_manager, monitor_task, running_tasks):
        """执行所有资源清理
        
        Args:
            resource_manager: 资源管理器
            monitor_task: 资源监控任务
            running_tasks: 运行中的任务集合
        """
        self.logger.info("正在清理定时任务调度器资源...")
        
        # 停止资源监控任务
        await self._stop_monitor_task(monitor_task)
        
        # 等待运行中的任务完成
        await self._wait_for_tasks(running_tasks)
        
        # 清理资源管理器
        await self._cleanup_resources(resource_manager)
        
        # 清理监控管理器
        await self._cleanup_monitor_manager()
        
        # 清理数据库连接池
        await self._cleanup_databases()
        
        self.logger.info("定时任务调度器资源清理完成")
    
    async def _stop_monitor_task(self, monitor_task):
        """停止资源监控任务"""
        if monitor_task and not monitor_task.done():
            monitor_task.cancel()
            try:
                await monitor_task
            except asyncio.CancelledError:
                pass
            self.logger.info("资源监控任务已停止")
    
    async def _wait_for_tasks(self, running_tasks):
        """等待运行中的任务完成"""
        if running_tasks:
            self.logger.info(f"等待 {len(running_tasks)} 个任务完成...")
            try:
                await asyncio.wait_for(
                    asyncio.gather(*running_tasks, return_exceptions=True),
                    timeout=30.0
                )
                self.logger.info("所有任务已完成")
            except asyncio.TimeoutError:
                self.logger.warning("部分任务未能在超时时间内完成，强制停止")
                for task in running_tasks:
                    if not task.done():
                        task.cancel()
    
    async def _cleanup_resources(self, resource_manager):
        """清理资源管理器"""
        try:
            await resource_manager.cleanup_all()
            self.logger.info("资源清理完成")
        except Exception as e:
            self.logger.error(f"资源清理失败: {e}")
    
    async def _cleanup_monitor_manager(self):
        """清理监控管理器"""
        try:
            from crawlo.extension.monitor.monitor_manager import monitor_manager
            monitor_manager.cleanup()
            self.logger.info("监控管理器清理完成")
        except Exception as e:
            self.logger.error(f"监控管理器清理失败: {e}")
    
    async def _cleanup_databases(self):
        """清理数据库连接池"""
        try:
            from crawlo.utils.db.mysql_connection_pool import close_all_mysql_pools
            from crawlo.utils.redis import close_all_pools as close_all_redis_pools
            from crawlo.utils.db.mongo_connection_pool import close_all_mongo_clients
            
            # 清理MySQL连接池
            await close_all_mysql_pools()
            self.logger.info("MySQL连接池已清理")
            
            # 清理Redis连接池
            await close_all_redis_pools()
            self.logger.info("Redis连接池已清理")
            
            # 清理MongoDB连接池
            await close_all_mongo_clients()
            self.logger.info("MongoDB连接池已清理")
            
        except Exception as e:
            self.logger.error(f"数据库连接池清理失败: {e}")
