#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
MySQL连接池管理器
====================

提供单例模式的MySQL连接池管理，支持aiomysql和asyncmy两种驱动，
确保多个爬虫共享同一个连接池，避免重复创建连接池导致的资源浪费。

特点：
1. 单例模式 - 全局唯一的连接池实例
2. 线程安全 - 使用异步锁保护初始化过程
3. 驱动隔离 - 分别管理aiomysql和asyncmy连接池
4. 自动清理 - 支持资源清理和重置
"""

import asyncio
from typing import Dict, Optional, Any
from crawlo.logging import get_logger


def is_pool_active(pool) -> bool:
    """统一检查连接池是否活跃
    
    Args:
        pool: 数据库连接池对象
        
    Returns:
        bool: 连接池是否活跃
    """
    if not pool:
        return False
    # 优先检查 asyncmy 的 _closed 属性
    if hasattr(pool, '_closed'):
        return not pool._closed
    # 其次检查 aiomysql 的 closed 属性
    elif hasattr(pool, 'closed'):
        return not pool.closed
    return True


# MySQL 相关导入
try:
    import aiomysql
    from asyncmy import create_pool as asyncmy_create_pool
    MYSQL_AVAILABLE = True
except ImportError:
    aiomysql = None
    asyncmy_create_pool = None
    MYSQL_AVAILABLE = False


class AiomysqlConnectionPoolManager:
    """aiomysql连接池管理器（单例模式）"""
    
    _instances: Dict[str, 'AiomysqlConnectionPoolManager'] = {}
    _lock = asyncio.Lock()
    
    def __init__(self, pool_key: str):
        """
        初始化连接池管理器
        
        Args:
            pool_key: 连接池唯一标识
        """
        self.pool_key = pool_key
        self.pool = None
        self._pool_lock = asyncio.Lock()
        self._pool_initialized = False
        self._config: Dict[str, Any] = {}
        self.logger = get_logger(f'AiomysqlPool.{pool_key}')
    
    @classmethod
    async def get_pool(
        cls, 
        host: str = 'localhost',
        port: int = 3306,
        user: str = 'root',
        password: str = '',
        db: str = 'crawlo',
        minsize: int = 2,
        maxsize: int = 5,
        **kwargs
    ):
        """
        获取aiomysql连接池实例（单例模式）
        
        Args:
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
        # 生成连接池唯一标识
        pool_key = f"aiomysql:{host}:{port}:{db}"
        
        async with cls._lock:
            if pool_key not in cls._instances:
                instance = cls(pool_key)
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
                cls._instances[pool_key] = instance
                instance.logger.debug(
                    f"创建新的aiomysql连接池管理器: {pool_key} "
                    f"(minsize={minsize}, maxsize={maxsize})"
                )
            
            instance = cls._instances[pool_key]
            await instance._ensure_pool()
            return instance.pool
    
    async def _ensure_pool(self):
        """确保连接池已初始化（线程安全）"""
        if self._pool_initialized:
            # 检查连接池是否仍然有效 - 使用统一函数
            if is_pool_active(self.pool):
                return
            else:
                self.logger.warning("aiomysql连接池已初始化但无效，重新初始化")
        
        async with self._pool_lock:
            if not self._pool_initialized:
                try:
                    self.pool = await self._create_pool()
                    self._pool_initialized = True
                    self.logger.info(
                        f"aiomysql连接池初始化成功: {self.pool_key} "
                        f"(minsize={self._config['minsize']}, maxsize={self._config['maxsize']})"
                    )
                except Exception as e:
                    self.logger.error(f"aiomysql连接池初始化失败: {e}")
                    self._pool_initialized = False
                    self.pool = None
                    raise
    
    async def _create_pool(self):
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
    async def close_all_pools(cls):
        """关闭所有aiomysql连接池"""
        logger = get_logger('AiomysqlPool')
        logger.debug(f"开始关闭所有aiomysql连接池，共 {len(cls._instances)} 个")
        
        for pool_key, instance in cls._instances.items():
            try:
                if instance.pool:
                    logger.debug(f"关闭aiomysql连接池: {pool_key}")
                    instance.pool.close()
                    await instance.pool.wait_closed()
                    logger.debug(f"aiomysql连接池已关闭: {pool_key}")
            except Exception as e:
                logger.error(f"关闭aiomysql连接池 {pool_key} 时发生错误: {e}")
        
        cls._instances.clear()
        logger.debug("所有aiomysql连接池已关闭")
    
    @classmethod
    def get_pool_stats(cls) -> Dict[str, Any]:
        """获取所有aiomysql连接池的统计信息"""
        stats = {
            'total_pools': len(cls._instances),
            'pools': {}
        }
        
        for pool_key, instance in cls._instances.items():
            if instance.pool:
                stats['pools'][pool_key] = {
                    'driver': 'aiomysql',
                    'size': getattr(instance.pool, 'size', 'unknown'),
                    'minsize': instance._config.get('minsize', 'unknown'),
                    'maxsize': instance._config.get('maxsize', 'unknown'),
                    'host': instance._config.get('host', 'unknown'),
                    'db': instance._config.get('db', 'unknown')
                }
        
        return stats


