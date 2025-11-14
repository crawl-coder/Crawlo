#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
批处理操作工具（已弃用）
请使用 crawlo.utils.batch_manager 替代
"""
import asyncio
from functools import wraps
from typing import List, Callable, Any, Optional, Dict

from crawlo.utils.error_handler import ErrorHandler
from crawlo.logging import get_logger


class BatchProcessor:
    """批处理处理器（已弃用）"""
    
    def __init__(self, batch_size: int = 100, max_concurrent_batches: int = 5):
        self.batch_size = batch_size
        self.max_concurrent_batches = max_concurrent_batches
        self.logger = get_logger(self.__class__.__name__)
        self.error_handler = ErrorHandler(self.__class__.__name__)
        self.logger.warning("BatchProcessor 已弃用，请使用 crawlo.utils.batch_manager.BatchProcessor")
    
    async def process_batch(self, items: List[Any], processor_func: Callable, 
                           *args, **kwargs) -> List[Any]:
        """
        处理一批数据项
        
        Args:
            items: 要处理的数据项列表
            processor_func: 处理函数
            *args: 传递给处理函数的额外参数
            **kwargs: 传递给处理函数的关键字参数
            
        Returns:
            处理结果列表
        """
        # 为了向后兼容，仍然提供实现
        from crawlo.utils.batch_manager import BatchProcessor as NewBatchProcessor
        new_processor = NewBatchProcessor(self.batch_size, self.max_concurrent_batches)
        return await new_processor.process_batch(items, processor_func, *args, **kwargs)
    
    async def process_in_batches(self, items: List[Any], processor_func: Callable,
                                *args, **kwargs) -> List[Any]:
        """
        分批处理大量数据项
        
        Args:
            items: 要处理的数据项列表
            processor_func: 处理函数
            *args: 传递给处理函数的额外参数
            **kwargs: 传递给处理函数的关键字参数
            
        Returns:
            所有处理结果的列表
        """
        # 为了向后兼容，仍然提供实现
        from crawlo.utils.batch_manager import BatchProcessor as NewBatchProcessor
        new_processor = NewBatchProcessor(self.batch_size, self.max_concurrent_batches)
        return await new_processor.process_in_batches(items, processor_func, *args, **kwargs)
    
    def batch_process_decorator(self, batch_size: Optional[int] = None):
        """
        装饰器：将函数转换为批处理函数
        
        Args:
            batch_size: 批次大小（如果为None则使用实例的batch_size）
        """
        def decorator(func):
            @wraps(func)
            async def async_wrapper(items: List[Any], *args, **kwargs):
                actual_batch_size = batch_size or self.batch_size
                from crawlo.utils.batch_manager import BatchProcessor as NewBatchProcessor
                processor = NewBatchProcessor(actual_batch_size, self.max_concurrent_batches)
                return await processor.process_in_batches(items, func, *args, **kwargs)
            
            @wraps(func)
            def sync_wrapper(items: List[Any], *args, **kwargs):
                # 同步版本使用事件循环运行异步函数
                return asyncio.run(async_wrapper(items, *args, **kwargs))
            
            # 根据原函数是否为异步函数返回相应的包装器
            import inspect
            if inspect.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper
        
        return decorator


class RedisBatchProcessor:
    """Redis批处理处理器（已弃用）"""
    
    def __init__(self, redis_client, batch_size: int = 100):
        self.redis_client = redis_client
        self.batch_size = batch_size
        self.logger = get_logger(self.__class__.__name__)
        self.error_handler = ErrorHandler(self.__class__.__name__)
        self.logger.warning("RedisBatchProcessor 已弃用，请使用 crawlo.utils.batch_manager.RedisBatchProcessor")
    
    async def batch_set(self, items: List[Dict[str, Any]]) -> int:
        """
        批量设置Redis键值对
        
        Args:
            items: 包含key和value的字典列表
            
        Returns:
            成功设置的键值对数量
        """
        # 为了向后兼容，仍然提供实现
        from crawlo.utils.batch_manager import RedisBatchProcessor as NewRedisBatchProcessor
        new_processor = NewRedisBatchProcessor(self.redis_client, self.batch_size)
        return await new_processor.batch_set(items)
    
    async def batch_get(self, keys: List[str]) -> Dict[str, Any]:
        """
        批量获取Redis键值
        
        Args:
            keys: 要获取的键列表
            
        Returns:
            键值对字典
        """
        # 为了向后兼容，仍然提供实现
        from crawlo.utils.batch_manager import RedisBatchProcessor as NewRedisBatchProcessor
        new_processor = NewRedisBatchProcessor(self.redis_client, self.batch_size)
        return await new_processor.batch_get(keys)
    
    async def batch_delete(self, keys: List[str]) -> int:
        """
        批量删除Redis键
        
        Args:
            keys: 要删除的键列表
            
        Returns:
            成功删除的键数量
        """
        # 为了向后兼容，仍然提供实现
        from crawlo.utils.batch_manager import RedisBatchProcessor as NewRedisBatchProcessor
        new_processor = NewRedisBatchProcessor(self.redis_client, self.batch_size)
        return await new_processor.batch_delete(keys)


# 便利函数
async def process_in_batches(items: List[Any], processor_func: Callable,
                            batch_size: int = 100, max_concurrent_batches: int = 5,
                            *args, **kwargs) -> List[Any]:
    """
    便利函数：分批处理大量数据项（已弃用）
    """
    from crawlo.utils.batch_manager import process_in_batches as new_process_in_batches
    return await new_process_in_batches(items, processor_func, batch_size, max_concurrent_batches, *args, **kwargs)


def batch_process(batch_size: int = 100, max_concurrent_batches: int = 5):
    """
    装饰器：将函数转换为批处理函数（已弃用）
    """
    from crawlo.utils.batch_manager import batch_process as new_batch_process
    return new_batch_process(batch_size, max_concurrent_batches)