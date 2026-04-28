#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Failure 模块
============
提供错误失败对象包装器，用于 errback 回调。

封装异常信息和原始请求，提供完整的错误上下文。
"""
import traceback
import time
from typing import Optional, Type, TYPE_CHECKING

if TYPE_CHECKING:
    from crawlo import Request


class Failure:
    """
    错误失败对象包装器。

    封装异常信息和原始请求对象，errback 回调接收 Failure 实例
    而非裸异常，从而可以访问 request、堆栈等完整上下文。

    Attributes:
        value: 原始异常对象
        type: 异常类型
        tb: 异常 traceback 对象
        request: 原始请求对象
        timestamp: 错误发生时间戳

    Examples:
        >>> async def on_error(self, failure):
        ...     # 获取异常
        ...     error = failure.value
        ...     # 获取原始请求
        ...     request = failure.request
        ...     # 按类型分发
        ...     if failure.check(ConnectError):
        ...         yield Request(url='...', callback=self.parse)
    """

    __slots__ = ('value', 'type', 'tb', 'request', 'timestamp')

    def __init__(self, exception: Exception, request: Optional['Request'] = None):
        self.value: Exception = exception
        self.type: Type[Exception] = type(exception)
        self.tb = getattr(exception, '__traceback__', None)
        self.request: Optional['Request'] = request
        self.timestamp: float = time.time()

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__} {self.type.__name__}: {self.value}>'

    def __str__(self) -> str:
        if self.request is not None:
            return (f'{self.__class__.__name__}({self.type.__name__}): '
                    f'{self.value} at {self.request.url}')
        return f'{self.__class__.__name__}({self.type.__name__}): {self.value}'

    def getErrorMessage(self) -> str:
        """获取异常消息字符串。"""
        return str(self.value)

    def getTraceback(self) -> str:
        """获取格式化的堆栈信息字符串。"""
        if self.tb is not None:
            return ''.join(traceback.format_tb(self.tb))
        return '<no traceback available>'

    def check(self, *exception_types: Type[Exception]) -> bool:
        """
        检查异常是否属于指定类型。

        Args:
            *exception_types: 一个或多个异常类型

        Returns:
            是否命中任一类型

        Examples:
            >>> if failure.check(ConnectError, TimeoutError):
            ...     self.logger.warning("网络错误")
        """
        return isinstance(self.value, exception_types)
