#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
统一错误处理工具
提供一致的错误处理和日志记录机制
"""
import traceback
import logging
from typing import Optional, Callable, Any
from functools import wraps

from crawlo.utils.log import get_logger
from crawlo.utils.enhanced_error_handler import EnhancedErrorHandler, ErrorContext


class ErrorHandler:
    """统一错误处理器（简化版，使用增强版作为后端实现）"""
    
    def __init__(self, logger_name: str = __name__, log_level: str = 'ERROR'):
        self.logger = get_logger(logger_name, log_level)
        # 使用增强版错误处理器作为后端
        self._enhanced_handler = EnhancedErrorHandler(logger_name, log_level)
    
    def handle_error(self, exception: Exception, context: str = "", 
                     raise_error: bool = True, log_error: bool = True) -> None:
        """
        统一处理错误
        
        Args:
            exception: 异常对象
            context: 错误上下文描述
            raise_error: 是否重新抛出异常
            log_error: 是否记录错误日志
        """
        # 转换为增强版错误上下文
        error_context = ErrorContext(context=context) if context else None
        self._enhanced_handler.handle_error(
            exception, context=error_context, 
            raise_error=raise_error, log_error=log_error
        )
    
    def safe_call(self, func: Callable, *args, default_return=None, 
                  context: str = "", **kwargs) -> Any:
        """
        安全调用函数，捕获并处理异常
        
        Args:
            func: 要调用的函数
            *args: 函数参数
            default_return: 默认返回值
            context: 错误上下文描述
            **kwargs: 函数关键字参数
            
        Returns:
            函数返回值或默认值
        """
        error_context = ErrorContext(context=context) if context else None
        return self._enhanced_handler.safe_call(
            func, *args, default_return=default_return, 
            context=error_context, **kwargs
        )
    
    def retry_on_failure(self, max_retries: int = 3, delay: float = 1.0, 
                         exceptions: tuple = (Exception,)):
        """
        装饰器：失败时重试
        
        Args:
            max_retries: 最大重试次数
            delay: 重试间隔（秒）
            exceptions: 需要重试的异常类型
        """
        def decorator(func):
            # 直接使用增强版处理器的重试装饰器
            return self._enhanced_handler.retry_on_failure(
                max_retries=max_retries, delay=delay, exceptions=exceptions
            )(func)
        return decorator


# 全局错误处理器实例
default_error_handler = ErrorHandler()


def handle_exception(context: str = "", raise_error: bool = True, log_error: bool = True):
    """
    装饰器：处理函数异常
    
    Args:
        context: 错误上下文描述
        raise_error: 是否重新抛出异常
        log_error: 是否记录错误日志
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                default_error_handler.handle_error(
                    e, context=f"{context} - {func.__name__}", 
                    raise_error=raise_error, log_error=log_error
                )
                if not raise_error:
                    return None
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                default_error_handler.handle_error(
                    e, context=f"{context} - {func.__name__}", 
                    raise_error=raise_error, log_error=log_error
                )
                if not raise_error:
                    return None
        
        # 根据函数是否为异步函数返回相应的包装器
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator