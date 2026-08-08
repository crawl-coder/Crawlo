#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
下载器层接口定义
================
IDownloader（下载器接口）。
"""
from abc import abstractmethod
from typing import (
    Type, Optional, Protocol, runtime_checkable, TYPE_CHECKING
)

if TYPE_CHECKING:
    from crawlo.http.request import Request
    from crawlo.http.response import Response
    from crawlo.crawler import Crawler


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


__all__ = [
    'IDownloader',
]
