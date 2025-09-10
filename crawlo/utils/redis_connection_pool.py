#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
Redis连接池优化工具
提供优化的Redis连接池管理和配置
"""
import asyncio
import redis.asyncio as aioredis
from typing import Dict, Any, Optional, Union
from contextlib import asynccontextmanager

from crawlo.utils.log import get_logger
from crawlo.utils.error_handler import ErrorHandler


class OptimizedRedisConnectionPool:
    """优化的Redis连接池管理器"""
    
    # 默认连接池配置
    DEFAULT_CONFIG = {
        'max_connections': 50,
        'socket_connect_timeout': 5,
        'socket_timeout': 30,
        'socket_keepalive': True,
        'health_check_interval': 30,
        'retry_on_timeout': True,
        'encoding': 'utf-8',
        'decode_responses': False,
    }
    
    def __init__(self, redis_url: str, **kwargs):
        self.redis_url = redis_url
        self.config = {**self.DEFAULT_CONFIG, **kwargs}
        self.logger = get_logger(self.__class__.__name__)
        self.error_handler = ErrorHandler(self.__class__.__name__)
        
        # 连接池实例
        self._connection_pool: Optional[aioredis.ConnectionPool] = None
        self._redis_client: Optional[aioredis.Redis] = None
        
        # 连接池统计信息
        self._stats = {
            'created_connections': 0,
            'active_connections': 0,
            'idle_connections': 0,
            'errors': 0
        }
        
        # 初始化连接池
        self._initialize_pool()
    
    def _initialize_pool(self):
        """初始化连接池"""
        try:
            self._connection_pool = aioredis.ConnectionPool.from_url(
                self.redis_url,
                **self.config
            )
            
            self._redis_client = aioredis.Redis(
                connection_pool=self._connection_pool
            )
            
            self.logger.info(f"✅ Redis连接池初始化成功: {self.redis_url}")
            self.logger.debug(f"   连接池配置: {self.config}")
            
        except Exception as e:
            self.error_handler.handle_error(
                e, 
                context="Redis连接池初始化失败", 
                raise_error=True
            )
    
    async def get_connection(self) -> aioredis.Redis:
        """
        获取Redis连接实例
        
        Returns:
            Redis连接实例
        """
        if not self._redis_client:
            await self._initialize_pool()
        
        self._stats['active_connections'] += 1
        return self._redis_client
    
    async def ping(self) -> bool:
        """
        检查Redis连接是否正常
        
        Returns:
            连接是否正常
        """
        try:
            if self._redis_client:
                await self._redis_client.ping()
                return True
            return False
        except Exception as e:
            self.logger.warning(f"Redis连接检查失败: {e}")
            return False
    
    async def close(self):
        """关闭连接池"""
        try:
            if self._redis_client:
                await self._redis_client.close()
                self._redis_client = None
            
            if self._connection_pool:
                await self._connection_pool.disconnect()
                self._connection_pool = None
                
            self.logger.info("✅ Redis连接池已关闭")
        except Exception as e:
            self.error_handler.handle_error(
                e, 
                context="关闭Redis连接池失败", 
                raise_error=False
            )
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取连接池统计信息
        
        Returns:
            统计信息字典
        """
        if self._connection_pool:
            pool_stats = {
                'max_connections': self._connection_pool.max_connections,
                'created_connections': self._connection_pool.created_connections,
                'available_connections': len(self._connection_pool._available_connections),
                'in_use_connections': len(self._connection_pool._in_use_connections),
            }
            self._stats.update(pool_stats)
        
        return self._stats.copy()
    
    @asynccontextmanager
    async def connection_context(self):
        """
        连接上下文管理器
        
        Yields:
            Redis连接实例
        """
        connection = await self.get_connection()
        try:
            yield connection
        finally:
            self._stats['active_connections'] -= 1
            self._stats['idle_connections'] += 1