class AsyncmyConnectionPoolManager:
    """asyncmy连接池管理器（单例模式）"""
    
    _instances: Dict[str, 'AsyncmyConnectionPoolManager'] = {}
    _lock = asyncio.Lock()
    
    def __init__(self, pool_key: str):
        """
        初始化连接池管理器
        
        Args:
            pool_key: 连接池唯一标识
        """
        self.pool_key = pool_key
        self.pool = None
        self._pool_lock = asyncio.Lock()
        self._pool_initialized = False
        self._config: Dict[str, Any] = {}
        self.logger = get_logger(f'AsyncmyPool.{pool_key}')
    
    @classmethod
    async def get_pool(
        cls, 
        host: str = 'localhost',
        port: int = 3306,
        user: str = 'root',
        password: str = '',
        db: str = 'crawlo',
        minsize: int = 3,
        maxsize: int = 10,
        echo: bool = False,
        **kwargs
    ):
        """
        获取asyncmy连接池实例（单例模式）
        
        Args:
            host: 数据库主机
            port: 数据库端口
            user: 数据库用户名
            password: 数据库密码
            db: 数据库名
            minsize: 最小连接数
            maxsize: 最大连接数
            echo: 是否打印SQL日志
            **kwargs: 其他连接参数
            
        Returns:
            连接池实例
        """
        # 生成连接池唯一标识
        pool_key = f"asyncmy:{host}:{port}:{db}"
        
        async with cls._lock:
            if pool_key not in cls._instances:
                instance = cls(pool_key)
                instance._config = {
                    'host': host,
                    'port': port,
                    'user': user,
                    'password': password,
                    'db': db,
                    'minsize': minsize,
                    'maxsize': maxsize,
                    'echo': echo,
                    **kwargs
                }
                cls._instances[pool_key] = instance
                instance.logger.debug(
                    f"创建新的asyncmy连接池管理器: {pool_key} "
                    f"(minsize={minsize}, maxsize={maxsize}, echo={echo})"
                )
            
            instance = cls._instances[pool_key]
            await instance._ensure_pool()
            return instance.pool
    
    async def _ensure_pool(self):
        """确保连接池已初始化（线程安全）"""
        if self._pool_initialized:
            # 检查连接池是否仍然有效 - 使用统一函数
            if is_pool_active(self.pool):
                return
            else:
                self.logger.warning("asyncmy连接池已初始化但无效，重新初始化")
        
        async with self._pool_lock:
            if not self._pool_initialized:
                try:
                    self.pool = await self._create_pool()
                    self._pool_initialized = True
                    self.logger.info(
                        f"asyncmy连接池初始化成功: {self.pool_key} "
                        f"(minsize={self._config['minsize']}, maxsize={self._config['maxsize']})"
                    )
                except Exception as e:
                    self.logger.error(f"asyncmy连接池初始化失败: {e}")
                    self._pool_initialized = False
                    self.pool = None
                    raise
    
    async def _create_pool(self):
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
    
    @classmethod
    async def close_all_pools(cls):
        """关闭所有asyncmy连接池"""
        logger = get_logger('AsyncmyPool')
        logger.debug(f"开始关闭所有asyncmy连接池，共 {len(cls._instances)} 个")
        
        for pool_key, instance in cls._instances.items():
            try:
                if instance.pool:
                    logger.debug(f"关闭asyncmy连接池: {pool_key}")
                    instance.pool.close()
                    await instance.pool.wait_closed()
                    logger.debug(f"asyncmy连接池已关闭: {pool_key}")
            except Exception as e:
                logger.error(f"关闭asyncmy连接池 {pool_key} 时发生错误: {e}")
        
        cls._instances.clear()
        logger.debug("所有asyncmy连接池已关闭")
    
    @classmethod
    def get_pool_stats(cls) -> Dict[str, Any]:
        """获取所有asyncmy连接池的统计信息"""
        stats = {
            'total_pools': len(cls._instances),
            'pools': {}
        }
        
        for pool_key, instance in cls._instances.items():
            if instance.pool:
                stats['pools'][pool_key] = {
                    'driver': 'asyncmy',
                    'size': getattr(instance.pool, 'size', 'unknown'),
                    'minsize': instance._config.get('minsize', 'unknown'),
                    'maxsize': instance._config.get('maxsize', 'unknown'),
                    'host': instance._config.get('host', 'unknown'),
                    'db': instance._config.get('db', 'unknown')
                }
        
        return stats


