#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
MySQL 连接池管理器
====================

提供单例模式的 MySQL 连接池管理，基于 asyncmy 异步驱动，
确保多个爬虫共享同一个连接池，避免重复创建连接池导致的资源浪费。

特点：
1. 单例模式 - 全局唯一的连接池实例
2. 线程安全 - 使用异步锁保护初始化过程
3. 高性能 - 基于 Cython 加速的 asyncmy 驱动
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
    # 检查 asyncmy 的 _closed 属性
    if hasattr(pool, '_closed'):
        return not pool._closed
    return True


# MySQL 相关导入
try:
    from asyncmy import create_pool as asyncmy_create_pool
    MYSQL_AVAILABLE = True
except ImportError:
    asyncmy_create_pool = None
    MYSQL_AVAILABLE = False


class MySQLConnectionPoolManager:
    """MySQL 连接池管理器（支持单例模式和独立模式）"""
    
    _instances: Dict[str, 'MySQLConnectionPoolManager'] = {}
    _lock = asyncio.Lock()
    
    def __init__(self, pool_key: str, shared: bool = True):
        """
        初始化连接池管理器
        
        Args:
            pool_key: 连接池唯一标识
            shared: 是否使用共享模式（单例），True 为单例模式，False 为独立模式
        """
        self.pool_key = pool_key
        self.shared = shared  # 是否为共享模式
        self.pool = None
        self._pool_lock = asyncio.Lock()
        self._pool_initialized = False
        self._config: Dict[str, Any] = {}
        self.logger = get_logger(f'MySQLPool.{pool_key}')
    
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
        shared: bool = True,
        **kwargs
    ):
        """
        获取 MySQL 连接池实例
        
        Args:
            host: 数据库主机
            port: 数据库端口
            user: 数据库用户名
            password: 数据库密码
            db: 数据库名
            minsize: 最小连接数
            maxsize: 最大连接数
            echo: 是否打印 SQL 日志
            shared: 是否使用共享模式（True=单例模式，False=独立模式）
            **kwargs: 其他连接参数
            
        Returns:
            连接池实例
        """
        # 生成连接池唯一标识
        if shared:
            pool_key = f"asyncmy:{host}:{port}:{db}"
        else:
            import uuid
            pool_key = f"asyncmy:{host}:{port}:{db}:{uuid.uuid4().hex[:8]}"
        
        if shared:
            async with cls._lock:
                if pool_key not in cls._instances:
                    instance = cls(pool_key, shared=True)
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
                        f"创建新的 MySQL 连接池管理器：{pool_key} "
                        f"(minsize={minsize}, maxsize={maxsize}, echo={echo})"
                    )
                
                instance = cls._instances[pool_key]
                await instance._ensure_pool()
                return instance.pool
        else:
            instance = cls(pool_key, shared=False)
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
            instance.logger.debug(
                f"创建独立的 MySQL 连接池：{pool_key} "
                f"(minsize={minsize}, maxsize={maxsize})"
            )
            await instance._ensure_pool()
            return instance.pool, instance
    
    async def _ensure_pool(self):
        """确保连接池已初始化（线程安全）"""
        if self._pool_initialized:
            if is_pool_active(self.pool):
                return
            else:
                self.logger.warning("MySQL 连接池已初始化但无效，重新初始化")
        
        async with self._pool_lock:
            if not self._pool_initialized:
                try:
                    self.pool = await self._create_pool()
                    self._pool_initialized = True
                    self.logger.debug(
                        f"MySQL 连接池初始化成功：{self.pool_key} "
                        f"(minsize={self._config['minsize']}, maxsize={self._config['maxsize']})"
                    )
                except Exception as e:
                    self.logger.error(f"MySQL 连接池初始化失败：{e}")
                    self._pool_initialized = False
                    self.pool = None
                    raise
    
    async def _create_pool(self):
        """创建 MySQL 连接池"""
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
    
    async def close_pool(self):
        """关闭当前实例的连接池"""
        if self.pool:
            try:
                self.logger.debug(f"关闭 MySQL 连接池：{self.pool_key}")
                self.pool.close()
                await self.pool.wait_closed()
                self.logger.debug(f"MySQL 连接池已关闭：{self.pool_key}")
            except Exception as e:
                self.logger.error(f"关闭 MySQL 连接池 {self.pool_key} 时发生错误：{e}")
            finally:
                self.pool = None
                self._pool_initialized = False
    
    @classmethod
    async def close_all_pools(cls):
        """关闭所有共享 MySQL 连接池"""
        logger = get_logger('MySQLPool')
        logger.debug(f"开始关闭所有 MySQL 连接池，共 {len(cls._instances)} 个")
        
        for pool_key, instance in cls._instances.items():
            try:
                if instance.pool:
                    logger.debug(f"关闭 MySQL 连接池：{pool_key}")
                    instance.pool.close()
                    await instance.pool.wait_closed()
                    logger.debug(f"MySQL 连接池已关闭：{pool_key}")
            except Exception as e:
                logger.error(f"关闭 MySQL 连接池 {pool_key} 时发生错误：{e}")
        
        cls._instances.clear()
        logger.debug("所有 MySQL 连接池已关闭")
    
    @classmethod
    def get_pool_stats(cls) -> Dict[str, Any]:
        """获取所有 MySQL 连接池的统计信息"""
        stats = {
            'total_pools': len(cls._instances),
            'pools': {}
        }
        
        for pool_key, instance in cls._instances.items():
            if instance.pool:
                pool = instance.pool
                size = getattr(pool, 'size', 0)
                freesize = getattr(pool, 'freesize', 0)
                maxsize = getattr(pool, 'maxsize', 0)
                minsize = getattr(pool, 'minsize', 0)
                
                stats['pools'][pool_key] = {
                    'driver': 'asyncmy',
                    'size': size,
                    'freesize': freesize,
                    'used': size - freesize,
                    'minsize': minsize,
                    'maxsize': maxsize,
                    'usage_percent': (size - freesize) / maxsize * 100 if maxsize > 0 else 0,
                    'host': instance._config.get('host', 'unknown'),
                    'db': instance._config.get('db', 'unknown')
                }
        
        return stats


