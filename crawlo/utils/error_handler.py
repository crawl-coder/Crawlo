#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
错误处理工具
提供详细、一致的错误处理和日志记录机制
"""
import traceback
from functools import wraps
from datetime import datetime
from typing import Optional, Callable, Any, Dict, List

from crawlo.logging import get_logger


class ErrorContext:
    """错误上下文信息"""
    
    def __init__(self, context: str = "", module: str = "", function: str = ""):
        self.context = context
        self.module = module
        self.function = function
        self.timestamp = datetime.now()
        
    def __str__(self):
        parts = []
        if self.module:
            parts.append(f"Module: {self.module}")
        if self.function:
            parts.append(f"Function: {self.function}")
        if self.context:
            parts.append(f"Context: {self.context}")
        parts.append(f"Time: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        return " | ".join(parts)


class DetailedException(Exception):
    """带有详细信息的异常基类"""
    
    def __init__(self, message: str, context: Optional[ErrorContext] = None, 
                 error_code: Optional[str] = None, **kwargs):
        super().__init__(message)
        self.context = context
        self.error_code = error_code
        self.details = kwargs
        self.timestamp = datetime.now()
        
    def __str__(self):
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
                            # 记录重试信息
                            retry_context = ErrorContext(
                                context=f"函数 {func.__name__} 执行失败 (尝试 {attempt + 1}/{max_retries + 1})",
                                module=context.module if context else "",
                                function=func.__name__
                            ) if context else None
                            
                            self.logger.warning(
                                f"函数 {func.__name__} 执行失败 (尝试 {attempt + 1}/{max_retries + 1}): {e}"
                            )
                            
                            import asyncio
                            await asyncio.sleep(current_delay)
                            current_delay *= backoff_factor  # 指数退避
                        else:
                            # 最后一次尝试失败
                            final_context = ErrorContext(
                                context=f"函数 {func.__name__} 执行失败，已达到最大重试次数",
                                module=context.module if context else "",
                                function=func.__name__
                            ) if context else None
                            
                            self.logger.error(
                                f"函数 {func.__name__} 执行失败，已达到最大重试次数: {e}"
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
                            # 记录重试信息
                            retry_context = ErrorContext(
                                context=f"函数 {func.__name__} 执行失败 (尝试 {attempt + 1}/{max_retries + 1})",
                                module=context.module if context else "",
                                function=func.__name__
                            ) if context else None
            
                            self.logger.warning(
                                f"函数 {func.__name__} 执行失败 (尝试 {attempt + 1}/{max_retries + 1}): {e}"
                            )
                            
                            import time
                            time.sleep(current_delay)
                            current_delay *= backoff_factor  # 指数退避
                        else:
                            # 最后一次尝试失败
                            final_context = ErrorContext(
                                context=f"函数 {func.__name__} 执行失败，已达到最大重试次数",
                                module=context.module if context else "",
                                function=func.__name__
                            ) if context else None
                            
                            self.logger.error(
                                f"函数 {func.__name__} 执行失败，已达到最大重试次数: {e}"
                            )
                raise last_exception
            
            # 根据函数是否为异步函数返回相应的包装器
            import inspect
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


# 全局错误处理器实例
error_handler = ErrorHandler()

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
                
                # 如果是详细异常，保留原有信息
                if isinstance(e, DetailedException):
                    # 确保上下文信息完整
                    if not e.context:
                        e.context = error_context
                    error_handler.handle_error(
                        e, context=e.context,
                        raise_error=raise_error, log_error=log_error
                    )
                else:
                    # 包装为详细异常
                    detailed_e = DetailedException(
                        str(e), context=error_context, error_code=error_code
                    )
                    error_handler.handle_error(
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
                
                # 如果是详细异常，保留原有信息
                if isinstance(e, DetailedException):
                    # 确保上下文信息完整
                    if not e.context:
                        e.context = error_context
                    error_handler.handle_error(
                        e, context=e.context,
                        raise_error=raise_error, log_error=log_error
                    )
                else:
                    # 包装为详细异常
                    detailed_e = DetailedException(
                        str(e), context=error_context, error_code=error_code
                    )
                    error_handler.handle_error(
                        detailed_e, context=error_context,
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

