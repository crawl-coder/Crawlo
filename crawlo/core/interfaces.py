#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
核心层接口定义
==============
IScheduler（调度器接口）等引擎核心接口。
"""
from abc import abstractmethod
from typing import (
    Type, List, Optional, Protocol, runtime_checkable, TYPE_CHECKING
)

if TYPE_CHECKING:
    from crawlo.spider import Spider
    from crawlo.network.request import Request
    from crawlo.network.response import Response
    from crawlo.items import Item
    from crawlo.crawler import Crawler


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


__all__ = [
    'IScheduler',
]
