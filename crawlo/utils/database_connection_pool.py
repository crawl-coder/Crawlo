#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
统一数据库连接池管理器
====================

提供单例模式的数据库连接池管理，支持 MySQL 和 MongoDB，确保多个爬虫共享同一个连接池，
避免重复创建连接池导致的资源浪费。

特点：
1. 单例模式 - 全局唯一的连接池实例
2. 线程安全 - 使用异步锁保护初始化过程
3. 配置隔离 - 支持不同的数据库配置创建不同的连接池
4. 自动清理 - 支持资源清理和重置
"""

import asyncio
from typing import Dict, Optional, Any
from crawlo.logging import get_logger

# MySQL 相关导入
try:
    import aiomysql
    from asyncmy import create_pool as asyncmy_create_pool
    MYSQL_AVAILABLE = True
except ImportError:
    aiomysql = None
    asyncmy_create_pool = None
    MYSQL_AVAILABLE = False

# MongoDB 相关导入
try:
    from motor.motor_asyncio import AsyncIOMotorClient
    MONGO_AVAILABLE = True
except ImportError:
    AsyncIOMotorClient = None
    MONGO_AVAILABLE = False


class DatabaseConnectionPoolManager:
    """统一数据库连接池管理器（单例模式）"""
    
    _mysql_instances: Dict[str, 'DatabaseConnectionPoolManager'] = {}
    _mongo_instances: Dict[str, 'DatabaseConnectionPoolManager'] = {}
    _lock = asyncio.Lock()
    
    def __init__(self, pool_key: str, db_type: str):
        """
        初始化连接池管理器
        
        Args:
            pool_key: 连接池唯一标识
            db_type: 数据库类型 ('mysql' 或 'mongo')
        """
        self.pool_key = pool_key
        self.db_type = db_type
        self.pool = None
        self.client = None
        self._pool_lock = asyncio.Lock()
        self._pool_initialized = False
        self._config: Dict[str, Any] = {}
        self._pool_type: str = 'asyncmy'  # MySQL默认使用 asyncmy
        self.logger = get_logger(f'DatabasePool.{pool_key}')
    
    @classmethod
    async def get_mysql_pool(
        cls, 
        pool_type: str = 'asyncmy',
        host: str = 'localhost',
        port: int = 3306,
        user: str = 'root',
        password: str = '',
        db: str = 'crawlo',
        minsize: int = 3,
        maxsize: int = 10,
        **kwargs
    ):
        """
        获取MySQL连接池实例（单例模式）
        
        Args:
            pool_type: 连接池类型 ('asyncmy' 或 'aiomysql')
            host: 数据库主机
            port: 数据库端口
            user: 数据库用户名
            password: 数据库密码
            db: 数据库名
            minsize: 最小连接数
            maxsize: 最大连接数
            **kwargs: 其他连接参数
            
        Returns:
            连接池实例
        """
        # 生成连接池唯一标识（修复：加入 user 到 key 中）
        pool_key = f"{pool_type}:{host}:{port}:{db}:{user}"
        
        async with cls._lock:
            if pool_key not in cls._mysql_instances:
                instance = cls(pool_key, 'mysql')
                instance._pool_type = pool_type
                instance._config = {
                    'host': host,
                    'port': port,
                    'user': user,
                    'password': password,
                    'db': db,
                    'minsize': minsize,
                    'maxsize': maxsize,
                    **kwargs
                }
                cls._mysql_instances[pool_key] = instance
                instance.logger.debug(
                    f"创建新的MySQL连接池管理器: {pool_key} "
                    f"(type={pool_type}, minsize={minsize}, maxsize={maxsize})"
                )
            
            instance = cls._mysql_instances[pool_key]
            await instance._ensure_mysql_pool()
            return instance.pool
    
    @classmethod
    async def get_mongo_client(
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
        # 生成连接池唯一标识（修复：移除 db_name，只基于 URI 和连接参数缓存 Client）
        # 注意：如果不同的 db_name 需要不同的权限认证（写在 URI 里），URI 本身就会不同，所以逻辑依然成立。
        pool_key = f"{mongo_uri}"
        
        async with cls._lock:
            if pool_key not in cls._mongo_instances:
                instance = cls(pool_key, 'mongo')
                instance._config = {
                    'mongo_uri': mongo_uri,
                    'db_name': db_name,
                    'max_pool_size': max_pool_size,
                    'min_pool_size': min_pool_size,
                    'connect_timeout_ms': connect_timeout_ms,
                    'socket_timeout_ms': socket_timeout_ms,
                    **kwargs
                }
                cls._mongo_instances[pool_key] = instance
                instance.logger.debug(
                    f"创建新的 MongoDB 连接池管理器: {pool_key} "
                    f"(minPoolSize={min_pool_size}, maxPoolSize={max_pool_size})"
                )
            
            instance = cls._mongo_instances[pool_key]
            await instance._ensure_mongo_client()
            return instance.client
    
    async def _ensure_mysql_pool(self):
        """确保MySQL连接池已初始化（线程安全）"""
        if self._pool_initialized:
            # 检查连接池是否仍然有效
            if self.pool and hasattr(self.pool, 'closed') and not self.pool.closed:
                return
            else:
                self.logger.warning("MySQL连接池已初始化但无效，重新初始化")
        
        async with self._pool_lock:
            if not self._pool_initialized:
                try:
                    if self._pool_type == 'asyncmy':
                        self.pool = await self._create_asyncmy_pool()
                    elif self._pool_type == 'aiomysql':
                        self.pool = await self._create_aiomysql_pool()
                    else:
                        raise ValueError(f"不支持的MySQL连接池类型: {self._pool_type}")
                    
                    self._pool_initialized = True
                    self.logger.info(
                        f"MySQL连接池初始化成功: {self.pool_key} "
                        f"(minsize={self._config['minsize']}, maxsize={self._config['maxsize']})"
                    )
                except Exception as e:
                    self.logger.error(f"MySQL连接池初始化失败: {e}")
                    self._pool_initialized = False
                    self.pool = None
                    raise
    
    async def _ensure_mongo_client(self):
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
    
    async def _create_asyncmy_pool(self):
        """创建 asyncmy 连接池"""
        if asyncmy_create_pool is None:
            raise RuntimeError("asyncmy 不可用，请安装 asyncmy")
        return await asyncmy_create_pool(
            host=self._config['host'],
            port=self._config['port'],
            user=self._config['user'],
            password=self._config['password'],
            db=self._config['db'],
            minsize=self._config['minsize'],
            maxsize=self._config['maxsize'],
            echo=self._config.get('echo', False)
        )
    
    async def _create_aiomysql_pool(self):
        """创建 aiomysql 连接池"""
        if aiomysql is None:
            raise RuntimeError("aiomysql 不可用，请安装 aiomysql")
        return await aiomysql.create_pool(
            host=self._config['host'],
            port=self._config['port'],
            user=self._config['user'],
            password=self._config['password'],
            db=self._config['db'],
            minsize=self._config['minsize'],
            maxsize=self._config['maxsize'],
            cursorclass=aiomysql.DictCursor,
            autocommit=False
        )
    
    @classmethod
    async def close_all_mysql_pools(cls):
        """关闭所有MySQL连接池"""
        logger = get_logger('DatabasePool')
        logger.info(f"开始关闭所有MySQL连接池，共 {len(cls._mysql_instances)} 个")
        
        for pool_key, instance in cls._mysql_instances.items():
            try:
                if instance.pool:
                    logger.info(f"关闭MySQL连接池: {pool_key}")
                    instance.pool.close()
                    await instance.pool.wait_closed()
                    logger.info(f"MySQL连接池已关闭: {pool_key}")
            except Exception as e:
                logger.error(f"关闭MySQL连接池 {pool_key} 时发生错误: {e}")
        
        cls._mysql_instances.clear()
        logger.info("所有MySQL连接池已关闭")
    
    @classmethod
    async def close_all_mongo_clients(cls):
        """关闭所有 MongoDB 客户端"""
        logger = get_logger('DatabasePool')
        logger.info(f"开始关闭所有 MongoDB 客户端，共 {len(cls._mongo_instances)} 个")
        
        for pool_key, instance in cls._mongo_instances.items():
            try:
                if instance.client:
                    logger.info(f"关闭 MongoDB 客户端: {pool_key}")
                    instance.client.close()
                    logger.info(f"MongoDB 客户端已关闭: {pool_key}")
            except Exception as e:
                logger.error(f"关闭 MongoDB 客户端 {pool_key} 时发生错误: {e}")
        
        cls._mongo_instances.clear()
        logger.info("所有 MongoDB 客户端已关闭")
    
    @classmethod
    def get_mysql_pool_stats(cls) -> Dict[str, Any]:
        """获取所有MySQL连接池的统计信息"""
        stats = {
            'total_pools': len(cls._mysql_instances),
            'pools': {}
        }
        
        for pool_key, instance in cls._mysql_instances.items():
            if instance.pool:
                stats['pools'][pool_key] = {
                    'type': instance._pool_type,
                    'size': getattr(instance.pool, 'size', 'unknown'),
                    'minsize': instance._config.get('minsize', 'unknown'),
                    'maxsize': instance._config.get('maxsize', 'unknown'),
                    'host': instance._config.get('host', 'unknown'),
                    'db': instance._config.get('db', 'unknown')
                }
        
        return stats
    
    @classmethod
    def get_mongo_pool_stats(cls) -> Dict[str, Any]:
        """获取所有MongoDB连接池的统计信息"""
        stats = {
            'total_pools': len(cls._mongo_instances),
            'pools': {}
        }
        
        for pool_key, instance in cls._mongo_instances.items():
            if instance.client:
                stats['pools'][pool_key] = {
                    'uri': instance._config.get('mongo_uri', 'unknown'),
                    'db_name': instance._config.get('db_name', 'unknown'),
                    'min_pool_size': instance._config.get('min_pool_size', 'unknown'),
                    'max_pool_size': instance._config.get('max_pool_size', 'unknown')
                }
        
        return stats


# 便捷函数 - 保持向后兼容性
async def get_mysql_pool(
    pool_type: str = 'asyncmy',
    host: str = 'localhost',
    port: int = 3306,
    user: str = 'root',
    password: str = '',
    db: str = 'crawlo',
    minsize: int = 3,
    maxsize: int = 10,
    **kwargs
):
    """
    获取 MySQL 连接池实例（便捷函数）
    
    Args:
        pool_type: 连接池类型 ('asyncmy' 或 'aiomysql')
        host: 数据库主机
        port: 数据库端口
        user: 数据库用户名
        password: 数据库密码
        db: 数据库名
        minsize: 最小连接数
        maxsize: 最大连接数
        **kwargs: 其他连接参数
        
    Returns:
        连接池实例
    """
    if not MYSQL_AVAILABLE:
        raise RuntimeError("MySQL 支持不可用，请安装 aiomysql 或 asyncmy")
    
    return await DatabaseConnectionPoolManager.get_mysql_pool(
        pool_type=pool_type,
        host=host,
        port=port,
        user=user,
        password=password,
        db=db,
        minsize=minsize,
        maxsize=maxsize,
        **kwargs
    )


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
    
    return await DatabaseConnectionPoolManager.get_mongo_client(
        mongo_uri=mongo_uri,
        db_name=db_name,
        max_pool_size=max_pool_size,
        min_pool_size=min_pool_size,
        connect_timeout_ms=connect_timeout_ms,
        socket_timeout_ms=socket_timeout_ms,
        **kwargs
    )


async def close_all_database_pools():
    """关闭所有数据库连接池"""
    logger = get_logger('DatabasePool')
    logger.info("开始关闭所有数据库连接池")
    
    # 关闭所有 MySQL 连接池
    await DatabaseConnectionPoolManager.close_all_mysql_pools()
    
    # 关闭所有 MongoDB 客户端
    await DatabaseConnectionPoolManager.close_all_mongo_clients()
    
    logger.info("所有数据库连接池已关闭")


def get_database_pool_stats() -> Dict[str, Any]:
    """获取所有数据库连接池的统计信息"""
    stats = {
        'mysql': DatabaseConnectionPoolManager.get_mysql_pool_stats(),
        'mongo': DatabaseConnectionPoolManager.get_mongo_pool_stats()
    }
    return stats