#!/usr/bin/python
# -*- coding:UTF-8 -*-
from typing import Optional, Callable

from crawlo.utils.log import get_logger
from crawlo.utils.request import set_request
from crawlo.utils.request_serializer import RequestSerializer
from crawlo.utils.error_handler import ErrorHandler
from crawlo.queue.queue_manager import QueueManager, QueueConfig
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
            success = await self.queue_manager.initialize()
            if not success:
                raise RuntimeError("队列初始化失败")
            
            # 输出队列状态
            status = self.queue_manager.get_status()
            self.logger.info(f'队列类型: {status["type"]}, 状态: {status["health"]}')
            self.logger.info(f'requesting filter: {self.dupe_filter}')
            self.logger.info("调度器初始化完成")
        except Exception as e:
            self.logger.error(f"❌ 调度器初始化失败: {e}")
            self.logger.debug(f"详细错误信息:\n{traceback.format_exc()}")
            raise

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