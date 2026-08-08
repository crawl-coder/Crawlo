#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
核心异常定义
===========
框架核心层（引擎、组件、配置、调度）的异常定义。

基础异常 CrawloException 放在此模块，所有框架异常都应继承此类。
"""
from typing import Optional, Any, Dict, List
from datetime import datetime


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


# ============= 调度异常（基类 + 队列异常由 queue/exceptions.py 定义）=============
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


# ============= 详细错误异常（用于错误处理工具）=============
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


# ============= 错误上下文（用于DetailedException）=============
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


# ============= 导出 =============
__all__ = [
    # 基础异常
    'CrawloException',

    # 组件初始化
    'ComponentInitException',
    'MiddlewareInitError',
    'PipelineInitError',
    'ExtensionInitError',

    # 配置
    'ConfigException',
    'NotConfigured',
    'NotConfiguredError',
    'ConfigValidationError',

    # 类型
    'TransformTypeError',
    'ReceiverTypeError',

    # 调度
    'ScheduleException',

    # 输出
    'OutputException',
    'OutputError',
    'InvalidOutputError',

    # 详细错误
    'DetailedException',
    'ErrorContext',
]
