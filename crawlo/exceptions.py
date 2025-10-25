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


# ============= 基础异常 =============
class CrawloException(Exception):
    """Crawlo框架基础异常。所有框架异常都应继承此类。"""
    pass


# ============= 爬虫相关异常 =============
class SpiderException(CrawloException):
    """爬虫相关异常基类。"""
    pass


class SpiderTypeError(SpiderException, TypeError):
    """爬虫类型错误。当爬虫类型不符合预期时抛出。"""
    pass


class SpiderCreationError(SpiderException):
    """爬虫实例化失败异常。当无法创建爬虫实例时抛出。"""
    pass


# ============= 组件初始化异常 =============
class ComponentInitException(CrawloException):
    """组件初始化异常基类。"""
    pass


class MiddlewareInitError(ComponentInitException):
    """中间件初始化失败异常。"""
    pass


class PipelineInitError(ComponentInitException):
    """管道初始化失败异常。"""
    pass


class ExtensionInitError(ComponentInitException):
    """扩展初始化失败异常。"""
    pass


# ============= 数据处理异常 =============
class DataException(CrawloException):
    """数据处理异常基类。"""
    pass


class ItemInitError(DataException):
    """Item初始化错误。当Item实例创建失败时抛出。"""
    pass


class ItemAttributeError(DataException, AttributeError):
    """Item属性错误。当访问不存在的Item属性时抛出。"""
    pass


class ItemValidationError(DataException):
    """Item字段验证错误。当Item字段值不符合验证规则时抛出。"""
    pass


class ItemDiscard(DataException):
    """
    Item被丢弃异常。
    
    注意：这不是一个真正的错误，而是用于流程控制，
    表示Item应该被管道丢弃（例如重复数据）。
    """
    def __init__(self, msg):
        self.msg = msg
        super().__init__(msg)


# ============= 请求/响应异常 =============
class RequestException(CrawloException):
    """请求异常基类。"""
    pass


class RequestMethodError(RequestException):
    """请求方法错误。当使用不支持的HTTP方法时抛出。"""
    pass


class IgnoreRequestError(RequestException):
    """
    请求被忽略异常。
    
    用于流程控制，表示请求应该被跳过处理。
    """
    def __init__(self, msg):
        self.msg = msg
        super().__init__(msg)


class DecodeError(RequestException):
    """响应解码错误。当无法解码响应内容时抛出。"""
    pass


# ============= 输出异常 =============
class OutputException(CrawloException):
    """输出异常基类。"""
    pass


class OutputError(OutputException):
    """输出错误。当输出处理失败时抛出。"""
    pass


class InvalidOutputError(OutputException):
    """无效的输出错误。当输出类型或格式不符合预期时抛出。"""
    pass


# ============= 配置异常 =============
class ConfigException(CrawloException):
    """配置异常基类。"""
    pass


class NotConfigured(ConfigException):
    """组件未配置异常。当必需的配置缺失时抛出。"""
    pass


class NotConfiguredError(ConfigException):
    """配置错误异常。当配置值无效时抛出。"""
    pass


# ============= 类型异常 =============
class TransformTypeError(CrawloException, TypeError):
    """转换类型错误。当数据转换类型不匹配时抛出。"""
    pass


class ReceiverTypeError(CrawloException, TypeError):
    """接收者类型错误。当事件接收者类型不符合预期时抛出。"""
    pass


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
    
    # 请求/响应
    'RequestException',
    'RequestMethodError',
    'IgnoreRequestError',
    'DecodeError',
    
    # 输出
    'OutputException',
    'OutputError',
    'InvalidOutputError',
    
    # 配置
    'ConfigException',
    'NotConfigured',
    'NotConfiguredError',
    
    # 类型
    'TransformTypeError',
    'ReceiverTypeError',
]