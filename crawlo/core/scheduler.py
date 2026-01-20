#!/usr/bin/python
# -*- coding:UTF-8 -*-
import traceback
from typing import Optional, Callable

from crawlo.logging import get_logger
from crawlo.project import common_call
from crawlo.utils.misc import load_object
from crawlo.utils.request import set_request
from crawlo.utils.error_handler import ErrorHandler
from crawlo.utils.request_serializer import RequestSerializer
from crawlo.queue.queue_manager import QueueManager, QueueConfig, QueueType


class Scheduler:
    def __init__(self, crawler, dupe_filter, stats, priority):
        self.crawler = crawler
        self.queue_manager: Optional[QueueManager] = None
        self.request_serializer = RequestSerializer()

        self.logger = get_logger(self.__class__.__name__)
        self.error_handler = ErrorHandler(self.__class__.__name__)
        self.stats = stats
        self.dupe_filter = dupe_filter
        self.priority = priority

    @classmethod
    def create_instance(cls, crawler):
        # 使用工具模块中的安全获取配置函数
        from crawlo.utils.misc import safe_get_config
        
        # 安全获取FILTER_CLASS设置 - 简化版本
        filter_class = safe_get_config(
            getattr(crawler, 'settings', None), 
            'FILTER_CLASS', 
            'crawlo.filters.memory_filter.MemoryFilter'
        )
        
        # 安全获取DEPTH_PRIORITY设置
        priority = safe_get_config(
            getattr(crawler, 'settings', None), 
            'DEPTH_PRIORITY', 
            0
        )
            
        filter_cls = load_object(filter_class)
        
        o = cls(
            crawler=crawler,
            dupe_filter=filter_cls.create_instance(crawler),
            stats=getattr(crawler, 'stats', None),
            priority=priority
        )
        return o

    async def open(self):
        """Initialize scheduler and queue"""
        self.logger.debug("开始初始化调度器...")
        try:
            # 如果是Redis队列，设置spider_name
            if self.crawler.spider:
                spider_name = getattr(self.crawler.spider, 'name', None)
                if spider_name:
                    # 设置SPIDER_NAME到配置中，以便RedisKeyManager能够获取
                    if hasattr(self.crawler.settings, 'set'):
                        try:
                            self.crawler.settings.set('SPIDER_NAME', spider_name)
                        except Exception:
                            pass
            
            # 创建队列配置
            queue_config = QueueConfig.from_settings(self.crawler.settings)
            
            # 创建队列管理器
            self.queue_manager = QueueManager(queue_config)
            
            # 初始化队列
            needs_config_update = await self.queue_manager.initialize()
            
            # 初始化默认配置值
            queue_type_setting = 'memory'  # 默认值
            current_filter = ''  # 默认值
            concurrency = 8  # 默认值
            delay = 1.0  # 默认值
            
            # 检查是否需要更新过滤器配置
            updated_configs = []
            if needs_config_update:
                # 如果返回True，说明队列类型发生了变化，需要检查当前队列类型来决定更新方向
                if self.queue_manager._queue_type == QueueType.REDIS:
                    self._switch_to_redis_config()
                    updated_configs.append("Redis")
                else:
                    self._switch_to_memory_config()
                    updated_configs.append("内存")
            else:
                # 检查是否需要更新配置（即使队列管理器没有要求更新）
                # 当 QUEUE_TYPE 明确设置为 redis 时，也应该检查配置一致性
                
                # 安全获取配置
                if self.crawler and self.crawler.settings is not None:
                    try:
                        queue_type_setting = self.crawler.settings.get('QUEUE_TYPE', 'memory')
                        current_filter = self.crawler.settings.get('FILTER_CLASS', '')
                        concurrency = self.crawler.settings.get('CONCURRENCY', 8)
                        delay = self.crawler.settings.get('DOWNLOAD_DELAY', 1.0)
                    except Exception:
                        # 使用默认值
                        pass
                
                if queue_type_setting == 'redis' or needs_config_update:
                    updated_configs = self._check_filter_config()
                else:
                    updated_configs = []
            
            # 处理过滤器配置更新
            await self._process_filter_updates(needs_config_update, updated_configs)
            
            # 输出关键的调度器初始化完成信息
            status = self.queue_manager.get_status() if self.queue_manager else {'type': 'unknown', 'health': 'unknown'}
            
            # 获取更新后的过滤器配置
            updated_filter = current_filter
            if self.crawler and self.crawler.settings is not None:
                try:
                    updated_filter = self.crawler.settings.get('FILTER_CLASS', current_filter)
                except Exception:
                    pass
            self.logger.info(f"enabled filters: \n  {updated_filter}")
            
            # 优化日志输出，将多条日志合并为1条关键信息
            if queue_type_setting in ['auto', 'redis'] and updated_configs:
                self.logger.debug(f"Scheduler initialized [Queue type: {status['type']}, Status: {status['health']}, Concurrency: {concurrency}, Delay: {delay}s]")
            else:
                self.logger.debug(f"Scheduler initialized [Queue type: {status['type']}, Status: {status['health']}]")
        except Exception as e:
            self.logger.error(f"Scheduler initialization failed: {e}")
            self.logger.debug(f"Detailed error information:\n{traceback.format_exc()}")
            raise
    
    def _check_filter_config(self):
        """检查并更新过滤器配置"""
        updated_configs = []
        
        # 安全检查queue_manager是否存在
        if not self.queue_manager:
            return updated_configs
            
        # 安全获取FILTER_CLASS配置
        current_filter_class = ''
        if self.crawler and self.crawler.settings is not None:
            try:
                current_filter_class = self.crawler.settings.get('FILTER_CLASS', '')
            except Exception:
                current_filter_class = ''
            
        if self.queue_manager._queue_type == QueueType.REDIS:
            # 检查当前过滤器是否为内存过滤器
            if 'memory_filter' in current_filter_class:
                self._switch_to_redis_config()
                updated_configs.append("Redis")
        elif self.queue_manager._queue_type == QueueType.MEMORY:
            # 检查当前过滤器是否为Redis过滤器
            if 'aioredis_filter' in current_filter_class or 'redis_filter' in current_filter_class:
                self._switch_to_memory_config()
                updated_configs.append("内存")
                
        return updated_configs
    
    async def _process_filter_updates(self, needs_config_update, updated_configs):
        """处理过滤器更新逻辑"""
        # 安全检查queue_manager是否存在
        if not self.queue_manager:
            return
            
        # 安全获取FILTER_CLASS配置
        current_filter_class = ''
        if self.crawler and self.crawler.settings is not None:
            try:
                current_filter_class = self.crawler.settings.get('FILTER_CLASS', '')
            except Exception:
                current_filter_class = ''
        
        filter_matches_queue_type = self._is_filter_matching_queue_type(current_filter_class)
        
        # 只有在配置不匹配且需要更新时才重新创建过滤器实例
        if needs_config_update or not filter_matches_queue_type:
            # 如果需要更新配置，则执行更新
            if needs_config_update:
                # 安全获取FILTER_CLASS配置
                filter_class = 'crawlo.filters.memory_filter.MemoryFilter'
                if self.crawler and self.crawler.settings is not None:
                    try:
                        filter_class = self.crawler.settings.get('FILTER_CLASS', filter_class)
                    except Exception:
                        pass
                
                # 重新创建过滤器实例，确保使用更新后的配置
                filter_cls = load_object(filter_class)
                self.dupe_filter = filter_cls.create_instance(self.crawler)
                
                # 记录警告信息
                original_mode = "standalone" if 'memory_filter' in current_filter_class else "distributed"
                new_mode = "distributed" if self.queue_manager._queue_type == QueueType.REDIS else "standalone"
                if original_mode != new_mode:
                    self.logger.warning(f"runtime mode inconsistency detected: switched from {original_mode} to {new_mode} mode")
            elif not filter_matches_queue_type:
                # 配置不匹配，需要更新
                if self.queue_manager._queue_type == QueueType.REDIS:
                    self._switch_to_redis_config()
                elif self.queue_manager._queue_type == QueueType.MEMORY:
                    self._switch_to_memory_config()
                
                # 安全获取FILTER_CLASS配置
                filter_class = 'crawlo.filters.memory_filter.MemoryFilter'
                if self.crawler and self.crawler.settings is not None:
                    try:
                        filter_class = self.crawler.settings.get('FILTER_CLASS', filter_class)
                    except Exception:
                        pass
                
                # 重新创建过滤器实例
                filter_cls = load_object(filter_class)
                self.dupe_filter = filter_cls.create_instance(self.crawler)
    
    def _is_filter_matching_queue_type(self, current_filter_class):
        """检查过滤器配置是否与队列类型匹配"""
        # 安全检查queue_manager是否存在
        if not self.queue_manager:
            return False
            
        return (
            (self.queue_manager._queue_type == QueueType.REDIS and 
             ('aioredis_filter' in current_filter_class or 'redis_filter' in current_filter_class)) or
            (self.queue_manager._queue_type == QueueType.MEMORY and 
             'memory_filter' in current_filter_class)
        )
    
    def _switch_to_redis_config(self):
        """切换到Redis配置"""
        # 安全检查queue_manager是否存在且类型正确
        if not self.queue_manager or self.queue_manager._queue_type != QueueType.REDIS:
            return
            
        # 安全获取FILTER_CLASS配置
        current_filter_class = ''
        default_dedup_pipeline = ''
        pipelines = []
        
        if self.crawler and self.crawler.settings is not None:
            try:
                current_filter_class = self.crawler.settings.get('FILTER_CLASS', '')
                default_dedup_pipeline = self.crawler.settings.get('DEFAULT_DEDUP_PIPELINE', '')
                pipelines = self.crawler.settings.get('PIPELINES', [])
            except Exception:
                pass
            
        updated_configs = []
        
        if 'memory_filter' in current_filter_class:
            # 更新为Redis过滤器
            if self.crawler and self.crawler.settings is not None:
                try:
                    self.crawler.settings.set('FILTER_CLASS', 'crawlo.filters.aioredis_filter.AioRedisFilter')
                    updated_configs.append("filter")
                except Exception:
                    pass
        
        # 检查当前去重管道是否为内存去重管道
        if 'memory_dedup_pipeline' in default_dedup_pipeline:
            # 更新为Redis去重管道
            if self.crawler and self.crawler.settings is not None:
                try:
                    self.crawler.settings.set('DEFAULT_DEDUP_PIPELINE', 'crawlo.pipelines.redis_dedup_pipeline.RedisDedupPipeline')
                    # 同时更新PIPELINES列表中的去重管道
                    if default_dedup_pipeline in pipelines:
                        # 找到并替换内存去重管道为Redis去重管道
                        index = pipelines.index(default_dedup_pipeline)
                        pipelines[index] = 'crawlo.pipelines.redis_dedup_pipeline.RedisDedupPipeline'
                        self.crawler.settings.set('PIPELINES', pipelines)
                    updated_configs.append("dedup pipeline")
                except Exception:
                    pass
        
        # 合并日志输出
        if updated_configs:
            self.logger.info(f"configuration updated: {', '.join(updated_configs)} -> redis mode")

    def _switch_to_memory_config(self):
        """切换到内存配置"""
        # 安全检查queue_manager是否存在且类型正确
        if not self.queue_manager or self.queue_manager._queue_type != QueueType.MEMORY:
            return
            
        # 安全获取FILTER_CLASS配置
        current_filter_class = ''
        default_dedup_pipeline = ''
        pipelines = []
        
        if self.crawler and self.crawler.settings is not None:
            try:
                current_filter_class = self.crawler.settings.get('FILTER_CLASS', '')
                default_dedup_pipeline = self.crawler.settings.get('DEFAULT_DEDUP_PIPELINE', '')
                pipelines = self.crawler.settings.get('PIPELINES', [])
            except Exception:
                pass
            
        updated_configs = []
        
        if 'aioredis_filter' in current_filter_class or 'redis_filter' in current_filter_class:
            # 更新为内存过滤器
            if self.crawler and self.crawler.settings is not None:
                try:
                    self.crawler.settings.set('FILTER_CLASS', 'crawlo.filters.memory_filter.MemoryFilter')
                    updated_configs.append("filter")
                except Exception:
                    pass
        
        # 检查当前去重管道是否为Redis去重管道
        if 'redis_dedup_pipeline' in default_dedup_pipeline:
            # 更新为内存去重管道
            if self.crawler and self.crawler.settings is not None:
                try:
                    self.crawler.settings.set('DEFAULT_DEDUP_PIPELINE', 'crawlo.pipelines.memory_dedup_pipeline.MemoryDedupPipeline')
                    # 同时更新PIPELINES列表中的去重管道
                    if default_dedup_pipeline in pipelines:
                        # 找到并替换Redis去重管道为内存去重管道
                        index = pipelines.index(default_dedup_pipeline)
                        pipelines[index] = 'crawlo.pipelines.memory_dedup_pipeline.MemoryDedupPipeline'
                        self.crawler.settings.set('PIPELINES', pipelines)
                    updated_configs.append("dedup pipeline")
                except Exception:
                    pass
        
        # 合并日志输出
        if updated_configs:
            self.logger.debug(f"configuration updated: {', '.join(updated_configs)} -> memory mode")

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
            from crawlo.utils.error_handler import ErrorContext
            self.error_handler.handle_error(
                e, 
                context=ErrorContext(context="Failed to get next request"), 
                raise_error=False
            )
            return None

    async def enqueue_request(self, request):
        """Add request to queue"""
        # 修改调度器逻辑以正确处理Redis过滤器
        if not request.dont_filter:
            # 检查过滤器是否为Redis过滤器且有异步方法
            if hasattr(self.dupe_filter, 'requested_async'):
                # 对于Redis过滤器，使用异步方法
                is_duplicate = await self.dupe_filter.requested_async(request)
                if is_duplicate:
                    self.dupe_filter.log_stats(request)
                    return False
            else:
                # 对于其他过滤器，使用同步方法
                is_duplicate = await common_call(self.dupe_filter.requested, request)
                if is_duplicate:
                    self.dupe_filter.log_stats(request)
                    return False

        if not self.queue_manager:
            self.logger.error("Queue manager not initialized")
            return False

        set_request(request, self.priority)
        
        try:
            # 使用统一的队列接口
            success = await self.queue_manager.put(request, priority=getattr(request, 'priority', 0))
            
            # 更新智能调度器的统计信息
            if hasattr(self.queue_manager, '_intelligent_scheduler'):
                self.queue_manager._intelligent_scheduler.update_crawl_frequency(request)
            
            if success:
                self.logger.debug(f"Request enqueued successfully: {request.url}")
            
            return success
        except Exception as e:
            from crawlo.utils.error_handler import ErrorContext
            self.error_handler.handle_error(
                e, 
                context=ErrorContext(context="Failed to enqueue request"), 
                raise_error=False
            )
            return False

    def idle(self) -> bool:
        """Check if queue is empty - 使用同步方法快速判断"""
        if not self.queue_manager:
            return True
        # 尝试使用同步方法判断，如果不可靠则返回False（假定队列非空）以确保准确性
        try:
            # 检查内存队列，同步方法比较可靠
            if hasattr(self.queue_manager, '_queue_type') and \
               self.queue_manager._queue_type == QueueType.MEMORY:
                return self.queue_manager.empty()
            else:
                # 对于Redis队列，同步empty方法不太可靠，所以返回False让系统使用异步方法
                # 这是为了避免在Redis队列场景下错误地认为队列为空
                return False
        except Exception:
            return True

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
            from crawlo.utils.error_handler import ErrorContext
            self.error_handler.handle_error(
                e, 
                context=ErrorContext(context="Failed to close scheduler"), 
                raise_error=False
            )

    async def ack_request(self, request):
        """确认请求处理完成"""
        # 由于我们不再使用处理队列，ack_request方法现在是一个空操作
        # 任务在从主队列取出时就已经被认为是完成的
        self.logger.debug(f"任务确认完成: {getattr(request, 'url', 'Unknown URL')}")

    def __len__(self):
        """Get queue size - 同步方法，仅作为近似值"""
        if not self.queue_manager:
            return 0
        # 由于queue_manager.size()是异步方法，在同步__len__方法中无法直接调用
        # 因此只能使用同步的empty()方法来判断是否为空
        # 这是一个近似值，主要用于idle()方法的判断
        if self.queue_manager.empty():
            return 0
        else:
            # 不能确定具体的大小，返回1作为非空的指示
            # 实际大小应通过异步方法获取
            return 1