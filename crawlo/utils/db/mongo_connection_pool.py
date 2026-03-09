#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
MongoDB连接池管理器
====================

提供单例模式的MongoDB连接管理，确保多个爬虫共享同一个客户端，
避免重复创建连接导致的资源浪费。

特点：
1. 单例模式 - 全局唯一的客户端实例
2. 线程安全 - 使用异步锁保护初始化过程
3. 配置隔离 - 支持不同的数据库配置创建不同的客户端
4. 自动清理 - 支持资源清理和重置
"""

import asyncio
from typing import Dict, Optional, Any
from crawlo.logging import get_logger


# MongoDB 相关导入
try:
    from motor.motor_asyncio import AsyncIOMotorClient
    MONGO_AVAILABLE = True
except ImportError:
    AsyncIOMotorClient = None
    MONGO_AVAILABLE = False


class MongoConnectionPoolManager:
    """MongoDB连接池管理器（单例模式）"""
    
    _instances: Dict[str, 'MongoConnectionPoolManager'] = {}
    _lock = asyncio.Lock()
    
    def __init__(self, pool_key: str):
        """
        初始化连接池管理器
        
        Args:
            pool_key: 连接池唯一标识
        """
        self.pool_key = pool_key
        self.client = None
        self._pool_lock = asyncio.Lock()
        self._pool_initialized = False
        self._config: Dict[str, Any] = {}
        self.logger = get_logger(f'MongoPool.{pool_key}')
    
    @classmethod
    async def get_client(
        cls,
        mongo_uri: str = 'mongodb://localhost:27017',
        db_name: str = 'crawlo',
        max_pool_size: int = 100,
        min_pool_size: int = 10,
        connect_timeout_ms: int = 5000,
        socket_timeout_ms: int = 30000,
        **kwargs
    ):
        """
        获取 MongoDB 客户端实例（单例模式）
        
        Args:
            mongo_uri: MongoDB 连接 URI
            db_name: 数据库名
            max_pool_size: 最大连接池大小
            min_pool_size: 最小连接池大小
            connect_timeout_ms: 连接超时（毫秒）
            socket_timeout_ms: Socket 超时（毫秒）
            **kwargs: 其他连接参数
            
        Returns:
            MongoDB 客户端实例
        """
        # 生成连接池唯一标识
        pool_key = f"{mongo_uri}:{db_name}"
        
        async with cls._lock:
            if pool_key not in cls._instances:
                instance = cls(pool_key)
                instance._config = {
                    'mongo_uri': mongo_uri,
                    'db_name': db_name,
                    'max_pool_size': max_pool_size,
                    'min_pool_size': min_pool_size,
                    'connect_timeout_ms': connect_timeout_ms,
                    'socket_timeout_ms': socket_timeout_ms,
                    **kwargs
                }
                cls._instances[pool_key] = instance
                instance.logger.info(
                    f"创建新的 MongoDB 连接池管理器: {pool_key} "
                    f"(minPoolSize={min_pool_size}, maxPoolSize={max_pool_size})"
                )
            
            instance = cls._instances[pool_key]
            await instance._ensure_client()
            return instance.client
    
    async def _ensure_client(self):
        """确保MongoDB客户端已初始化（线程安全）"""
        if self._pool_initialized and self.client:
            return
        
        async with self._pool_lock:
            if not self._pool_initialized:
                try:
                    if AsyncIOMotorClient is None:
                        raise RuntimeError("motor 不可用，请安装 motor")
                    self.client = AsyncIOMotorClient(
                        self._config['mongo_uri'],
                        maxPoolSize=self._config['max_pool_size'],
                        minPoolSize=self._config['min_pool_size'],
                        connectTimeoutMS=self._config['connect_timeout_ms'],
                        socketTimeoutMS=self._config['socket_timeout_ms']
                    )
                    
                    self._pool_initialized = True
                    self.logger.info(
                        f"MongoDB 客户端初始化成功: {self.pool_key} "
                        f"(minPoolSize={self._config['min_pool_size']}, "
                        f"maxPoolSize={self._config['max_pool_size']})"
                    )
                except Exception as e:
                    self.logger.error(f"MongoDB 客户端初始化失败: {e}")
                    self._pool_initialized = False
                    self.client = None
                    raise
    
    @classmethod
    async def close_all_clients(cls):
        """关闭所有 MongoDB 客户端"""
        logger = get_logger('MongoPool')
        logger.debug(f"开始关闭所有 MongoDB 客户端，共 {len(cls._instances)} 个")
        
        for pool_key, instance in cls._instances.items():
            try:
                if instance.client:
                    logger.info(f"关闭 MongoDB 客户端: {pool_key}")
                    instance.client.close()
                    logger.info(f"MongoDB 客户端已关闭: {pool_key}")
            except Exception as e:
                logger.error(f"关闭 MongoDB 客户端 {pool_key} 时发生错误: {e}")
        
        cls._instances.clear()
        logger.debug("所有 MongoDB 客户端已关闭")
    
    @classmethod
    def get_pool_stats(cls) -> Dict[str, Any]:
        """获取所有MongoDB连接池的统计信息"""
        stats = {
            'total_pools': len(cls._instances),
            'pools': {}
        }
        
        for pool_key, instance in cls._instances.items():
            if instance.client:
                stats['pools'][pool_key] = {
                    'uri': instance._config.get('mongo_uri', 'unknown'),
                    'db_name': instance._config.get('db_name', 'unknown'),
                    'min_pool_size': instance._config.get('min_pool_size', 'unknown'),
                    'max_pool_size': instance._config.get('max_pool_size', 'unknown')
                }
        
        return stats


# 便捷函数 - 保持向后兼容性
async def get_mongo_client(
    mongo_uri: str = 'mongodb://localhost:27017',
    db_name: str = 'crawlo',
    max_pool_size: int = 100,
    min_pool_size: int = 10,
    connect_timeout_ms: int = 5000,
    socket_timeout_ms: int = 30000,
    **kwargs
):
    """
    获取 MongoDB 客户端实例（便捷函数）
    
    Args:
        mongo_uri: MongoDB 连接 URI
        db_name: 数据库名
        max_pool_size: 最大连接池大小
        min_pool_size: 最小连接池大小
        connect_timeout_ms: 连接超时（毫秒）
        socket_timeout_ms: Socket 超时（毫秒）
        **kwargs: 其他连接参数
        
    Returns:
        MongoDB 客户端实例
    """
    if not MONGO_AVAILABLE:
        raise RuntimeError("MongoDB 支持不可用，请安装 motor")
    
    return await MongoConnectionPoolManager.get_client(
        mongo_uri=mongo_uri,
        db_name=db_name,
        max_pool_size=max_pool_size,
        min_pool_size=min_pool_size,
        connect_timeout_ms=connect_timeout_ms,
        socket_timeout_ms=socket_timeout_ms,
        **kwargs
    )


async def close_all_mongo_clients():
    """关闭所有 MongoDB 客户端"""
    logger = get_logger('MongoPool')
    logger.debug("开始关闭所有 MongoDB 客户端")
    
    await MongoConnectionPoolManager.close_all_clients()
    
    logger.debug("所有 MongoDB 客户端已关闭")


def get_mongo_pool_stats() -> Dict[str, Any]:
    """获取所有MongoDB连接池的统计信息"""
    return MongoConnectionPoolManager.get_pool_stats()