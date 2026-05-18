#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Redis 连接池管理
================
提供 Redis 连接池、连接池管理器和全局连接池管理功能
"""

import asyncio
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional, List, TYPE_CHECKING

import redis.asyncio as aioredis

# 尝试导入Redis集群支持
try:
    from redis.asyncio.cluster import RedisCluster
    from redis.asyncio.cluster import ClusterNode
    REDIS_CLUSTER_AVAILABLE = True
except ImportError:
    RedisCluster = None
    ClusterNode = None
    REDIS_CLUSTER_AVAILABLE = False

if TYPE_CHECKING:
    pass

from crawlo.utils.error_handler import ErrorHandler, ErrorContext


class RedisConnectionPool:
    """Redis连接池管理器"""

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

    # Redis集群不支持的配置参数
    CLUSTER_UNSUPPORTED_CONFIG = {
        'retry_on_timeout',
        'health_check_interval',
        'socket_keepalive'
    }

    def __init__(self, redis_url: str, is_cluster: bool = False, cluster_nodes: Optional[List[str]] = None, **kwargs):
        self.redis_url = redis_url
        self.is_cluster = is_cluster
        self.cluster_nodes = cluster_nodes
        self.config = {**self.DEFAULT_CONFIG, **kwargs}

        # 延迟初始化logger和error_handler
        self._logger = None
        self._error_handler: Optional["ErrorHandler"] = None

        # 连接池实例
        self._connection_pool: Optional[aioredis.ConnectionPool] = None
        self._redis_client = None
        self._connection_tested = False

        # 初始化连接池
        self._initialize_pool()

    @property
    def logger(self):
        """延迟初始化logger"""
        if self._logger is None:
            from crawlo.logging import get_logger
            self._logger = get_logger(self.__class__.__name__)
        return self._logger

    @property
    def error_handler(self):
        """延迟初始化error_handler"""
        if self._error_handler is None:
            # ErrorHandler 已在顶部导入
            self._error_handler = ErrorHandler(self.__class__.__name__)
        return self._error_handler

    def _is_cluster_url(self) -> bool:
        """判断是否为集群URL格式"""
        if self.cluster_nodes:
            return True
        if ',' in self.redis_url:
            return True
        if 'redis-cluster://' in self.redis_url or 'rediss-cluster://' in self.redis_url:
            return True
        return False

    def _parse_cluster_nodes(self) -> List[Dict[str, Any]]:
        """解析集群节点"""
        nodes = []
        if self.cluster_nodes:
            node_list = self.cluster_nodes
        else:
            url_part = self.redis_url.replace('redis://', '').replace('rediss://', '')
            node_list = url_part.split(',')

        for node in node_list:
            if ':' in node:
                host, port = node.rsplit(':', 1)
                try:
                    nodes.append({
                        'host': str(host.strip()),
                        'port': int(port.strip())
                    })
                except ValueError:
                    self.logger.warning(f"无效的节点格式: {node}")
            else:
                nodes.append({
                    'host': str(node.strip()),
                    'port': 6379
                })
        return nodes

    def _get_cluster_config(self) -> Dict[str, Any]:
        """获取适用于Redis集群的配置"""
        cluster_config = self.config.copy()
        for unsupported_key in self.CLUSTER_UNSUPPORTED_CONFIG:
            cluster_config.pop(unsupported_key, None)
        return cluster_config

    def _initialize_pool(self):
        """初始化连接池"""
        try:
            should_use_cluster = self.is_cluster or self._is_cluster_url()

            if should_use_cluster and REDIS_CLUSTER_AVAILABLE and RedisCluster is not None and ClusterNode is not None:
                nodes = self._parse_cluster_nodes()
                cluster_config = self._get_cluster_config()

                if nodes:
                    if len(nodes) == 1:
                        self._redis_client = RedisCluster(
                            host=str(nodes[0]['host']),
                            port=int(nodes[0]['port']),
                            **cluster_config
                        )
                    else:
                        cluster_node_objects = [ClusterNode(str(node['host']), int(node['port'])) for node in nodes]
                        self._redis_client = RedisCluster(
                            startup_nodes=cluster_node_objects,
                            **cluster_config
                        )
                    self.logger.info(f"Redis集群连接池初始化成功: {len(nodes)} 个节点")
                else:
                    self._connection_pool = aioredis.ConnectionPool.from_url(
                        self.redis_url,
                        **self.config
                    )
                    self._redis_client = aioredis.Redis(
                        connection_pool=self._connection_pool
                    )
                    self.logger.warning("无法解析集群节点，回退到单实例模式")
            else:
                try:
                    self._connection_pool = aioredis.ConnectionPool.from_url(
                        self.redis_url,
                        **self.config
                    )
                except Exception as e:
                    if 'AUTH' in str(e).upper() or 'PASSWORD' in str(e).upper() or 'INVALID PASSWORD' in str(e).upper():
                        self.logger.warning(f"Redis认证失败，可能密码不正确: {e}")
                        self.logger.warning(f"请检查Redis密码配置: {self.redis_url}")
                        raise
                    else:
                        raise

                self._redis_client = aioredis.Redis(
                    connection_pool=self._connection_pool
                )

            if should_use_cluster and REDIS_CLUSTER_AVAILABLE:
                self.logger.debug(f"Redis集群连接池初始化成功: {self.redis_url}")
            else:
                self.logger.info(f"Redis connection pool initialized successfully: {self.redis_url}")
                self.logger.debug(f"Connection pool configuration: {self.config}")

        except Exception as e:
            # ErrorContext 已在顶部导入
            error_context = ErrorContext(context="Redis连接池初始化失败")
            self.error_handler.handle_error(
                e,
                context=error_context,
                raise_error=True
            )

    async def _test_connection(self):
        """测试Redis连接"""
        if self._redis_client and not self._connection_tested:
            try:
                await self._redis_client.ping()
                self._connection_tested = True
                if REDIS_CLUSTER_AVAILABLE and RedisCluster is not None and isinstance(self._redis_client, RedisCluster):
                    self.logger.debug(f"Redis集群连接测试成功: {self.redis_url}")
                else:
                    self.logger.debug(f"Redis连接测试成功: {self.redis_url}")
            except Exception as e:
                self.logger.error(f"Redis连接测试失败: {self.redis_url} - {e}")
                raise

    async def get_connection(self):
        """获取Redis连接实例"""
        if not self._redis_client:
            self._initialize_pool()

        await self._test_connection()

        return self._redis_client

    async def ping(self) -> bool:
        """检查Redis连接是否正常"""
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

            self.logger.debug("Redis连接池已关闭")
        except Exception as e:
            # ErrorContext 已在顶部导入
            error_context = ErrorContext(context="关闭Redis连接池失败")
            self.error_handler.handle_error(
                e,
                context=error_context,
                raise_error=False
            )

    def get_stats(self) -> Dict[str, Any]:
        """获取连接池统计信息"""
        if self._connection_pool and hasattr(self._connection_pool, 'max_connections'):
            return {
                'max_connections': self._connection_pool.max_connections,
                'available_connections': len(self._connection_pool._available_connections) if hasattr(self._connection_pool, '_available_connections') else 0,
                'in_use_connections': len(self._connection_pool._in_use_connections) if hasattr(self._connection_pool, '_in_use_connections') else 0,
            }
        return {}

    @asynccontextmanager
    async def connection_context(self):
        """连接上下文管理器"""
        connection = await self.get_connection()
        yield connection


def get_redis_pool(redis_url: str, is_cluster: bool = False, cluster_nodes: Optional[List[str]] = None, shared: bool = True, **kwargs) -> RedisConnectionPool:
    """获取Redis连接池实例（存储于 ApplicationContext）"""
    if shared:
        from crawlo.core.application import get_global_context
        pools = get_global_context().connection_pools
        pool_key = f"{redis_url}:{is_cluster}:{cluster_nodes}" if cluster_nodes else f"{redis_url}:{is_cluster}"
        if pool_key not in pools:
            pools[pool_key] = RedisConnectionPool(redis_url, is_cluster=is_cluster, cluster_nodes=cluster_nodes, **kwargs)
        return pools[pool_key]
    else:
        import uuid
        return RedisConnectionPool(redis_url, is_cluster=is_cluster, cluster_nodes=cluster_nodes, **kwargs)


async def close_all_pools():
    """关闭所有共享连接池"""
    from crawlo.core.application import get_global_context
    pools = get_global_context().connection_pools
    for pool in list(pools.values()):
        await pool.close()
    pools.clear()


class CrawloRedisManager:
    """
    Crawlo 专用 Redis 管理器
    提供连接生命周期隔离，确保多爬虫场景下的连接安全
    """

    def __init__(self, crawler_id: str):
        """
        初始化 Redis 管理器

        Args:
            crawler_id: 爬虫实例ID，用于连接隔离
        """
        self.crawler_id = crawler_id
        self._connection_pools: Dict[str, RedisConnectionPool] = {}
        self._is_closed = False

    def get_pool(self, redis_url: str, **kwargs) -> RedisConnectionPool:
        """获取专属连接池（独立模式）"""
        if self._is_closed:
            raise RuntimeError("Redis管理器已关闭")

        pool = get_redis_pool(redis_url, shared=False, **kwargs)
        self._connection_pools[redis_url] = pool
        return pool

    async def close_all(self):
        """关闭所有连接池"""
        if self._is_closed:
            return

        for pool in self._connection_pools.values():
            try:
                await pool.close()
            except Exception as e:
                print(f"关闭连接池时出错: {e}")

        self._connection_pools.clear()
        self._is_closed = True

    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口，确保资源清理"""
        await self.close_all()


