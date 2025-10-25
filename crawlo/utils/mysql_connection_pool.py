#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
MySQL 连接池管理器
================

提供单例模式的MySQL连接池，确保多个爬虫共享同一个连接池，
避免重复创建连接池导致的资源浪费。

特点：
1. 单例模式 - 全局唯一的连接池实例
2. 线程安全 - 使用异步锁保护初始化过程
3. 配置隔离 - 支持不同的数据库配置创建不同的连接池
4. 自动清理 - 支持资源清理和重置
"""

import asyncio
import aiomysql
from asyncmy import create_pool as asyncmy_create_pool
from typing import Dict, Optional, Any
from crawlo.logging import get_logger


class MySQLConnectionPoolManager:
    """MySQL 连接池管理器（单例模式）"""
    
    _instances: Dict[str, 'MySQLConnectionPoolManager'] = {}
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
        self._pool_type: str = 'asyncmy'  # 默认使用 asyncmy
        self.logger = get_logger(f'MySQLPool.{pool_key}')
    
    @classmethod
    async def get_pool(
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
        获取连接池实例（单例模式）
        
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
        # 生成连接池唯一标识
        pool_key = f"{pool_type}:{host}:{port}:{db}"
        
        async with cls._lock:
            if pool_key not in cls._instances:
                instance = cls(pool_key)
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
                cls._instances[pool_key] = instance
                instance.logger.info(
                    f"创建新的连接池管理器: {pool_key} "
                    f"(type={pool_type}, minsize={minsize}, maxsize={maxsize})"
                )
            
            instance = cls._instances[pool_key]
            await instance._ensure_pool()
            return instance.pool
    
    async def _ensure_pool(self):
        """确保连接池已初始化（线程安全）"""
        if self._pool_initialized:
            # 检查连接池是否仍然有效
            if self.pool and hasattr(self.pool, 'closed') and not self.pool.closed:
                return
            else:
                self.logger.warning("连接池已初始化但无效，重新初始化")
        
        async with self._pool_lock:
            if not self._pool_initialized:
                try:
                    if self._pool_type == 'asyncmy':
                        self.pool = await self._create_asyncmy_pool()
                    elif self._pool_type == 'aiomysql':
                        self.pool = await self._create_aiomysql_pool()
                    else:
                        raise ValueError(f"不支持的连接池类型: {self._pool_type}")
                    
                    self._pool_initialized = True
                    self.logger.info(
                        f"连接池初始化成功: {self.pool_key} "
                        f"(minsize={self._config['minsize']}, maxsize={self._config['maxsize']})"
                    )
                except Exception as e:
                    self.logger.error(f"连接池初始化失败: {e}")
                    self._pool_initialized = False
                    self.pool = None
                    raise
    
    async def _create_asyncmy_pool(self):
        """创建 asyncmy 连接池"""
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
        """关闭所有连接池"""
        logger = get_logger('MySQLPool')
        logger.info(f"开始关闭所有连接池，共 {len(cls._instances)} 个")
        
        for pool_key, instance in cls._instances.items():
            try:
                if instance.pool:
                    logger.info(f"关闭连接池: {pool_key}")
                    instance.pool.close()
                    await instance.pool.wait_closed()
                    logger.info(f"连接池已关闭: {pool_key}")
            except Exception as e:
                logger.error(f"关闭连接池 {pool_key} 时发生错误: {e}")
        
        cls._instances.clear()
        logger.info("所有连接池已关闭")
    
    @classmethod
    def get_pool_stats(cls) -> Dict[str, Any]:
        """获取所有连接池的统计信息"""
        stats = {
            'total_pools': len(cls._instances),
            'pools': {}
        }
        
        for pool_key, instance in cls._instances.items():
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
