#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
统一批处理管理器
整合所有批处理相关功能
"""
import asyncio
from functools import wraps
from typing import List, Callable, Any, Optional, Dict

from crawlo.utils.error_handler import ErrorHandler, ErrorContext
from crawlo.logging import get_logger

# 尝试导入Redis支持
try:
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    aioredis = None
    REDIS_AVAILABLE = False


class BatchProcessor:
    """通用批处理处理器"""
    
    def __init__(self, batch_size: int = 100, max_concurrent_batches: int = 5):
        self.batch_size = batch_size
        self.max_concurrent_batches = max_concurrent_batches
        self.logger = get_logger(self.__class__.__name__)
        self.error_handler = ErrorHandler(self.__class__.__name__)
    
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
        results = []
        semaphore = asyncio.Semaphore(self.max_concurrent_batches)
        
        async def process_item(item):
            async with semaphore:
                try:
                    if asyncio.iscoroutinefunction(processor_func):
                        return await processor_func(item, *args, **kwargs)
                    else:
                        return processor_func(item, *args, **kwargs)
                except Exception as e:
                    self.logger.error(f"处理单项失败: {e}")
                    return None
        
        # 并发处理批次中的所有项
        tasks = [process_item(item) for item in items]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 过滤掉异常结果
        return [result for result in results if not isinstance(result, Exception)]
    
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
        all_results = []
        
        # 将数据分批处理
        for i in range(0, len(items), self.batch_size):
            batch = items[i:i + self.batch_size]
            self.logger.debug(f"处理批次 {i//self.batch_size + 1}/{(len(items)-1)//self.batch_size + 1}")
            
            try:
                batch_results = await self.process_batch(batch, processor_func, *args, **kwargs)
                all_results.extend(batch_results)
            except Exception as e:
                self.logger.error(f"处理批次失败: {e}")
                # 继续处理下一个批次而不是中断
        
        return all_results
    
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
                processor = BatchProcessor(actual_batch_size, self.max_concurrent_batches)
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
    """Redis批处理处理器"""
    
    def __init__(self, redis_client, batch_size: int = 100):
        self.redis_client = redis_client
        self.batch_size = batch_size
        self.logger = get_logger(self.__class__.__name__)
        self.error_handler = ErrorHandler(self.__class__.__name__)
    
    async def batch_set(self, items: List[Dict[str, Any]]) -> int:
        """
        批量设置Redis键值对
        
        Args:
            items: 包含key和value的字典列表
            
        Returns:
            成功设置的键值对数量
        """
        try:
            pipe = self.redis_client.pipeline()
            count = 0
            
            for item in items:
                if 'key' in item and 'value' in item:
                    pipe.set(item['key'], item['value'])
                    count += 1
                    
                    # 每达到批次大小就执行一次
                    if count % self.batch_size == 0:
                        result = pipe.execute()
                        # 处理可能的异步情况
                        if asyncio.iscoroutine(result):
                            await result
                        pipe = self.redis_client.pipeline()
            
            # 执行剩余的操作
            if count % self.batch_size != 0:
                result = pipe.execute()
                # 处理可能的异步情况
                if asyncio.iscoroutine(result):
                    await result
            
            self.logger.debug(f"批量设置 {count} 个键值对")
            return count
        except Exception as e:
            self.error_handler.handle_error(
                e, 
                context=ErrorContext(context="Redis批量设置失败"), 
                raise_error=False
            )
            return 0
    
    async def batch_get(self, keys: List[str]) -> Dict[str, Any]:
        """
        批量获取Redis键值
        
        Args:
            keys: 要获取的键列表
            
        Returns:
            键值对字典
        """
        try:
            # 使用管道批量获取
            pipe = self.redis_client.pipeline()
            for key in keys:
                pipe.get(key)
            
            result = pipe.execute()
            # 处理可能的异步情况
            if asyncio.iscoroutine(result):
                results = await result
            else:
                results = result
            
            # 构建结果字典
            result_dict = {}
            for i, key in enumerate(keys):
                if results[i] is not None:
                    result_dict[key] = results[i]
            
            self.logger.debug(f"批量获取 {len(result_dict)} 个键值对")
            return result_dict
        except Exception as e:
            self.error_handler.handle_error(
                e, 
                context=ErrorContext(context="Redis批量获取失败"), 
                raise_error=False
            )
            return {}
    
    async def batch_delete(self, keys: List[str]) -> int:
        """
        批量删除Redis键
        
        Args:
            keys: 要删除的键列表
            
        Returns:
            成功删除的键数量
        """
        try:
            pipe = self.redis_client.pipeline()
            count = 0
            
            for key in keys:
                pipe.delete(key)
                count += 1
                
                # 每达到批次大小就执行一次
                if count % self.batch_size == 0:
                    result = pipe.execute()
                    # 处理可能的异步情况
                    if asyncio.iscoroutine(result):
                        await result
                    pipe = self.redis_client.pipeline()
            
            # 执行剩余的操作
            if count % self.batch_size != 0:
                result = pipe.execute()
                # 处理可能的异步情况
                if asyncio.iscoroutine(result):
                    await result
            
            self.logger.debug(f"批量删除 {count} 个键")
            return count
        except Exception as e:
            self.error_handler.handle_error(
                e, 
                context=ErrorContext(context="Redis批量删除失败"), 
                raise_error=False
            )
            return 0


# 便利函数
async def process_in_batches(items: List[Any], processor_func: Callable,
                            batch_size: int = 100, max_concurrent_batches: int = 5,
                            *args, **kwargs) -> List[Any]:
    """
    便利函数：分批处理大量数据项
    
    Args:
        items: 要处理的数据项列表
        processor_func: 处理函数
        batch_size: 批次大小
        max_concurrent_batches: 最大并发批次数
        *args: 传递给处理函数的额外参数
        **kwargs: 传递给处理函数的关键字参数
        
    Returns:
        所有处理结果的列表
    """
    processor = BatchProcessor(batch_size, max_concurrent_batches)
    return await processor.process_in_batches(items, processor_func, *args, **kwargs)


def batch_process(batch_size: int = 100, max_concurrent_batches: int = 5):
    """
    装饰器：将函数转换为批处理函数
    
    Args:
        batch_size: 批次大小
        max_concurrent_batches: 最大并发批次数
    """
    def decorator(func):
        def wrapper(items: List[Any], *args, **kwargs):
            # 检查是否有batch_size或max_concurrent_batches参数在kwargs中
            actual_batch_size = kwargs.pop('batch_size', batch_size)
            actual_max_concurrent = kwargs.pop('max_concurrent_batches', max_concurrent_batches)
            
            processor = BatchProcessor(actual_batch_size, actual_max_concurrent)
            return asyncio.run(processor.process_in_batches(items, func, *args, **kwargs))
        
        return wrapper
    
    return decorator