def get_isolated_redis_pool(crawler_id: str, redis_url: str, **kwargs) -> RedisConnectionPool:
    """
    获取隔离的 Redis 连接池（推荐用于多爬虫场景）

    Args:
        crawler_id: 爬虫实例ID
        redis_url: Redis URL
        **kwargs: 连接池配置参数

    Returns:
        Redis连接池实例
    """
    return get_redis_pool(redis_url, shared=False, **kwargs)


class GlobalRedisManager:
    """全局 Redis 管理器（单例）"""

    def __init__(self):
        self._default_pool: Optional[RedisConnectionPool] = None
        self._is_initialized = False

    async def initialize(self, redis_url: str, **kwargs):
        """初始化默认连接池"""
        if self._is_initialized:
            return

        self._default_pool = get_redis_pool(redis_url, shared=True, **kwargs)
        self._is_initialized = True

    async def get_pool(self) -> Optional[RedisConnectionPool]:
        """获取默认连接池"""
        if not self._is_initialized:
            raise RuntimeError("Redis管理器未初始化，请先调用 initialize()")
        return self._default_pool

    async def ping(self) -> bool:
        """检查 Redis 连接是否正常"""
        if self._default_pool:
            return await self._default_pool.ping()
        return False

    async def close(self):
        """关闭默认连接池"""
        if self._default_pool:
            await self._default_pool.close()
            self._default_pool = None
            self._is_initialized = False


def get_redis_manager() -> GlobalRedisManager:
    """获取全局 Redis 管理器单例（存储于 ApplicationContext）"""
    from crawlo.core.application import get_global_context
    ctx = get_global_context()
    if ctx.redis_manager is None:
        ctx.redis_manager = GlobalRedisManager()
    return ctx.redis_manager
