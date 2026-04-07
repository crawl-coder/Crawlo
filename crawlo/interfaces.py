#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
Crawlo 框架接口定义
===================
定义框架中所有核心组件的抽象接口，支持：
- 类型安全：避免拼写错误
- IDE 支持：自动补全和提示
- 文档化：集中管理所有接口
- 可扩展性：便于用户实现自定义组件

使用示例：
    from crawlo.interfaces import IPipeline
    
    class MyPipeline(IPipeline):
        async def process_item(self, item: Item) -> Item:
            # 处理逻辑
            return item
"""
from abc import ABC, abstractmethod
from typing import (
    Type, List, Dict, Any, Optional, Union, 
    Protocol, runtime_checkable, TYPE_CHECKING, Coroutine
)

if TYPE_CHECKING:
    from crawlo.spider import Spider
    from crawlo.network.request import Request
    from crawlo.network.response import Response
    from crawlo.items import Item
    from crawlo.crawler import Crawler


# ==================== 爬虫加载器接口 ====================

@runtime_checkable
class ISpiderLoader(Protocol):
    """
    Spider 加载器接口
    
    负责发现、加载和管理爬虫类。
    
    实现示例：
        class FileSystemSpiderLoader(ISpiderLoader):
            def __init__(self, spider_dir: str):
                self.spider_dir = spider_dir
                self._spiders = {}
                self._load_spiders()
    """
    
    @abstractmethod
    def load(self, spider_name: str) -> Type['Spider']:
        """
        根据名称加载爬虫类
        
        Args:
            spider_name: 爬虫名称
            
        Returns:
            Type[Spider]: 爬虫类
            
        Raises:
            KeyError: 爬虫不存在
        """
        ...
    
    @abstractmethod
    def list(self) -> List[str]:
        """
        列出所有可用的爬虫名称
        
        Returns:
            List[str]: 爬虫名称列表
        """
        ...
    
    @abstractmethod
    def find_by_request(self, request: 'Request') -> List[str]:
        """
        查找能处理指定请求的爬虫名称
        
        Args:
            request: 请求对象
            
        Returns:
            List[str]: 能处理该请求的爬虫名称列表
        """
        ...


# ==================== 下载器接口 ====================

@runtime_checkable
class IDownloader(Protocol):
    """
    下载器接口
    
    负责执行 HTTP 请求并返回响应。
    支持多种实现：aiohttp、httpx、curl_cffi、playwright 等。
    
    实现示例：
        class AioHttpDownloader(IDownloader):
            async def fetch(self, request: Request) -> Optional[Response]:
                async with aiohttp.ClientSession() as session:
                    async with session.get(request.url) as resp:
                        return Response(url=request.url, body=await resp.read())
    """
    
    @abstractmethod
    async def fetch(self, request: 'Request') -> 'Optional[Response]':
        """
        执行请求并返回响应（经过中间件处理）
        
        Args:
            request: 请求对象
            
        Returns:
            Optional[Response]: 响应对象，可能为 None（请求被过滤）
            
        Raises:
            DownloadError: 下载失败
        """
        ...
    
    @abstractmethod
    async def download(self, request: 'Request') -> 'Response':
        """
        执行实际的下载操作（子类实现）
        
        Args:
            request: 请求对象
            
        Returns:
            Response: 响应对象
        """
        ...
    
    @abstractmethod
    async def close(self) -> None:
        """
        关闭下载器并清理资源
        
        应该释放连接池、关闭会话等资源。
        """
        ...
    
    @abstractmethod
    def idle(self) -> bool:
        """
        检查下载器是否空闲（无活跃请求）
        
        Returns:
            bool: 是否空闲
        """
        ...
    
    @classmethod
    def create_instance(cls, crawler: 'Crawler') -> 'IDownloader':
        """
        创建下载器实例的工厂方法
        
        Args:
            crawler: Crawler 实例
            
        Returns:
            IDownloader: 下载器实例
        """
        ...


# ==================== 管道接口 ====================

@runtime_checkable
class IPipeline(Protocol):
    """
    数据管道接口
    
    负责 Item 的处理、清洗、存储等操作。
    
    实现示例：
        class MySQLPipeline(IPipeline):
            async def process_item(self, item: Item) -> Item:
                await self.db.insert(item.to_dict())
                return item
            
            async def close(self) -> None:
                await self.db.close()
    """
    
    @abstractmethod
    async def process_item(self, item: 'Item') -> 'Item':
        """
        处理 Item
        
        Args:
            item: 待处理的 Item
            
        Returns:
            Item: 处理后的 Item（传递给下一个管道）
            
        Raises:
            ItemDiscard: 丢弃 Item，不传递给后续管道
            DropItem: 同 ItemDiscard（别名）
        """
        ...
    
    async def open(self) -> None:
        """
        打开管道（可选实现）
        
        用于初始化资源，如数据库连接。
        """
        ...
    
    async def close(self) -> None:
        """
        关闭管道（可选实现）
        
        用于清理资源，如关闭数据库连接。
        """
        ...


# ==================== 过滤器接口 ====================

@runtime_checkable
class IFilter(Protocol):
    """
    请求去重过滤器接口
    
    负责识别和过滤重复请求。
    
    实现示例：
        class MemoryFilter(IFilter):
            def __init__(self):
                self._fingerprints = set()
            
            def requested(self, request: Request) -> bool:
                fp = self._get_fingerprint(request)
                if fp in self._fingerprints:
                    return True
                self._fingerprints.add(fp)
                return False
    """
    
    @abstractmethod
    def requested(self, request: 'Request') -> bool:
        """
        检查请求是否重复
        
        Args:
            request: 请求对象
            
        Returns:
            bool: True 表示重复（已请求过），False 表示新请求
        """
        ...
    
    @abstractmethod
    def add_fingerprint(self, fp: str) -> None:
        """
        添加请求指纹
        
        Args:
            fp: 请求指纹字符串
        """
        ...
    
    @abstractmethod
    def __contains__(self, fp: str) -> bool:
        """
        检查指纹是否存在
        
        Args:
            fp: 请求指纹字符串
            
        Returns:
            bool: 是否已存在
        """
        ...
    
    def close(self) -> None:
        """
        关闭过滤器并清理资源（可选实现）
        """
        ...
    
    @classmethod
    def create_instance(cls, *args, **kwargs) -> 'IFilter':
        """
        创建过滤器实例的工厂方法
        """
        ...


# ==================== 扩展接口 ====================

@runtime_checkable
class IExtension(Protocol):
    """
    扩展接口
    
    扩展用于添加框架级功能，如统计、监控、日志等。
    
    与中间件不同，扩展不处理请求/响应流程，
    而是订阅事件并在事件触发时执行。
    
    实现示例：
        class StatsExtension(IExtension):
            @classmethod
            def create_instance(cls, crawler):
                return cls(crawler)
            
            async def spider_closed(self) -> None:
                self.logger.info(f"Total items: {self.stats.get('item_count')}")
    """
    
    @classmethod
    def create_instance(cls, crawler: 'Crawler') -> 'IExtension':
        """
        创建扩展实例的工厂方法
        
        Args:
            crawler: Crawler 实例
            
        Returns:
            IExtension: 扩展实例
        """
        ...
    
    # 以下是可选的事件处理方法
    async def spider_opened(self) -> None:
        """爬虫开启时调用（可选）"""
        ...
    
    async def spider_closed(self) -> None:
        """爬虫关闭时调用（可选）"""
        ...
    
    async def item_successful(self, item: 'Item') -> None:
        """Item 处理成功时调用（可选）"""
        ...
    
    async def item_discard(self, item: 'Item', reason: str) -> None:
        """Item 被丢弃时调用（可选）"""
        ...
    
    async def response_received(self, response: 'Response') -> None:
        """响应接收时调用（可选）"""
        ...
    
    async def request_scheduled(self, request: 'Request') -> None:
        """请求调度时调用（可选）"""
        ...


# ==================== 调度器接口 ====================

@runtime_checkable
class IScheduler(Protocol):
    """
    调度器接口
    
    负责请求的调度、优先级排序、去重等。
    
    实现示例：
        class RedisScheduler(IScheduler):
            async def enqueue_request(self, request: Request) -> bool:
                if self.duplicate_filter.requested(request):
                    return False
                await self.queue.put(request)
                return True
            
            async def next_request(self) -> Optional[Request]:
                return await self.queue.get()
    """
    
    @abstractmethod
    async def enqueue_request(self, request: 'Request') -> bool:
        """
        将请求加入调度队列
        
        Args:
            request: 请求对象
            
        Returns:
            bool: 是否成功加入队列（False 可能是因为去重）
        """
        ...
    
    @abstractmethod
    async def next_request(self) -> 'Optional[Request]':
        """
        获取下一个待处理的请求
        
        Returns:
            Optional[Request]: 请求对象，队列为空时返回 None
        """
        ...
    
    @abstractmethod
    def idle(self) -> bool:
        """
        检查调度器是否空闲
        
        Returns:
            bool: 是否空闲
        """
        ...
    
    @abstractmethod
    async def open(self) -> None:
        """
        打开调度器（初始化资源）
        """
        ...
    
    @abstractmethod
    async def close(self) -> None:
        """
        关闭调度器（清理资源）
        """
        ...
    
    @classmethod
    def create_instance(cls, crawler: 'Crawler') -> 'IScheduler':
        """
        创建调度器实例的工厂方法
        """
        ...


# ==================== 队列接口 ====================

@runtime_checkable
class IQueue(Protocol):
    """
    队列接口
    
    负责请求的存储和获取，支持多种后端实现。
    
    实现示例：
        class RedisQueue(IQueue):
            async def put(self, request: Request) -> None:
                await self.redis.lpush(self.key, serialize(request))
            
            async def get(self) -> Optional[Request]:
                data = await self.redis.rpop(self.key)
                return deserialize(data) if data else None
    """
    
    @abstractmethod
    async def put(self, request: 'Request') -> None:
        """
        将请求加入队列
        
        Args:
            request: 请求对象
        """
        ...
    
    @abstractmethod
    async def get(self) -> 'Optional[Request]':
        """
        从队列获取请求
        
        Returns:
            Optional[Request]: 请求对象，队列为空时返回 None
        """
        ...
    
    @abstractmethod
    def qsize(self) -> int:
        """
        获取队列大小
        
        Returns:
            int: 队列中请求数量
        """
        ...
    
    @abstractmethod
    async def clear(self) -> None:
        """
        清空队列
        """
        ...


# ==================== 统计收集器接口 ====================

@runtime_checkable
class IStatsCollector(Protocol):
    """
    统计收集器接口
    
    负责收集和存储爬虫运行期间的统计信息。
    支持多种后端实现：内存、Redis、Prometheus 等。
    
    实现示例：
        class RedisStatsCollector(IStatsCollector):
            def inc_value(self, key: str, count: int = 1) -> None:
                self.redis.hincrby(self.key, key, count)
            
            def get_value(self, key: str, default: Any = None) -> Any:
                value = self.redis.hget(self.key, key)
                return int(value) if value else default
    """
    
    @abstractmethod
    def inc_value(self, key: str, count: int = 1) -> None:
        """
        增加计数器值
        
        Args:
            key: 统计键名
            count: 增量，默认为 1
        """
        ...
    
    @abstractmethod
    def get_value(self, key: str, default: Any = None) -> Any:
        """
        获取统计值
        
        Args:
            key: 统计键名
            default: 默认值
            
        Returns:
            Any: 统计值
        """
        ...
    
    @abstractmethod
    def set_value(self, key: str, value: Any) -> None:
        """
        设置统计值
        
        Args:
            key: 统计键名
            value: 统计值
        """
        ...
    
    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """
        获取所有统计信息
        
        Returns:
            Dict[str, Any]: 统计信息字典
        """
        ...
    
    @abstractmethod
    def clear(self) -> None:
        """
        清空所有统计信息
        """
        ...


# ==================== 中间件接口 ====================

@runtime_checkable
class IMiddleware(Protocol):
    """
    中间件接口
    
    中间件用于在请求发送前和响应接收后进行处理。
    
    实现示例：
        class RetryMiddleware(IMiddleware):
            async def process_request(self, request: Request) -> Optional[Response]:
                # 可以修改请求或返回 Response 终止请求
                return None
            
            async def process_response(self, request: Request, response: Response) -> Response:
                if response.status_code in (500, 502, 503):
                    raise RetryException()
                return response
            
            async def process_exception(self, request: Request, exception: Exception) -> Optional[Response]:
                if request.meta.get('retry_times', 0) < 3:
                    return None  # 重试
                raise exception
    """
    
    async def process_request(self, request: 'Request') -> 'Optional[Response]':
        """
        处理请求（发送前）
        
        Args:
            request: 请求对象
            
        Returns:
            Optional[Response]: 
                - None: 继续处理
                - Response: 终止请求流程，直接返回响应
        """
        ...
    
    async def process_response(self, request: 'Request', response: 'Response') -> 'Response':
        """
        处理响应（接收后）
        
        Args:
            request: 请求对象
            response: 响应对象
            
        Returns:
            Response: 处理后的响应对象
            
        Raises:
            IgnoreRequest: 忽略该响应
            RetryRequest: 重试该请求
        """
        ...
    
    async def process_exception(self, request: 'Request', exception: Exception) -> 'Optional[Response]':
        """
        处理异常
        
        Args:
            request: 请求对象
            exception: 异常对象
            
        Returns:
            Optional[Response]:
                - None: 继续抛出异常
                - Response: 使用该响应替代异常
        """
        ...
    
    @classmethod
    def create_instance(cls, crawler: 'Crawler') -> 'IMiddleware':
        """
        创建中间件实例的工厂方法
        """
        ...


# ==================== 导出所有接口 ====================

__all__ = [
    # 核心接口
    'ISpiderLoader',
    'IDownloader',
    'IPipeline',
    'IFilter',
    'IExtension',
    'IScheduler',
    'IQueue',
    'IStatsCollector',
    'IMiddleware',
]
