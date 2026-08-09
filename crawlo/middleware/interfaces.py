#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
中间件层接口定义
================
IMiddleware（中间件接口）。
"""
from typing import (
    Optional, Protocol, runtime_checkable, TYPE_CHECKING
)

if TYPE_CHECKING:
    from crawlo.http.request import Request
    from crawlo.http.response import Response
    from crawlo.crawler import Crawler


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
                if response.status in (500, 502, 503):
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


__all__ = [
    'IMiddleware',
]
