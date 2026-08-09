#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
网络层异常定义
=============
请求/响应/下载相关异常。
"""
from typing import Optional

from crawlo.core.errors import CrawloException


# ============= 请求/响应异常 =============
class RequestException(CrawloException):
    """请求异常基类"""


class RequestMethodError(RequestException):
    """请求方法错误。当使用不支持的HTTP方法时抛出"""


class IgnoreRequestError(RequestException):
    """
    请求被忽略异常

    用于流程控制，表示请求应该被跳过处理。

    Attributes:
        msg: 忽略原因
    """

    def __init__(self, msg: str = "") -> None:
        self.msg = msg
        super().__init__(msg)

    def __str__(self) -> str:
        return f"IgnoreRequest: {self.msg}"


class DecodeError(RequestException):
    """响应解码错误。当无法解码响应内容时抛出"""


class DownloadError(RequestException):
    """下载错误。当请求下载失败时抛出"""

    def __init__(
        self,
        message: str = "",
        url: Optional[str] = None,
        status_code: Optional[int] = None
    ) -> None:
        super().__init__(message)
        self.url = url
        self.status_code = status_code


class RetryError(RequestException):
    """重试错误。当重试次数用尽时抛出"""

    def __init__(
        self,
        message: str = "",
        retry_times: int = 0,
        max_retries: int = 0
    ) -> None:
        super().__init__(message)
        self.retry_times = retry_times
        self.max_retries = max_retries


# ============= 导出 =============
__all__ = [
    'RequestException',
    'RequestMethodError',
    'IgnoreRequestError',
    'DecodeError',
    'DownloadError',
    'RetryError',
]
