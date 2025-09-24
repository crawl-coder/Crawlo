#!/usr/bin/python
# -*- coding:UTF-8 -*-
import traceback
from typing import Optional, Callable

from crawlo.utils.log import get_logger
from crawlo.utils.request import set_request
from crawlo.utils.error_handler import ErrorHandler
from crawlo.utils.class_loader import load_class
from crawlo.project import common_call
from crawlo.utils.request_serializer import RequestSerializer
from crawlo.queue.queue_manager import QueueManager, QueueConfig, QueueType


class Scheduler:
    def __init__(self, crawler, dupe_filter, stats, log_level, priority):
        self.crawler = crawler
        self.queue_manager: Optional[QueueManager] = None
        self.request_serializer = RequestSerializer()

        self.logger = get_logger(name=self.__class__.__name__, level=log_level)
        self.error_handler = ErrorHandler(self.__class__.__name__, log_level)
        self.stats = stats
        self.dupe_filter = dupe_filter
        self.priority = priority

    @classmethod
    def create_instance(cls, crawler):
        filter_cls = load_class(crawler.settings.get('FILTER_CLASS'))
        o = cls(
            crawler=crawler,
            dupe_filter=filter_cls.create_instance(crawler),
            stats=crawler.stats,
            log_level=crawler.settings.get('LOG_LEVEL'),
            priority=crawler.settings.get('DEPTH_PRIORITY')
        )
        return o

    async def open(self):
        """Initialize scheduler and queue"""
        self.logger.debug("开始初始化调度器...")
        try:
            # 创建队列配置
            queue_config = QueueConfig.from_settings(self.crawler.settings)
            
            # 创建队列管理器
            self.queue_manager = QueueManager(queue_config)
            
            # 初始化队列
            needs_config_update = await self.queue_manager.initialize()
            
            # 检查是否需要更新过滤器配置
            updated_configs = []
            if needs_config_update:
                # 如果返回True，说明队列类型发生了变化，需要检查当前队列类型来决定更新方向
                if self.queue_manager._queue_type == QueueType.REDIS:
                    self._update_filter_config_for_redis()
                    updated_configs.append("Redis")
                else:
                    self._update_filter_config_if_needed()
                    updated_configs.append("内存")
            else:
                # 检查是否需要更新配置（即使队列管理器没有要求更新）
                if self.queue_manager._queue_type == QueueType.REDIS:
                    # 检查当前过滤器是否为内存过滤器
                    current_filter_class = self.crawler.settings.get('FILTER_CLASS', '')
                    if 'memory_filter' in current_filter_class:
                        self._update_filter_config_for_redis()
                        updated_configs.append("Redis")
                elif self.queue_manager._queue_type == QueueType.MEMORY:
                    # 检查当前过滤器是否为Redis过滤器
                    current_filter_class = self.crawler.settings.get('FILTER_CLASS', '')
                    if 'aioredis_filter' in current_filter_class or 'redis_filter' in current_filter_class:
                        self._update_filter_config_if_needed()
                        updated_configs.append("内存")
            
            # 只有在确实需要更新配置时才重新创建过滤器实例
            # 检查是否真的进行了配置更新
            filter_updated = (
                (self.queue_manager._queue_type == QueueType.REDIS and 'memory_filter' in self.crawler.settings.get('FILTER_CLASS', '')) or
                (self.queue_manager._queue_type == QueueType.MEMORY and ('aioredis_filter' in self.crawler.settings.get('FILTER_CLASS', '') or 'redis_filter' in self.crawler.settings.get('FILTER_CLASS', '')))
            )
            
            if needs_config_update or filter_updated:
                # 重新创建过滤器实例，确保使用更新后的配置
                filter_cls = load_class(self.crawler.settings.get('FILTER_CLASS'))
                self.dupe_filter = filter_cls.create_instance(self.crawler)
                
                # 如果配置被更新，记录警告信息
                if filter_updated:
                    original_mode = "distributed" if 'memory_filter' in self.crawler.settings.get('FILTER_CLASS', '') else "standalone"
                    new_mode = "standalone" if self.queue_manager._queue_type == QueueType.MEMORY else "distributed"
                    self.logger.warning(f"runtime mode inconsistency detected: switched from {original_mode} to {new_mode} mode")
            
            # 输出关键的调度器初始化完成信息
            status = self.queue_manager.get_status()
            current_filter = self.crawler.settings.get('FILTER_CLASS')
            
            # 输出启用的过滤器信息（类似Downloader的格式）
            self.logger.info(f"enabled filters: \n  {current_filter}")  # 注释掉重复的日志
            
            # 优化日志输出，将多条日志合并为1条关键信息
            # 显示完整路径的过滤器类名
            if self.crawler.settings.get('QUEUE_TYPE', 'memory') == 'auto' and updated_configs:
                concurrency = self.crawler.settings.get('CONCURRENCY', 8)
                delay = self.crawler.settings.get('DOWNLOAD_DELAY', 1.0)
                # Change INFO level log to DEBUG level to avoid redundant output
                self.logger.debug(f"Scheduler initialized [Queue type: {status['type']}, Status: {status['health']}, Concurrency: {concurrency}, Delay: {delay}s]")
            else:
                # Change INFO level log to DEBUG level to avoid redundant output
                self.logger.debug(f"Scheduler initialized [Queue type: {status['type']}, Status: {status['health']}]")
        except Exception as e:
            self.logger.error(f"Scheduler initialization failed: {e}")
            self.logger.debug(f"Detailed error information:\n{traceback.format_exc()}")
            raise
    
    def _update_filter_config_if_needed(self):
        """Update filter configuration if queue type switches to memory mode"""
        if self.queue_manager and self.queue_manager._queue_type == QueueType.MEMORY:
            # 检查当前过滤器是否为Redis过滤器
            current_filter_class = self.crawler.settings.get('FILTER_CLASS', '')
            updated_configs = []
            
            if 'aioredis_filter' in current_filter_class or 'redis_filter' in current_filter_class:
                # 更新为内存过滤器
                self.crawler.settings.set('FILTER_CLASS', 'crawlo.filters.memory_filter.MemoryFilter')
                updated_configs.append("filter")
            
            # 检查当前去重管道是否为Redis去重管道
            current_dedup_pipeline = self.crawler.settings.get('DEFAULT_DEDUP_PIPELINE', '')
            if 'redis_dedup_pipeline' in current_dedup_pipeline:
                # 更新为内存去重管道
                self.crawler.settings.set('DEFAULT_DEDUP_PIPELINE', 'crawlo.pipelines.memory_dedup_pipeline.MemoryDedupPipeline')
                # 同时更新PIPELINES列表中的去重管道
                pipelines = self.crawler.settings.get('PIPELINES', [])
                if current_dedup_pipeline in pipelines:
                    # 找到并替换Redis去重管道为内存去重管道
                    index = pipelines.index(current_dedup_pipeline)
                    pipelines[index] = 'crawlo.pipelines.memory_dedup_pipeline.MemoryDedupPipeline'
                    self.crawler.settings.set('PIPELINES', pipelines)
                updated_configs.append("dedup pipeline")
            
            # 合并日志输出
            if updated_configs:
                self.logger.debug(f"configuration updated: {', '.join(updated_configs)} -> memory mode")

    def _update_filter_config_for_redis(self):
        """Update filter configuration to Redis implementation if queue type is Redis"""
        if self.queue_manager and self.queue_manager._queue_type == QueueType.REDIS:
            # 检查当前过滤器是否为内存过滤器
            current_filter_class = self.crawler.settings.get('FILTER_CLASS', '')
            updated_configs = []
            
            if 'memory_filter' in current_filter_class:
                # 更新为Redis过滤器
                self.crawler.settings.set('FILTER_CLASS', 'crawlo.filters.aioredis_filter.AioRedisFilter')
                updated_configs.append("filter")
            
            # 检查当前去重管道是否为内存去重管道
            current_dedup_pipeline = self.crawler.settings.get('DEFAULT_DEDUP_PIPELINE', '')
            if 'memory_dedup_pipeline' in current_dedup_pipeline:
                # 更新为Redis去重管道
                self.crawler.settings.set('DEFAULT_DEDUP_PIPELINE', 'crawlo.pipelines.redis_dedup_pipeline.RedisDedupPipeline')
                # 同时更新PIPELINES列表中的去重管道
                pipelines = self.crawler.settings.get('PIPELINES', [])
                if current_dedup_pipeline in pipelines:
                    # 找到并替换内存去重管道为Redis去重管道
                    index = pipelines.index(current_dedup_pipeline)
                    pipelines[index] = 'crawlo.pipelines.redis_dedup_pipeline.RedisDedupPipeline'
                    self.crawler.settings.set('PIPELINES', pipelines)
                updated_configs.append("dedup pipeline")
            
            # 合并日志输出
            if updated_configs:
                self.logger.info(f"configuration updated: {', '.join(updated_configs)} -> redis mode")

    async def next_request(self):
        """Get next request"""
        if not self.queue_manager:
            return None
            
        try:
            request = await self.queue_manager.get()
            
            # 恢复 callback（从 Redis 队列取出时）
            if request:
                spider = getattr(self.crawler, 'spider', None)
                request = self.request_serializer.restore_after_deserialization(request, spider)
            
            return request
        except Exception as e:
            self.error_handler.handle_error(
                e, 
                context="Failed to get next request", 
                raise_error=False
            )
            return None

    async def enqueue_request(self, request):
        """Add request to queue"""
        if not request.dont_filter and await common_call(self.dupe_filter.requested, request):
            self.dupe_filter.log_stats(request)
            return False

        if not self.queue_manager:
            self.logger.error("Queue manager not initialized")
            return False

        set_request(request, self.priority)
        
        try:
            # 使用统一的队列接口
            success = await self.queue_manager.put(request, priority=getattr(request, 'priority', 0))
            
            if success:
                self.logger.debug(f"Request enqueued successfully: {request.url}")
            
            return success
        except Exception as e:
            self.error_handler.handle_error(
                e, 
                context="Failed to enqueue request", 
                raise_error=False
            )
            return False

    def idle(self) -> bool:
        """Check if queue is empty"""
        return len(self) == 0

    async def async_idle(self) -> bool:
        """Asynchronously check if queue is empty (more accurate)"""
        if not self.queue_manager:
            return True
        # 使用队列管理器的异步empty方法
        return await self.queue_manager.async_empty()

    async def close(self):
        """Close scheduler"""
        try:
            if isinstance(closed := getattr(self.dupe_filter, 'closed', None), Callable):
                await closed()
            
            if self.queue_manager:
                await self.queue_manager.close()
        except Exception as e:
            self.error_handler.handle_error(
                e, 
                context="Failed to close scheduler", 
                raise_error=False
            )

    def __len__(self):
        """Get queue size"""
        if not self.queue_manager:
            return 0
        # 返回同步的近似值，实际大小需要异步获取
        return 0 if self.queue_manager.empty() else 1