# 便捷函数 - 保持向后兼容性
async def get_aiomysql_pool(
    host: str = 'localhost',
    port: int = 3306,
    user: str = 'root',
    password: str = '',
    db: str = 'crawlo',
    minsize: int = 2,
    maxsize: int = 5,
    **kwargs
):
    """
    获取 aiomysql 连接池实例（便捷函数）
    
    Args:
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
    if aiomysql is None:
        raise RuntimeError("aiomysql 不可用，请安装 aiomysql")
    
    return await AiomysqlConnectionPoolManager.get_pool(
        host=host,
        port=port,
        user=user,
        password=password,
        db=db,
        minsize=minsize,
        maxsize=maxsize,
        **kwargs
    )


async def get_asyncmy_pool(
    host: str = 'localhost',
    port: int = 3306,
    user: str = 'root',
    password: str = '',
    db: str = 'crawlo',
    minsize: int = 3,
    maxsize: int = 10,
    echo: bool = False,
    **kwargs
):
    """
    获取 asyncmy 连接池实例（便捷函数）
    
    Args:
        host: 数据库主机
        port: 数据库端口
        user: 数据库用户名
        password: 数据库密码
        db: 数据库名
        minsize: 最小连接数
        maxsize: 最大连接数
        echo: 是否打印SQL日志
        **kwargs: 其他连接参数
        
    Returns:
        连接池实例
    """
    if asyncmy_create_pool is None:
        raise RuntimeError("asyncmy 不可用，请安装 asyncmy")
    
    return await AsyncmyConnectionPoolManager.get_pool(
        host=host,
        port=port,
        user=user,
        password=password,
        db=db,
        minsize=minsize,
        maxsize=maxsize,
        echo=echo,
        **kwargs
    )


async def close_all_mysql_pools():
    """关闭所有MySQL连接池"""
    logger = get_logger('MySQLPools')
    logger.debug("开始关闭所有MySQL连接池")
    
    # 关闭所有 aiomysql 连接池
    await AiomysqlConnectionPoolManager.close_all_pools()
    
    # 关闭所有 asyncmy 连接池
    await AsyncmyConnectionPoolManager.close_all_pools()
    
    logger.debug("所有MySQL连接池已关闭")


def get_mysql_pool_stats() -> Dict[str, Any]:
    """获取所有MySQL连接池的统计信息"""
    stats = {
        'aiomysql': AiomysqlConnectionPoolManager.get_pool_stats(),
        'asyncmy': AsyncmyConnectionPoolManager.get_pool_stats()
    }
    return stats