class RedisBatchOperationHelper:
    """Redis批量操作助手"""
    
    def __init__(self, redis_client: aioredis.Redis, batch_size: int = 100):
        self.redis_client = redis_client
        self.batch_size = batch_size
        self.logger = get_logger(self.__class__.__name__)
        self.error_handler = ErrorHandler(self.__class__.__name__)
    
    async def batch_execute(self, operations: list, batch_size: Optional[int] = None) -> list:
        """
        批量执行Redis操作
        
        Args:
            operations: 操作列表，每个操作是一个包含(command, *args)的元组
            batch_size: 批次大小（如果为None则使用实例的batch_size）
            
        Returns:
            执行结果列表
        """
        actual_batch_size = batch_size or self.batch_size
        results = []
        
        try:
            for i in range(0, len(operations), actual_batch_size):
                batch = operations[i:i + actual_batch_size]
                self.logger.debug(f"执行批次 {i//actual_batch_size + 1}/{(len(operations)-1)//actual_batch_size + 1}")
                
                try:
                    pipe = self.redis_client.pipeline()
                    for operation in batch:
                        command, *args = operation
                        getattr(pipe, command)(*args)
                    
                    batch_results = await pipe.execute()
                    results.extend(batch_results)
                    
                except Exception as e:
                    self.logger.error(f"执行批次失败: {e}")
                    # 继续执行下一个批次而不是中断
        
        except Exception as e:
            self.error_handler.handle_error(
                e, 
                context="Redis批量操作执行失败", 
                raise_error=False
            )
        
        return results
    
    async def batch_set_hash(self, hash_key: str, items: Dict[str, Any]) -> int:
        """
        批量设置Hash字段
        
        Args:
            hash_key: Hash键名
            items: 要设置的字段字典
            
        Returns:
            成功设置的字段数量
        """
        try:
            if not items:
                return 0
            
            pipe = self.redis_client.pipeline()
            count = 0
            
            for key, value in items.items():
                pipe.hset(hash_key, key, value)
                count += 1
                
                # 每达到批次大小就执行一次
                if count % self.batch_size == 0:
                    await pipe.execute()
                    pipe = self.redis_client.pipeline()
            
            # 执行剩余的操作
            if count % self.batch_size != 0:
                await pipe.execute()
            
            self.logger.debug(f"批量设置Hash {count} 个字段")
            return count
            
        except Exception as e:
            self.error_handler.handle_error(
                e, 
                context="Redis批量设置Hash失败", 
                raise_error=False
            )
            return 0
    
    async def batch_get_hash(self, hash_key: str, fields: list) -> Dict[str, Any]:
        """
        批量获取Hash字段值
        
        Args:
            hash_key: Hash键名
            fields: 要获取的字段列表
            
        Returns:
            字段值字典
        """
        try:
            if not fields:
                return {}
            
            # 使用管道批量获取
            pipe = self.redis_client.pipeline()
            for field in fields:
                pipe.hget(hash_key, field)
            
            results = await pipe.execute()
            
            # 构建结果字典
            result_dict = {}
            for i, field in enumerate(fields):
                if results[i] is not None:
                    result_dict[field] = results[i]
            
            self.logger.debug(f"批量获取Hash {len(result_dict)} 个字段")
            return result_dict
            
        except Exception as e:
            self.error_handler.handle_error(
                e, 
                context="Redis批量获取Hash失败", 
                raise_error=False
            )
            return {}


# 全局连接池管理器
_connection_pools: Dict[str, OptimizedRedisConnectionPool] = {}


def get_redis_pool(redis_url: str, **kwargs) -> OptimizedRedisConnectionPool:
    """
    获取Redis连接池实例（单例模式）
    
    Args:
        redis_url: Redis URL
        **kwargs: 连接池配置参数
        
    Returns:
        Redis连接池实例
    """
    if redis_url not in _connection_pools:
        _connection_pools[redis_url] = OptimizedRedisConnectionPool(redis_url, **kwargs)
    
    return _connection_pools[redis_url]


async def close_all_pools():
    """关闭所有连接池"""
    global _connection_pools
    
    for pool in _connection_pools.values():
        await pool.close()
    
    _connection_pools.clear()


# 便捷函数
async def execute_redis_batch(redis_url: str, operations: list, batch_size: int = 100) -> list:
    """
    便捷函数：执行Redis批量操作
    
    Args:
        redis_url: Redis URL
        operations: 操作列表
        batch_size: 批次大小
        
    Returns:
        执行结果列表
    """
    pool = get_redis_pool(redis_url)
    redis_client = await pool.get_connection()
    helper = RedisBatchOperationHelper(redis_client, batch_size)
    return await helper.batch_execute(operations)