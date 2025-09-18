#!/usr/bin/python
# -*- coding:UTF-8 -*-
from typing import Optional, Callable
import traceback

from crawlo.utils.log import get_logger
from crawlo.utils.request import set_request
from crawlo.utils.request_serializer import RequestSerializer
from crawlo.utils.error_handler import ErrorHandler
from crawlo.queue.queue_manager import QueueManager, QueueConfig, QueueType
from crawlo.project import load_class, common_call


class Scheduler:
    def __init__(self, crawler, dupe_filter, stats, log_level, priority):
        self.crawler = crawler
        self.queue_manager: Optional[QueueManager] = None
        self.request_serializer = RequestSerializer()  # 专门处理序列化

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
        """初始化调度器和队列"""
        self.logger.info("开始初始化调度器...")
        try:
            # 创建队列配置
            queue_config = QueueConfig.from_settings(self.crawler.settings)
            
            # 创建队列管理器
            self.queue_manager = QueueManager(queue_config)
            
            # 初始化队列
            self.logger.info("开始初始化队列管理器...")
            needs_config_update = await self.queue_manager.initialize()
            
            self.logger.info(f"队列初始化完成，needs_config_update: {needs_config_update}")
            self.logger.info(f"当前队列类型: {self.queue_manager._queue_type}")
            
            # 检查是否需要更新过滤器配置
            if needs_config_update:
                # 如果返回True，说明队列类型发生了变化，需要检查当前队列类型来决定更新方向
                self.logger.info("需要更新配置...")
                if self.queue_manager._queue_type == QueueType.REDIS:
                    self.logger.info("更新为Redis配置...")
                    self._update_filter_config_for_redis()
                else:
                    self.logger.info("更新为内存配置...")
                    self._update_filter_config_if_needed()
            else:
                # 检查是否需要更新配置（即使队列管理器没有要求更新）
                self.logger.debug("检查是否需要更新配置...")
                if self.queue_manager._queue_type == QueueType.REDIS:
                    # 检查当前过滤器是否为内存过滤器
                    current_filter_class = self.crawler.settings.get('FILTER_CLASS', '')
                    if 'memory_filter' in current_filter_class:
                        self.logger.info("检测到需要更新为Redis配置...")
                        self._update_filter_config_for_redis()
                elif self.queue_manager._queue_type == QueueType.MEMORY:
                    # 检查当前过滤器是否为Redis过滤器
                    current_filter_class = self.crawler.settings.get('FILTER_CLASS', '')
                    if 'aioredis_filter' in current_filter_class or 'redis_filter' in current_filter_class:
                        self.logger.info("检测到需要更新为内存配置...")
                        self._update_filter_config_if_needed()
            
            # 只有在确实需要更新配置时才重新创建过滤器实例
            # 检查是否真的进行了配置更新
            filter_updated = (
                (self.queue_manager._queue_type == QueueType.REDIS and 'memory_filter' in self.crawler.settings.get('FILTER_CLASS', '')) or
                (self.queue_manager._queue_type == QueueType.MEMORY and ('aioredis_filter' in self.crawler.settings.get('FILTER_CLASS', '') or 'redis_filter' in self.crawler.settings.get('FILTER_CLASS', '')))
            )
            
            if needs_config_update or filter_updated:
                # 重新创建过滤器实例，确保使用更新后的配置
                self.logger.debug("重新创建过滤器实例...")
                filter_cls = load_class(self.crawler.settings.get('FILTER_CLASS'))
                self.dupe_filter = filter_cls.create_instance(self.crawler)
                self.logger.info(f"✅ 过滤器实例已更新为: {type(self.dupe_filter).__name__}")
            else:
                self.logger.debug("过滤器配置无需更新，跳过重新创建")
            
            # 输出队列状态和配置信息
            status = self.queue_manager.get_status()
            current_filter = self.crawler.settings.get('FILTER_CLASS')
            current_dedup_pipeline = self.crawler.settings.get('DEFAULT_DEDUP_PIPELINE')
            
            self.logger.info(f'队列类型: {status["type"]}, 状态: {status["health"]}')
            self.logger.info(f'当前过滤器: {type(self.dupe_filter).__name__} ({current_filter})')
            self.logger.info(f'当前去重管道: {current_dedup_pipeline}')
            self.logger.info("调度器初始化完成")
        except Exception as e:
            self.logger.error(f"❌ 调度器初始化失败: {e}")
            self.logger.debug(f"详细错误信息:\n{traceback.format_exc()}")
            raise
    
    def _update_filter_config_if_needed(self):
        """如果队列类型切换到内存模式，则更新过滤器配置"""
        if self.queue_manager and self.queue_manager._queue_type == QueueType.MEMORY:
            # 检查当前过滤器是否为Redis过滤器
            current_filter_class = self.crawler.settings.get('FILTER_CLASS', '')
            if 'aioredis_filter' in current_filter_class or 'redis_filter' in current_filter_class:
                # 更新为内存过滤器
                self.crawler.settings.set('FILTER_CLASS', 'crawlo.filters.memory_filter.MemoryFilter')
                self.logger.info("✅ 已更新过滤器配置为内存模式")
            
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
                self.logger.info("✅ 已更新去重管道配置为内存模式")
    
    def _update_filter_config_for_redis(self):
        """如果队列类型是Redis，则更新过滤器配置为Redis实现"""
        if self.queue_manager and self.queue_manager._queue_type == QueueType.REDIS:
            # 检查当前过滤器是否为内存过滤器
            current_filter_class = self.crawler.settings.get('FILTER_CLASS', '')
            if 'memory_filter' in current_filter_class:
                # 更新为Redis过滤器
                self.crawler.settings.set('FILTER_CLASS', 'crawlo.filters.aioredis_filter.AioRedisFilter')
                self.logger.info("✅ 已更新过滤器配置为Redis模式")
            
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
                self.logger.info("✅ 已更新去重管道配置为Redis模式")

    async def next_request(self):
        """获取下一个请求"""
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
                context="获取下一个请求失败", 
                raise_error=False
            )
            return None

    async def enqueue_request(self, request):
        """将请求加入队列"""
        if not request.dont_filter and await common_call(self.dupe_filter.requested, request):
            self.dupe_filter.log_stats(request)
            return False

        if not self.queue_manager:
            self.logger.error("队列管理器未初始化")
            return False

        set_request(request, self.priority)
        
        try:
            # 使用统一的队列接口
            success = await self.queue_manager.put(request, priority=getattr(request, 'priority', 0))
            
            if success:
                self.logger.debug(f"✅ 请求入队成功: {request.url}")
            
            return success
        except Exception as e:
            self.error_handler.handle_error(
                e, 
                context="请求入队失败", 
                raise_error=False
            )
            return False

    def idle(self) -> bool:
        """检查队列是否为空"""
        return len(self) == 0

    async def async_idle(self) -> bool:
        """异步检查队列是否为空（更精确）"""
        if not self.queue_manager:
            return True
        # 使用队列管理器的异步empty方法
        return await self.queue_manager.async_empty()

    async def close(self):
        """关闭调度器"""
        try:
            if isinstance(closed := getattr(self.dupe_filter, 'closed', None), Callable):
                await closed()
            
            if self.queue_manager:
                await self.queue_manager.close()
        except Exception as e:
            self.error_handler.handle_error(
                e, 
                context="关闭调度器失败", 
                raise_error=False
            )

    def __len__(self):
        """获取队列大小"""
        if not self.queue_manager:
            return 0
        # 返回同步的近似值，实际大小需要异步获取
        return 0 if self.queue_manager.empty() else 1