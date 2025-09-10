#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
# @Time    : 2025-09-10 22:00
# @Author  : crawl-coder
# @Desc    : 重试机制工具
"""

import time
import random
import asyncio
from typing import Callable, Any, Optional, Tuple, Set
from functools import wraps


class RetryMechanism:
    """重试机制工具类"""

    # 默认应该重试的HTTP状态码
    DEFAULT_RETRY_STATUS_CODES = {429, 500, 502, 503, 504}
    
    # 默认应该重试的异常类型
    DEFAULT_RETRY_EXCEPTIONS = (
        ConnectionError,
        TimeoutError,
        asyncio.TimeoutError,
    )

    def __init__(self, max_retries: int = 3, 
                 retry_status_codes: Optional[Set[int]] = None,
                 retry_exceptions: Optional[Tuple[type, ...]] = None):
        """
        初始化重试机制
        
        Args:
            max_retries (int): 最大重试次数
            retry_status_codes (Optional[Set[int]]): 应该重试的HTTP状态码
            retry_exceptions (Optional[Tuple[type, ...]]): 应该重试的异常类型
        """
        self.max_retries = max_retries
        self.retry_status_codes = retry_status_codes or self.DEFAULT_RETRY_STATUS_CODES
        self.retry_exceptions = retry_exceptions or self.DEFAULT_RETRY_EXCEPTIONS

    def should_retry(self, status_code: Optional[int] = None, 
                     exception: Optional[Exception] = None) -> bool:
        """
        判断是否应该重试
        
        Args:
            status_code (Optional[int]): HTTP状态码
            exception (Optional[Exception]): 异常对象
            
        Returns:
            bool: 是否应该重试
        """
        # 如果有状态码，检查是否在重试列表中
        if status_code is not None and status_code in self.retry_status_codes:
            return True
            
        # 如果有异常，检查是否在重试列表中
        if exception is not None and isinstance(exception, self.retry_exceptions):
            return True
            
        return False

    def exponential_backoff(self, attempt: int, base_delay: float = 1.0, 
                           max_delay: float = 60.0) -> float:
        """
        计算指数退避延迟时间
        
        Args:
            attempt (int): 当前重试次数
            base_delay (float): 基础延迟时间（秒）
            max_delay (float): 最大延迟时间（秒）
            
        Returns:
            float: 延迟时间（秒）
        """
        # 计算基本延迟：base_delay * (2 ^ attempt)
        delay = base_delay * (2 ** attempt)
        
        # 添加随机抖动，避免惊群效应
        jitter = random.uniform(0, 0.1) * delay
        
        # 返回最终延迟时间，不超过最大延迟
        return min(delay + jitter, max_delay)

    async def async_retry(self, func: Callable, *args, **kwargs) -> Any:
        """
        异步重试执行函数
        
        Args:
            func (Callable): 要执行的函数
            *args: 函数参数
            **kwargs: 函数关键字参数
            
        Returns:
            Any: 函数执行结果
            
        Raises:
            Exception: 如果超过最大重试次数仍未成功，则抛出最后一个异常
        """
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                result = await func(*args, **kwargs)
                
                # 如果函数返回状态码，检查是否需要重试
                if hasattr(result, 'status') and self.should_retry(status_code=result.status):
                    if attempt < self.max_retries:
                        delay = self.exponential_backoff(attempt)
                        await asyncio.sleep(delay)
                        continue
                    else:
                        raise Exception(f"HTTP {result.status} after {self.max_retries} retries")
                
                return result
                
            except Exception as e:
                last_exception = e
                
                # 检查是否应该重试
                if self.should_retry(exception=e) and attempt < self.max_retries:
                    delay = self.exponential_backoff(attempt)
                    await asyncio.sleep(delay)
                    continue
                else:
                    raise e
                    
        # 如果到达这里，说明所有重试都失败了
        raise last_exception

    def sync_retry(self, func: Callable, *args, **kwargs) -> Any:
        """
        同步重试执行函数
        
        Args:
            func (Callable): 要执行的函数
            *args: 函数参数
            **kwargs: 函数关键字参数
            
        Returns:
            Any: 函数执行结果
            
        Raises:
            Exception: 如果超过最大重试次数仍未成功，则抛出最后一个异常
        """
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                result = func(*args, **kwargs)
                
                # 如果函数返回状态码，检查是否需要重试
                if hasattr(result, 'status') and self.should_retry(status_code=result.status):
                    if attempt < self.max_retries:
                        delay = self.exponential_backoff(attempt)
                        time.sleep(delay)
                        continue
                    else:
                        raise Exception(f"HTTP {result.status} after {self.max_retries} retries")
                
                return result
                
            except Exception as e:
                last_exception = e
                
                # 检查是否应该重试
                if self.should_retry(exception=e) and attempt < self.max_retries:
                    delay = self.exponential_backoff(attempt)
                    time.sleep(delay)
                    continue
                else:
                    raise e
                    
        # 如果到达这里，说明所有重试都失败了
        raise last_exception


def retry(max_retries: int = 3, 
          retry_status_codes: Optional[Set[int]] = None,
          retry_exceptions: Optional[Tuple[type, ...]] = None):
    """
    重试装饰器
    
    Args:
        max_retries (int): 最大重试次数
        retry_status_codes (Optional[Set[int]]): 应该重试的HTTP状态码
        retry_exceptions (Optional[Tuple[type, ...]]): 应该重试的异常类型
    """
    def decorator(func: Callable) -> Callable:
        retry_mechanism = RetryMechanism(max_retries, retry_status_codes, retry_exceptions)
        
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                return await retry_mechanism.async_retry(func, *args, **kwargs)
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                return retry_mechanism.sync_retry(func, *args, **kwargs)
            return sync_wrapper
            
    return decorator


# 便捷函数
def should_retry(status_code: Optional[int] = None, 
                 exception: Optional[Exception] = None) -> bool:
    """判断是否应该重试"""
    retry_mechanism = RetryMechanism()
    return retry_mechanism.should_retry(status_code, exception)


def exponential_backoff(attempt: int, base_delay: float = 1.0, 
                       max_delay: float = 60.0) -> float:
    """计算指数退避延迟时间"""
    retry_mechanism = RetryMechanism()
    return retry_mechanism.exponential_backoff(attempt, base_delay, max_delay)