# 便捷函数
async def get_mysql_pool(
    host: str = 'localhost',
    port: int = 3306,
    user: str = 'root',
    password: str = '',
    db: str = 'crawlo',
    minsize: int = 3,
    maxsize: int = 10,
    echo: bool = False,
    shared: bool = True,
    **kwargs
):
    """
    获取 MySQL 连接池实例（便捷函数）
    
    Args:
        host: 数据库主机
        port: 数据库端口
        user: 数据库用户名
        password: 数据库密码
        db: 数据库名
        minsize: 最小连接数
        maxsize: 最大连接数
        echo: 是否打印 SQL 日志
        shared: 是否使用共享模式
        **kwargs: 其他连接参数
        
    Returns:
        连接池实例
    """
    if asyncmy_create_pool is None:
        raise RuntimeError("asyncmy 不可用，请安装 asyncmy")
    
    result = await MySQLConnectionPoolManager.get_pool(
        host=host,
        port=port,
        user=user,
        password=password,
        db=db,
        minsize=minsize,
        maxsize=maxsize,
        echo=echo,
        shared=shared,
        **kwargs
    )
    
    if shared:
        return result
    else:
        return result[0]


async def close_all_mysql_pools():
    """关闭所有共享 MySQL 连接池"""
    logger = get_logger('MySQLPools')
    logger.debug("开始关闭所有 MySQL 连接池")
    
    await MySQLConnectionPoolManager.close_all_pools()
    
    logger.debug("所有 MySQL 连接池已关闭")


def get_mysql_pool_stats() -> Dict[str, Any]:
    """获取所有 MySQL 连接池的统计信息"""
    return MySQLConnectionPoolManager.get_pool_stats()
