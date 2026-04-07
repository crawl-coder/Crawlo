#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
Crawlo 框架异常定义
===================
提供层次化的异常体系，便于统一处理和类型安全。

异常层次：
    CrawloException (基础异常)
    ├── SpiderException (爬虫相关)
    ├── ComponentInitException (组件初始化)
    ├── DataException (数据处理)
    ├── RequestException (请求/响应)
    ├── OutputException (输出)
    └── ConfigException (配置)

使用示例：
    >>> try:
    ...     # 代码
    ... except CrawloException as e:
    ...     # 捕获所有框架异常
    ... except Exception as e:
    ...     # 其他异常
"""
from typing import Optional, Any


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


# ============= 爬虫相关异常 =============
class SpiderException(CrawloException):
    """爬虫相关异常基类"""
    pass


class SpiderTypeError(SpiderException, TypeError):
    """爬虫类型错误。当爬虫类型不符合预期时抛出"""
    pass


class SpiderCreationError(SpiderException):
    """爬虫实例化失败异常。当无法创建爬虫实例时抛出"""
    pass


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


# ============= 数据处理异常 =============
class DataException(CrawloException):
    """数据处理异常基类"""
    pass


class ItemInitError(DataException):
    """Item初始化错误。当Item实例创建失败时抛出"""
    pass


class ItemAttributeError(DataException, AttributeError):
    """Item属性错误。当访问不存在的Item属性时抛出"""
    pass


class ItemValidationError(DataException):
    """Item字段验证错误。当Item字段值不符合验证规则时抛出"""
    
    def __init__(
        self, 
        message: str = "", 
        field_name: Optional[str] = None,
        value: Any = None
    ) -> None:
        super().__init__(message)
        self.field_name = field_name
        self.value = value


class ItemDiscard(DataException):
    """
    Item被丢弃异常
    
    注意：这不是一个真正的错误，而是用于流程控制，
    表示Item应该被管道丢弃（例如重复数据）。
    
    Attributes:
        msg: 丢弃原因
    """
    
    def __init__(self, msg: str = "") -> None:
        self.msg = msg
        super().__init__(msg)
    
    def __str__(self) -> str:
        return f"ItemDiscard: {self.msg}"


# 别名
DropItem = ItemDiscard


# ============= 请求/响应异常 =============
class RequestException(CrawloException):
    """请求异常基类"""
    pass


class RequestMethodError(RequestException):
    """请求方法错误。当使用不支持的HTTP方法时抛出"""
    pass


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
    pass


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


class QueueFullError(ScheduleException):
    """队列已满错误"""
    
    def __init__(self, queue_name: str = "", size: int = 0) -> None:
        message = f"Queue '{queue_name}' is full (size: {size})"
        super().__init__(message)
        self.queue_name = queue_name
        self.size = size


class QueueEmptyError(ScheduleException):
    """队列为空错误"""
    
    def __init__(self, queue_name: str = "") -> None:
        message = f"Queue '{queue_name}' is empty"
        super().__init__(message)
        self.queue_name = queue_name


# ============= 导出所有异常 =============
__all__ = [
    # 基础异常
    'CrawloException',
    
    # 爬虫相关
    'SpiderException',
    'SpiderTypeError',
    'SpiderCreationError',
    
    # 组件初始化
    'ComponentInitException',
    'MiddlewareInitError',
    'PipelineInitError',
    'ExtensionInitError',
    
    # 数据处理
    'DataException',
    'ItemInitError',
    'ItemAttributeError',
    'ItemValidationError',
    'ItemDiscard',
    'DropItem',
    
    # 请求/响应
    'RequestException',
    'RequestMethodError',
    'IgnoreRequestError',
    'DecodeError',
    'DownloadError',
    'RetryError',
    
    # 输出
    'OutputException',
    'OutputError',
    'InvalidOutputError',
    
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
    'QueueFullError',
    'QueueEmptyError',
]
