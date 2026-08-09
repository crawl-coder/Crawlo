#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
扩展层接口定义
==============
IExtension（扩展接口）。
"""
from typing import (
    Protocol, runtime_checkable, TYPE_CHECKING
)

if TYPE_CHECKING:
    from crawlo.items import Item
    from crawlo.http.request import Request
    from crawlo.http.response import Response
    from crawlo.crawler import Crawler


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


__all__ = [
    'IExtension',
]
