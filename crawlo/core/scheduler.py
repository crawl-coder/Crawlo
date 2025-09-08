#!/usr/bin/python
# -*- coding:UTF-8 -*-
from typing import Optional, Callable

from crawlo.utils.log import get_logger
from crawlo.utils.request import set_request
from crawlo.utils.request_serializer import RequestSerializer
from crawlo.queue.queue_manager import QueueManager, QueueConfig
from crawlo.project import load_class, common_call


class Scheduler:
    def __init__(self, crawler, dupe_filter, stats, log_level, priority):
        self.crawler = crawler
        self.queue_manager: Optional[QueueManager] = None
        self.request_serializer = RequestSerializer()  # 专门处理序列化

        self.logger = get_logger(name=self.__class__.__name__, level=log_level)
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
        # 创建队列配置
        queue_config = QueueConfig.from_settings(self.crawler.settings)
        
        # 创建队列管理器
        self.queue_manager = QueueManager(queue_config)
        
        # 初始化队列
        success = await self.queue_manager.initialize()
        if not success:
            raise RuntimeError("队列初始化失败")
        
        # 输出队列状态
        status = self.queue_manager.get_status()
        self.logger.info(f'队列类型: {status["type"]}, 状态: {status["health"]}')
        self.logger.info(f'requesting filter: {self.dupe_filter}')

    async def next_request(self):
        """获取下一个请求"""
        if not self.queue_manager:
            return None
            
        request = await self.queue_manager.get()
        
        # 恢复 callback（从 Redis 队列取出时）
        if request:
            spider = getattr(self.crawler, 'spider', None)
            request = self.request_serializer.restore_after_deserialization(request, spider)
            
        return request

    async def enqueue_request(self, request):
        """将请求加入队列"""
        if not request.dont_filter and await common_call(self.dupe_filter.requested, request):
            self.dupe_filter.log_stats(request)
            return False

        if not self.queue_manager:
            self.logger.error("队列管理器未初始化")
            return False

        set_request(request, self.priority)
        
        # 使用统一的队列接口
        success = await self.queue_manager.put(request, priority=getattr(request, 'priority', 0))
        
        if success:
            self.logger.debug(f"✅ 请求入队成功: {request.url}")
        
        return success

    def idle(self) -> bool:
        """检查队列是否为空"""
        return len(self) == 0

    async def close(self):
        """关闭调度器"""
        if isinstance(closed := getattr(self.dupe_filter, 'closed', None), Callable):
            await closed()
        
        if self.queue_manager:
            await self.queue_manager.close()

    def __len__(self):
        """获取队列大小"""
        if not self.queue_manager:
            return 0
        # 返回同步的近似值，实际大小需要异步获取
        return 0 if self.queue_manager.empty() else 1

# #!/usr/bin/python
# # -*- coding:UTF-8 -*-
# from typing import Optional, Callable
#
# from crawlo.utils.log import get_logger
# from crawlo.utils.request import set_request
# from crawlo.utils.pqueue import SpiderPriorityQueue
# from crawlo.project import load_class, common_call
#
#
# class Scheduler:
#     def __init__(self, crawler, dupe_filter, stats, log_level, priority):
#         self.crawler = crawler
#         self.request_queue: Optional[SpiderPriorityQueue] = None
#
#         self.logger = get_logger(name=self.__class__.__name__, level=log_level)
#         self.stats = stats
#         self.dupe_filter = dupe_filter
#         self.priority = priority
#
#     @classmethod
#     def create_instance(cls, crawler):
#         filter_cls = load_class(crawler.settings.get('FILTER_CLASS'))
#         o = cls(
#             crawler=crawler,
#             dupe_filter=filter_cls.create_instance(crawler),
#             stats=crawler.stats,
#             log_level=crawler.settings.get('LOG_LEVEL'),
#             priority=crawler.settings.get('DEPTH_PRIORITY')
#         )
#         return o
#
#     def open(self):
#         self.request_queue = SpiderPriorityQueue()
#         self.logger.info(f'requesting filter: {self.dupe_filter}')
#
#     async def next_request(self):
#         request = await self.request_queue.get()
#         return request
#
#     async def enqueue_request(self, request):
#         if not request.dont_filter and await common_call(self.dupe_filter.requested, request):
#             self.dupe_filter.log_stats(request)
#             return False
#         set_request(request, self.priority)
#         await self.request_queue.put(request)
#         return True
#
#     def idle(self) -> bool:
#         return len(self) == 0
#
#     async def close(self):
#         if isinstance(closed := getattr(self.dupe_filter, 'closed', None), Callable):
#             await closed()
#
#     def __len__(self):
#         return self.request_queue.qsize()
