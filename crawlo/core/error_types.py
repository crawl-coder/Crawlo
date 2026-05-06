#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
Crawlo 框架错误类型分类配置
============================
集中管理框架中各种错误类型的分类，便于统一配置和维护。

分类体系：
    - 关键错误 (Critical): 会导致系统不稳定的错误，需要立即停止
    - 网络错误 (Network): 与网络通信相关的错误，通常可重试
    - 数据错误 (Data): 数据处理相关的错误
    - 资源错误 (Resource): 资源管理相关的错误
    - 可重试错误 (Retryable): 可以通过重试机制解决的错误

使用示例：
    >>> from crawlo.core.error_types import ErrorClassifier
    >>> if ErrorClassifier.is_critical(error):
    ...     raise error  # 关键错误需要重新抛出
    >>> if ErrorClassifier.should_retry(error):
    ...     return await self.retry_request(request)
"""
from typing import Tuple, Type, Union
import asyncio


class ErrorClassifier:
    """
    错误分类器
    
    集中管理框架中所有错误类型的分类，支持：
    - 关键错误识别（需要立即停止爬虫）
    - 网络错误识别（可重试）
    - 数据错误识别
    - 资源错误识别
    - 重试策略判断
    """
    
    # ========== 关键错误类型 ==========
    # 这些错误会导致系统处于不稳定状态，需要立即停止爬虫
    CRITICAL_EXCEPTIONS: Tuple[Type[Exception], ...] = (
        MemoryError,       # 内存不足
        SystemError,       # 系统错误
        RecursionError,    # 递归深度超限
        KeyboardInterrupt, # 用户中断
        SystemExit,        # 系统退出
    )
    
    # ========== 网络错误类型 ==========
    # 与网络通信相关的错误，通常可以通过重试解决
    NETWORK_EXCEPTIONS: Tuple[Type[Exception], ...] = (
        ConnectionError,           # 连接错误
        TimeoutError,              # 超时错误
        asyncio.TimeoutError,      # 异步超时
        OSError,                   # 操作系统错误（包含网络相关）
    )
    
    # ========== 数据错误类型 ==========
    # 数据处理相关的错误
    DATA_EXCEPTIONS: Tuple[Type[Exception], ...] = (
        ValueError,        # 值错误
        TypeError,         # 类型错误
        KeyError,          # 键错误
        IndexError,        # 索引错误
        AttributeError,    # 属性错误
        UnicodeError,      # 编码错误
    )
    
    # ========== 资源错误类型 ==========
    # 资源管理相关的错误
    RESOURCE_EXCEPTIONS: Tuple[Type[Exception], ...] = (
        FileNotFoundError,      # 文件不存在
        PermissionError,        # 权限错误
        IsADirectoryError,      # 是目录而非文件
        NotADirectoryError,     # 不是目录
        BlockingIOError,        # IO阻塞错误
    )
    
    # ========== 可重试错误类型 ==========
    # 可以通过重试机制解决的错误
    RETRYABLE_EXCEPTIONS: Tuple[Type[Exception], ...] = (
        ConnectionError,
        TimeoutError,
        asyncio.TimeoutError,
        OSError,
    )
    
    @classmethod
    def is_critical(cls, error: Exception) -> bool:
        """
        判断是否为关键错误
        
        Args:
            error: 异常实例
            
        Returns:
            bool: 是否为关键错误
        """
        return isinstance(error, cls.CRITICAL_EXCEPTIONS)
    
    @classmethod
    def is_network_error(cls, error: Exception) -> bool:
        """
        判断是否为网络错误
        
        Args:
            error: 异常实例
            
        Returns:
            bool: 是否为网络错误
        """
        return isinstance(error, cls.NETWORK_EXCEPTIONS)
    
    @classmethod
    def is_data_error(cls, error: Exception) -> bool:
        """
        判断是否为数据错误
        
        Args:
            error: 异常实例
            
        Returns:
            bool: 是否为数据错误
        """
        return isinstance(error, cls.DATA_EXCEPTIONS)
    
    @classmethod
    def is_resource_error(cls, error: Exception) -> bool:
        """
        判断是否为资源错误
        
        Args:
            error: 异常实例
            
        Returns:
            bool: 是否为资源错误
        """
        return isinstance(error, cls.RESOURCE_EXCEPTIONS)
    
    @classmethod
    def should_retry(cls, error: Exception) -> bool:
        """
        判断错误是否应该重试
        
        Args:
            error: 异常实例
            
        Returns:
            bool: 是否应该重试
        """
        # 关键错误不应该重试
        if cls.is_critical(error):
            return False
        # 可重试错误类型
        return isinstance(error, cls.RETRYABLE_EXCEPTIONS)
    
    @classmethod
    def get_error_category(cls, error: Exception) -> str:
        """
        获取错误分类
        
        Args:
            error: 异常实例
            
        Returns:
            str: 错误分类名称
        """
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
        """
        获取所有错误分类信息
        
        Returns:
            dict: 包含所有错误分类的字典
        """
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


# ========== 便捷函数 ==========
def is_critical_error(error: Exception) -> bool:
    """判断是否为关键错误的便捷函数"""
    return ErrorClassifier.is_critical(error)


def should_retry_error(error: Exception) -> bool:
    """判断是否应该重试的便捷函数"""
    return ErrorClassifier.should_retry(error)


def get_error_category(error: Exception) -> str:
    """获取错误分类的便捷函数"""
    return ErrorClassifier.get_error_category(error)


# ========== 导出 ==========
__all__ = [
    'ErrorClassifier',
    'is_critical_error',
    'should_retry_error',
    'get_error_category',
]
