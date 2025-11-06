#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
Redis连接池工具
提供Redis连接池管理和配置
"""
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional, List, Union, TYPE_CHECKING
import re

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
    from crawlo.utils.error_handler import ErrorHandler


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
        self._connection_tested = False  # 标记是否已测试连接
        
        # 连接池统计信息
        self._stats = {
            'created_connections': 0,
            'active_connections': 0,
            'idle_connections': 0,
            'errors': 0
        }
        
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
            from crawlo.utils.error_handler import ErrorHandler
            self._error_handler = ErrorHandler(self.__class__.__name__)
        return self._error_handler
    
    def _is_cluster_url(self) -> bool:
        """判断是否为集群URL格式"""
        if self.cluster_nodes:
            return True
        # 检查URL是否包含多个节点（逗号分隔）
        if ',' in self.redis_url:
            return True
        # 检查URL是否为集群格式
        if 'redis-cluster://' in self.redis_url or 'rediss-cluster://' in self.redis_url:
            return True
        return False
    
    def _parse_cluster_nodes(self) -> List[Dict[str, Union[str, int]]]:
        """解析集群节点"""
        nodes = []
        if self.cluster_nodes:
            node_list = self.cluster_nodes
        else:
            # 从URL中解析节点
            # 支持格式: redis://host1:port1,host2:port2,host3:port3
            # 或: host1:port1,host2:port2,host3:port3
            url_part = self.redis_url.replace('redis://', '').replace('rediss://', '')
            node_list = url_part.split(',')
        
        for node in node_list:
            # 解析host:port格式
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
                # 默认端口
                nodes.append({
                    'host': str(node.strip()),
                    'port': 6379
                })
        
        return nodes
    
    def _get_cluster_config(self) -> Dict[str, Any]:
        """获取适用于Redis集群的配置"""
        # 移除集群不支持的配置参数
        cluster_config = self.config.copy()
        for unsupported_key in self.CLUSTER_UNSUPPORTED_CONFIG:
            cluster_config.pop(unsupported_key, None)
        return cluster_config
    
    def _initialize_pool(self):
        """初始化连接池"""
        try:
            # 智能检测是否应该使用集群模式
            should_use_cluster = self.is_cluster or self._is_cluster_url()
            
            if should_use_cluster and REDIS_CLUSTER_AVAILABLE and RedisCluster is not None and ClusterNode is not None:
                # 使用Redis集群
                nodes = self._parse_cluster_nodes()
                cluster_config = self._get_cluster_config()
                
                if nodes:
                    if len(nodes) == 1:
                        # 单节点集群
                        self._redis_client = RedisCluster(
                            host=str(nodes[0]['host']),
                            port=int(nodes[0]['port']),
                            **cluster_config
                        )
                    else:
                        # 多节点集群
                        cluster_node_objects = [ClusterNode(str(node['host']), int(node['port'])) for node in nodes]
                        self._redis_client = RedisCluster(
                            startup_nodes=cluster_node_objects,
                            **cluster_config
                        )
                    self.logger.info(f"Redis集群连接池初始化成功: {len(nodes)} 个节点")
                else:
                    # 回退到单实例模式
                    self._connection_pool = aioredis.ConnectionPool.from_url(
                        self.redis_url,
                        **self.config
                    )
                    self._redis_client = aioredis.Redis(
                        connection_pool=self._connection_pool
                    )
                    self.logger.warning("无法解析集群节点，回退到单实例模式")
            else:
                # 使用单实例Redis
                self._connection_pool = aioredis.ConnectionPool.from_url(
                    self.redis_url,
                    **self.config
                )
                
                self._redis_client = aioredis.Redis(
                    connection_pool=self._connection_pool
                )
            
            # 只在调试模式下输出详细连接池信息
            if should_use_cluster and REDIS_CLUSTER_AVAILABLE:
                self.logger.debug(f"Redis集群连接池初始化成功: {self.redis_url}")
            else:
                self.logger.info(f"Redis connection pool initialized successfully: {self.redis_url}")
                self.logger.debug(f"Connection pool configuration: {self.config}")
                
        except Exception as e:
            from crawlo.utils.error_handler import ErrorContext
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
                # 只在调试模式下输出连接测试成功信息
                if REDIS_CLUSTER_AVAILABLE and RedisCluster is not None and isinstance(self._redis_client, RedisCluster):
                    self.logger.debug(f"Redis集群连接测试成功: {self.redis_url}")
                else:
                    self.logger.debug(f"Redis连接测试成功: {self.redis_url}")
            except Exception as e:
                self.logger.error(f"Redis连接测试失败: {self.redis_url} - {e}")
                raise
    
    async def get_connection(self):
        """
        获取Redis连接实例
        
        Returns:
            Redis连接实例
        """
        if not self._redis_client:
            self._initialize_pool()
        
        # 确保连接有效
        await self._test_connection()
        
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
                
            self.logger.info("Redis连接池已关闭")
        except Exception as e:
            from crawlo.utils.error_handler import ErrorContext
            error_context = ErrorContext(context="关闭Redis连接池失败")
            self.error_handler.handle_error(
                e, 
                context=error_context, 
                raise_error=False
            )
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取连接池统计信息
        
        Returns:
            统计信息字典
        """
        if self._connection_pool and hasattr(self._connection_pool, 'max_connections'):
            pool_stats = {
                'max_connections': self._connection_pool.max_connections,
                'available_connections': len(self._connection_pool._available_connections) if hasattr(self._connection_pool, '_available_connections') else 0,
                'in_use_connections': len(self._connection_pool._in_use_connections) if hasattr(self._connection_pool, '_in_use_connections') else 0,
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
    
    def __init__(self, redis_client, batch_size: int = 100):
        self.redis_client = redis_client
        self.batch_size = batch_size
        
        # 延迟初始化logger和error_handler
        self._logger = None
        self._error_handler = None
    
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
            from crawlo.utils.error_handler import ErrorHandler
            self._error_handler = ErrorHandler(self.__class__.__name__)
        return self._error_handler
    
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
                    # 处理集群模式下的管道操作
                    if hasattr(self.redis_client, 'pipeline'):
                        pipe = self.redis_client.pipeline()
                        for operation in batch:
                            command, *args = operation
                            getattr(pipe, command)(*args)
                        
                        batch_results = await pipe.execute()
                        results.extend(batch_results)
                    else:
                        # 集群模式可能不支持跨slot的管道操作，逐个执行
                        batch_results = []
                        for operation in batch:
                            command, *args = operation
                            result = await getattr(self.redis_client, command)(*args)
                            batch_results.append(result)
                        results.extend(batch_results)
                    
                except Exception as e:
                    self.logger.error(f"执行批次失败: {e}")
                    # 继续执行下一个批次而不是中断
        
        except Exception as e:
            from crawlo.utils.error_handler import ErrorContext
            error_context = ErrorContext(context="Redis批量操作执行失败")
            self.error_handler.handle_error(
                e, 
                context=error_context, 
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
            
            # 处理集群模式
            if hasattr(self.redis_client, 'pipeline'):
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
            else:
                # 集群模式逐个执行
                count = 0
                batch_count = 0
                for key, value in items.items():
                    await self.redis_client.hset(hash_key, key, value)
                    count += 1
                    batch_count += 1
                    
                    # 每达到批次大小就暂停一下
                    if batch_count % self.batch_size == 0:
                        import asyncio
                        await asyncio.sleep(0.001)  # 避免过于频繁的请求
                        batch_count = 0
            
            self.logger.debug(f"批量设置Hash {count} 个字段")
            return count
            
        except Exception as e:
            from crawlo.utils.error_handler import ErrorContext
            error_context = ErrorContext(context="Redis批量设置Hash失败")
            self.error_handler.handle_error(
                e, 
                context=error_context, 
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
            
            # 处理集群模式
            if hasattr(self.redis_client, 'pipeline'):
                # 使用管道批量获取
                pipe = self.redis_client.pipeline()
                for field in fields:
                    pipe.hget(hash_key, field)
                
                results = await pipe.execute()
            else:
                # 集群模式逐个获取
                results = []
                for field in fields:
                    result = await self.redis_client.hget(hash_key, field)
                    results.append(result)
            
            # 构建结果字典
            result_dict = {}
            for i, field in enumerate(fields):
                if results[i] is not None:
                    result_dict[field] = results[i]
            
            self.logger.debug(f"批量获取Hash {len(result_dict)} 个字段")
            return result_dict
            
        except Exception as e:
            from crawlo.utils.error_handler import ErrorContext
            error_context = ErrorContext(context="Redis批量获取Hash失败")
            self.error_handler.handle_error(
                e, 
                context=error_context, 
                raise_error=False
            )
            return {}


# 全局连接池管理器
_connection_pools: Dict[str, RedisConnectionPool] = {}


def get_redis_pool(redis_url: str, is_cluster: bool = False, cluster_nodes: Optional[List[str]] = None, **kwargs) -> RedisConnectionPool:
    """
    获取Redis连接池实例（单例模式）
    
    Args:
        redis_url: Redis URL
        is_cluster: 是否为集群模式
        cluster_nodes: 集群节点列表
        **kwargs: 连接池配置参数
        
    Returns:
        Redis连接池实例
    """
    # 创建唯一标识符，包含集群相关信息
    pool_key = f"{redis_url}_{is_cluster}_{','.join(cluster_nodes) if cluster_nodes else ''}"
    
    if pool_key not in _connection_pools:
        _connection_pools[pool_key] = RedisConnectionPool(redis_url, is_cluster, cluster_nodes, **kwargs)
    
    return _connection_pools[pool_key]


async def close_all_pools():
    """关闭所有连接池"""
    import asyncio
    global _connection_pools
    
    from crawlo.logging import get_logger
    logger = get_logger('RedisConnectionPool')
    
    if not _connection_pools:
        logger.debug("No Redis connection pools to close")
        return
    
    logger.info(f"Closing {len(_connection_pools)} Redis connection pool(s)...")
    
    close_tasks = []
    for pool_key, pool in _connection_pools.items():
        try:
            close_tasks.append(pool.close())
        except Exception as e:
            logger.error(f"Error scheduling close for pool {pool_key}: {e}")
    
    # 并发关闭所有连接池
    if close_tasks:
        results = await asyncio.gather(*close_tasks, return_exceptions=True)
        
        # 检查结果
        error_count = sum(1 for r in results if isinstance(r, Exception))
        if error_count > 0:
            logger.warning(f"Failed to close {error_count} pool(s)")
        else:
            logger.info("All Redis connection pools closed successfully")
    
    _connection_pools.clear()
    logger.debug("Redis connection pools registry cleared")


# 便捷函数
async def execute_redis_batch(redis_url: str, operations: list, batch_size: int = 100, is_cluster: bool = False, cluster_nodes: Optional[List[str]] = None) -> list:
    """
    便捷函数：执行Redis批量操作
    
    Args:
        redis_url: Redis URL
        operations: 操作列表
        batch_size: 批次大小
        is_cluster: 是否为集群模式
        cluster_nodes: 集群节点列表
        
    Returns:
        执行结果列表
    """
    pool = get_redis_pool(redis_url, is_cluster, cluster_nodes)
    redis_client = await pool.get_connection()
    helper = RedisBatchOperationHelper(redis_client, batch_size)
    return await helper.batch_execute(operations)