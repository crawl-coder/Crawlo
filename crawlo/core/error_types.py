#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
Crawlo Framework Error Type Classification Configuration
========================================================
Centralized management of various error type classifications in the framework
for unified configuration and maintenance.

Classification System:
    - Critical: Errors that cause system instability, require immediate stop
    - Network: Network communication related errors, usually retryable
    - Data: Data processing related errors
    - Resource: Resource management related errors
    - Retryable: Errors that can be resolved through retry mechanism

Example:
    >>> from crawlo.core.error_types import ErrorClassifier
    >>> if ErrorClassifier.is_critical(error):
    ...     raise error  # Critical errors need to be re-raised
    >>> if ErrorClassifier.should_retry(error):
    ...     return await self.retry_request(request)
"""
from typing import Tuple, Type, Union
import asyncio


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
    
    # ========== Critical Error Types ==========
    # These errors cause system instability and require immediate crawler stop
    CRITICAL_EXCEPTIONS: Tuple[Type[Exception], ...] = (
        MemoryError,       # Memory exhausted
        SystemError,       # System error
        RecursionError,    # Recursion depth exceeded
        KeyboardInterrupt, # User interrupt
        SystemExit,        # System exit
    )
    
    # ========== Network Error Types ==========
    # Network communication related errors, usually retryable
    # Note: asyncio.TimeoutError is an alias of TimeoutError in Python 3.11+
    NETWORK_EXCEPTIONS: Tuple[Type[Exception], ...] = (
        ConnectionError,           # Connection error
        TimeoutError,              # Timeout error (includes asyncio.TimeoutError in 3.11+)
        OSError,                   # OS error (includes network related)
    )
    
    # ========== Data Error Types ==========
    # Data processing related errors
    DATA_EXCEPTIONS: Tuple[Type[Exception], ...] = (
        ValueError,        # Value error
        TypeError,         # Type error
        KeyError,          # Key error
        IndexError,        # Index error
        AttributeError,    # Attribute error
        UnicodeError,      # Encoding error
    )
    
    # ========== Resource Error Types ==========
    # Resource management related errors
    RESOURCE_EXCEPTIONS: Tuple[Type[Exception], ...] = (
        FileNotFoundError,      # File not found
        PermissionError,        # Permission error
        IsADirectoryError,      # Is a directory not a file
        NotADirectoryError,     # Not a directory
        BlockingIOError,        # IO blocking error
    )
    
    # ========== Retryable Error Types ==========
    # Errors that can be resolved through retry mechanism
    # Note: asyncio.TimeoutError is an alias of TimeoutError in Python 3.11+
    RETRYABLE_EXCEPTIONS: Tuple[Type[Exception], ...] = (
        ConnectionError,
        TimeoutError,              # Includes asyncio.TimeoutError in 3.11+
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
