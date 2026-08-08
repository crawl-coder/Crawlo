#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
核心错误模块（合并版）
====================

本模块合并了原 error_types.py、exceptions.py 和 failure.py 三个模块，
统一提供 Crawlo 框架的错误分类、异常定义和失败包装功能。

内容结构：
    1. ErrorClassifier + 辅助函数（来自 error_types.py）
       - 关键/网络/数据/资源/可重试错误分类
       - is_critical_error / should_retry_error / get_error_category 便捷函数
    2. CrawloException 异常体系（来自 exceptions.py）
       - 基础异常 CrawloException
       - 组件初始化异常（Middleware/Pipeline/Extension）
       - 配置异常（NotConfigured / ConfigValidationError 等）
       - 类型异常（TransformTypeError / ReceiverTypeError）
       - 调度异常 ScheduleException
       - 输出异常（OutputError / InvalidOutputError）
       - DetailedException + ErrorContext 详细错误工具
    3. Failure 失败对象包装器（来自 failure.py）
       - 封装异常 + Request + traceback，用于 errback 回调
"""
from typing import Optional, Any, Dict, List, Tuple, Type, Union, TYPE_CHECKING
from datetime import datetime
import asyncio
import traceback
import time

if TYPE_CHECKING:
    from crawlo import Request


# ============================================================
# 来自 error_types.py：错误分类器 + 便捷函数
# ============================================================
class ErrorClassifier:
    """
    Error classifier

    Centralized management of all error type classifications in the framework, supporting:
    - Critical error identification (requires immediate crawler stop)
    - Network error identification (retryable)
    - Data error identification
    - Resource error identification
    - Retry strategy determination
    """

    CRITICAL_EXCEPTIONS: Tuple[Type[Exception], ...] = (
        MemoryError,
        SystemError,
        RecursionError,
        KeyboardInterrupt,
        SystemExit,
    )

    NETWORK_EXCEPTIONS: Tuple[Type[Exception], ...] = (
        ConnectionError,
        TimeoutError,
        OSError,
    )

    DATA_EXCEPTIONS: Tuple[Type[Exception], ...] = (
        ValueError,
        TypeError,
        KeyError,
        IndexError,
        AttributeError,
        UnicodeError,
    )

    RESOURCE_EXCEPTIONS: Tuple[Type[Exception], ...] = (
        FileNotFoundError,
        PermissionError,
        IsADirectoryError,
        NotADirectoryError,
        BlockingIOError,
    )

    RETRYABLE_EXCEPTIONS: Tuple[Type[Exception], ...] = (
        ConnectionError,
        TimeoutError,
        OSError,
    )

    @classmethod
    def is_critical(cls, error: Exception) -> bool:
        return isinstance(error, cls.CRITICAL_EXCEPTIONS)

    @classmethod
    def is_network_error(cls, error: Exception) -> bool:
        return isinstance(error, cls.NETWORK_EXCEPTIONS)

    @classmethod
    def is_data_error(cls, error: Exception) -> bool:
        return isinstance(error, cls.DATA_EXCEPTIONS)

    @classmethod
    def is_resource_error(cls, error: Exception) -> bool:
        return isinstance(error, cls.RESOURCE_EXCEPTIONS)

    @classmethod
    def should_retry(cls, error: Exception) -> bool:
        if cls.is_critical(error):
            return False
        return isinstance(error, cls.RETRYABLE_EXCEPTIONS)

    @classmethod
    def get_error_category(cls, error: Exception) -> str:
        if cls.is_critical(error):
            return 'critical'
        elif cls.is_network_error(error):
            return 'network'
        elif cls.is_data_error(error):
            return 'data'
        elif cls.is_resource_error(error):
            return 'resource'
        else:
            return 'unknown'

    @classmethod
    def get_all_categories(cls) -> dict:
        return {
            'critical': {
                'description': '关键错误，需要立即停止爬虫',
                'exceptions': cls.CRITICAL_EXCEPTIONS,
            },
            'network': {
                'description': '网络错误，通常可重试',
                'exceptions': cls.NETWORK_EXCEPTIONS,
            },
            'data': {
                'description': '数据处理错误',
                'exceptions': cls.DATA_EXCEPTIONS,
            },
            'resource': {
                'description': '资源管理错误',
                'exceptions': cls.RESOURCE_EXCEPTIONS,
            },
            'retryable': {
                'description': '可重试错误',
                'exceptions': cls.RETRYABLE_EXCEPTIONS,
            },
        }


def is_critical_error(error: Exception) -> bool:
    return ErrorClassifier.is_critical(error)


def should_retry_error(error: Exception) -> bool:
    return ErrorClassifier.should_retry(error)


def get_error_category(error: Exception) -> str:
    return ErrorClassifier.get_error_category(error)


# ============================================================
# 来自 exceptions.py：异常体系定义
# ============================================================

# ============= 基础异常 =============
class CrawloException(Exception):
    """
    Crawlo框架基础异常

    所有框架异常都应继承此类。

    Attributes:
        message: 异常消息
    """

    def __init__(self, message: str = "") -> None:
        self.message = message
        super().__init__(message)


# ============= 组件初始化异常 =============
class ComponentInitException(CrawloException):
    """组件初始化异常基类"""
    pass


class MiddlewareInitError(ComponentInitException):
    """中间件初始化失败异常"""
    pass


class PipelineInitError(ComponentInitException):
    """管道初始化失败异常"""
    pass


class ExtensionInitError(ComponentInitException):
    """扩展初始化失败异常"""
    pass


# ============= 配置异常 =============
class ConfigException(CrawloException):
    """配置异常基类"""
    pass


class NotConfigured(ConfigException):
    """组件未配置异常。当必需的配置缺失时抛出"""
    pass


class NotConfiguredError(ConfigException):
    """配置错误异常。当配置值无效时抛出"""
    pass


class ConfigValidationError(ConfigException):
    """配置验证错误"""

    def __init__(
        self,
        message: str = "",
        errors: Optional[list] = None
    ) -> None:
        super().__init__(message)
        self.errors = errors or []


# ============= 类型异常 =============
class TransformTypeError(CrawloException, TypeError):
    """转换类型错误。当数据转换类型不匹配时抛出"""

    def __init__(
        self,
        message: str = "",
        expected_type: Optional[str] = None,
        actual_type: Optional[str] = None
    ) -> None:
        super().__init__(message)
        self.expected_type = expected_type
        self.actual_type = actual_type


class ReceiverTypeError(CrawloException, TypeError):
    """接收者类型错误。当事件接收者类型不符合预期时抛出"""
    pass


# ============= 调度异常 =============
class ScheduleException(CrawloException):
    """调度异常基类"""
    pass


# ============= 输出异常 =============
class OutputException(CrawloException):
    """输出异常基类"""
    pass


class OutputError(OutputException):
    """输出错误。当输出处理失败时抛出"""
    pass


class InvalidOutputError(OutputException):
    """无效的输出错误。当输出类型或格式不符合预期时抛出"""
    pass


# ============= 详细错误异常 =============
class DetailedException(CrawloException):
    """
    带有详细信息的异常

    用于错误处理工具，提供上下文、错误代码等额外信息。

    Attributes:
        message: 异常消息
        context: 错误上下文信息
        error_code: 错误代码
        details: 额外详情字典
        timestamp: 异常发生时间
    """

    def __init__(
        self,
        message: str,
        context: Optional['ErrorContext'] = None,
        error_code: Optional[str] = None,
        **kwargs
    ) -> None:
        super().__init__(message)
        self.context = context
        self.error_code = error_code
        self.details = kwargs
        self.timestamp = datetime.now()

    def __str__(self) -> str:
        base_msg = super().__str__()
        if self.context:
            return f"{base_msg} ({self.context})"
        return base_msg

    def get_full_details(self) -> Dict:
        """获取完整的错误详情"""
        return {
            "message": str(self),
            "error_code": self.error_code,
            "context": str(self.context) if self.context else None,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
            "exception_type": self.__class__.__name__
        }


# ============= 错误上下文 =============
class ErrorContext:
    """错误上下文信息"""

    def __init__(self, context: str = "", module: str = "", function: str = ""):
        self.context = context
        self.module = module
        self.function = function
        self.timestamp = datetime.now()

    def __str__(self) -> str:
        parts = []
        if self.module:
            parts.append(f"Module: {self.module}")
        if self.function:
            parts.append(f"Function: {self.function}")
        if self.context:
            parts.append(f"Context: {self.context}")
        parts.append(f"Time: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        return " | ".join(parts)


# ============================================================
# 来自 failure.py：Failure 失败对象包装器
# ============================================================
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
        """
        return isinstance(self.value, exception_types)


# ============================================================
# 合并导出
# ============================================================
__all__ = [
    # ===== error_types.py =====
    'ErrorClassifier',
    'is_critical_error',
    'should_retry_error',
    'get_error_category',

    # ===== exceptions.py - 基础异常 =====
    'CrawloException',

    # ===== exceptions.py - 组件初始化 =====
    'ComponentInitException',
    'MiddlewareInitError',
    'PipelineInitError',
    'ExtensionInitError',

    # ===== exceptions.py - 配置 =====
    'ConfigException',
    'NotConfigured',
    'NotConfiguredError',
    'ConfigValidationError',

    # ===== exceptions.py - 类型 =====
    'TransformTypeError',
    'ReceiverTypeError',

    # ===== exceptions.py - 调度 =====
    'ScheduleException',

    # ===== exceptions.py - 输出 =====
    'OutputException',
    'OutputError',
    'InvalidOutputError',

    # ===== exceptions.py - 详细错误 =====
    'DetailedException',
    'ErrorContext',

    # ===== failure.py =====
    'Failure',
]
