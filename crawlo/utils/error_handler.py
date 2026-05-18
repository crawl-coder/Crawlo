#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
错误处理工具
提供详细、一致的错误处理和日志记录机制
"""
import asyncio
import inspect
import time
import traceback
from datetime import datetime
from functools import wraps
from typing import Optional, Callable, Any, Dict, List

from crawlo.logging import get_logger
from crawlo.exceptions import DetailedException, ErrorContext


class ErrorHandler:
    """统一的错误处理器"""
    
    def __init__(self, logger_name: str = __name__, log_level: str = 'ERROR'):
        self.logger = get_logger(logger_name)
        self.error_history: List[Dict] = []  # 错误历史记录
        self.max_history_size = 100  # 最大历史记录数
    
    def handle_error(self, exception: Exception, context: Optional[ErrorContext] = None, 
                     raise_error: bool = True, log_error: bool = True,
                     extra_info: Optional[Dict] = None) -> Dict:
        """
        统一的错误处理
        
        Args:
            exception: 异常对象
            context: 错误上下文信息
            raise_error: 是否重新抛出异常
            log_error: 是否记录错误日志
            extra_info: 额外的错误信息
            
        Returns:
            包含错误详情的字典
        """
        # 构建错误详情
        error_details = {
            "exception": exception,
            "exception_type": type(exception).__name__,
            "message": str(exception),
            "context": str(context) if context else None,
            "timestamp": datetime.now().isoformat(),
            "traceback": traceback.format_exc() if log_error else None,
            "extra_info": extra_info or {}
        }
        
        # 记录到历史
        self._record_error(error_details)
        
        # 记录日志
        if log_error:
            self._log_error(error_details)
        
        # 重新抛出异常
        if raise_error:
            raise exception
        
        return error_details
    
    def _log_error(self, error_details: Dict):
        """记录错误日志"""
        # 基本错误信息
        context_info = error_details.get("context", "")
        message = error_details["message"]
        error_msg = f"{message} [{context_info}]" if context_info else message
        
        # 记录错误
        self.logger.error(error_msg)
        
        # 记录详细信息
        if error_details.get("traceback"):
            self.logger.debug(f"详细错误信息:\n{error_details['traceback']}")
        
        # 记录额外信息
        if error_details.get("extra_info"):
            self.logger.debug(f"额外信息: {error_details['extra_info']}")
    
    def _record_error(self, error_details: Dict):
        """记录错误到历史"""
        self.error_history.append(error_details)
        # 限制历史记录大小
        if len(self.error_history) > self.max_history_size:
            self.error_history.pop(0)
    
    def safe_call(self, func: Callable, *args, default_return=None, 
                  context: Optional[ErrorContext] = None, **kwargs) -> Any:
        """
        安全调用函数，捕获并处理异常
        
        Args:
            func: 要调用的函数
            *args: 函数参数
            default_return: 默认返回值
            context: 错误上下文
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
                         exceptions: tuple = (Exception,), backoff_factor: float = 1.0,
                         context: Optional[ErrorContext] = None):
        """
        装饰器：失败时重试
        
        Args:
            max_retries: 最大重试次数
            delay: 初始重试间隔（秒）
            exceptions: 需要重试的异常类型
            backoff_factor: 退避因子（每次重试间隔乘以此因子）
            context: 错误上下文
        """
        def decorator(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                last_exception = None
                current_delay = delay
                
                for attempt in range(max_retries + 1):
                    try:
                        return await func(*args, **kwargs)
                    except exceptions as e:
                        last_exception = e
                        if attempt < max_retries:
                            self.logger.warning(
                                f"Function {func.__name__} failed (attempt {attempt + 1}/{max_retries + 1}): {e}"
                            )
                            
                            await asyncio.sleep(current_delay)
                            current_delay *= backoff_factor  # 指数退避
                        else:
                            # Last attempt failed
                            self.logger.error(
                                f"Function {func.__name__} failed after {max_retries + 1} attempts: {e}"
                            )
                raise last_exception
            
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                last_exception = None
                current_delay = delay
                
                for attempt in range(max_retries + 1):
                    try:
                        return func(*args, **kwargs)
                    except exceptions as e:
                        last_exception = e
                        if attempt < max_retries:
                            self.logger.warning(
                                f"Function {func.__name__} failed (attempt {attempt + 1}/{max_retries + 1}): {e}"
                            )
                            
                            time.sleep(current_delay)
                            current_delay *= backoff_factor  # 指数退避
                        else:
                            # Last attempt failed
                            self.logger.error(
                                f"Function {func.__name__} failed after {max_retries + 1} attempts: {e}"
                            )
                raise last_exception
            
            # Return appropriate wrapper based on function type
            if inspect.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper
        
        return decorator
    
    def get_error_history(self) -> List[Dict]:
        """获取错误历史记录"""
        return self.error_history.copy()
    
    def clear_error_history(self):
        """清空错误历史记录"""
        self.error_history.clear()


def _get_global_error_handler() -> ErrorHandler:
    """获取全局 ErrorHandler 单例（存储于 ApplicationContext）"""
    from crawlo.core.application import get_global_context
    ctx = get_global_context()
    if ctx.error_handler_instance is None:
        ctx.error_handler_instance = ErrorHandler()
    return ctx.error_handler_instance


def handle_exception(context: str = "", module: str = "", function: str = "",
                     raise_error: bool = True, log_error: bool = True,
                     error_code: Optional[str] = None):
    """
    装饰器：处理函数异常
    
    Args:
        context: 错误上下文描述
        module: 模块名称
        function: 函数名称
        raise_error: 是否重新抛出异常
        log_error: 是否记录错误日志
        error_code: 错误代码
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                error_context = ErrorContext(
                    context=f"{context} - {func.__name__}",
                    module=module,
                    function=func.__name__
                )
                _handler = _get_global_error_handler()
                if isinstance(e, DetailedException):
                    if not e.context:
                        e.context = error_context
                    _handler.handle_error(
                        e, context=e.context,
                        raise_error=raise_error, log_error=log_error
                    )
                else:
                    detailed_e = DetailedException(
                        str(e), context=error_context, error_code=error_code
                    )
                    _handler.handle_error(
                        detailed_e, context=error_context,
                        raise_error=raise_error, log_error=log_error
                    )
                if not raise_error:
                    return None
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_context = ErrorContext(
                    context=f"{context} - {func.__name__}",
                    module=module,
                    function=func.__name__
                )
                _handler = _get_global_error_handler()
                if isinstance(e, DetailedException):
                    if not e.context:
                        e.context = error_context
                    _handler.handle_error(
                        e, context=e.context,
                        raise_error=raise_error, log_error=log_error
                    )
                else:
                    detailed_e = DetailedException(
                        str(e), context=error_context, error_code=error_code
                    )
                    _handler.handle_error(
                        detailed_e, context=error_context,
                        raise_error=raise_error, log_error=log_error
                    )
                if not raise_error:
                    return None
        
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

