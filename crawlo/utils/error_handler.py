#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
统一错误处理工具
提供一致的错误处理和日志记录机制
"""
import time
import traceback
from functools import wraps
from typing import Callable, Any

from crawlo.utils.log import get_logger


class ErrorHandler:
    """统一错误处理器（简化版，避免循环依赖）"""

    def __init__(self, logger_name: str = __name__, log_level: str = 'ERROR'):
        # 延迟初始化logger避免循环依赖
        self._logger = None
        self.logger_name = logger_name
        self.log_level = log_level

    @property
    def logger(self):
        if self._logger is None:
            self._logger = get_logger(self.logger_name)
        return self._logger

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
        if log_error:
            error_msg = f"Error in {context}: {str(exception)}" if context else str(exception)
            self.logger.error(error_msg)
            # 在DEBUG级别记录详细的堆栈跟踪
            self.logger.debug(f"详细错误信息:\n{traceback.format_exc()}")

        if raise_error:
            raise exception

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
        try:
            return func(*args, **kwargs)
        except Exception as e:
            self.handle_error(e, context=context, raise_error=False)
            return default_return

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
            @wraps(func)
            def wrapper(*args, **kwargs):
                last_exception = None
                for attempt in range(max_retries + 1):
                    try:
                        return func(*args, **kwargs)
                    except exceptions as e:
                        last_exception = e
                        if attempt < max_retries:
                            self.logger.warning(f"Attempt {attempt + 1} failed, retrying in {delay}s: {e}")
                            time.sleep(delay)
                        else:
                            self.logger.error(f"All {max_retries + 1} attempts failed")
                            raise e
                return None

            return wrapper

        return decorator


# 全局错误处理器实例（延迟初始化）
_default_error_handler = None


def get_default_error_handler():
    """Get the default error handler with lazy initialization"""
    global _default_error_handler
    if _default_error_handler is None:
        _default_error_handler = ErrorHandler()
    return _default_error_handler


# 为了向后兼容，保留老的接口
def __getattr__(name):
    if name == 'default_error_handler':
        return get_default_error_handler()
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


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
