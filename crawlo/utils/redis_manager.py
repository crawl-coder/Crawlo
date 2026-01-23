#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
统一 Redis 管理器
================
整合 Redis 连接池、Key 管理和 Key 验证功能
"""

import asyncio
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional, List, Union, TYPE_CHECKING, Tuple
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
                # 首先尝试使用提供的URL
                try:
                    self._connection_pool = aioredis.ConnectionPool.from_url(
                        self.redis_url,
                        **self.config
                    )
                except Exception as e:
                    # 如果认证失败，可能是密码错误，记录警告并继续
                    if 'AUTH' in str(e).upper() or 'PASSWORD' in str(e).upper() or 'INVALID PASSWORD' in str(e).upper():
                        self.logger.warning(f"Redis认证失败，可能密码不正确: {e}")
                        self.logger.warning(f"请检查Redis密码配置: {self.redis_url}")
                        # 尝试重新构建URL，可能URL格式有问题
                        raise
                    else:
                        raise
                
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
                # 统一连接测试成功的日志输出
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
                
            self.logger.debug("Redis连接池已关闭")
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


# RedisBatchOperationHelper 已经移动到 batch_manager.py
# 为了向后兼容，这里提供一个别名
from crawlo.utils.batch_manager import RedisBatchProcessor as RedisBatchOperationHelper


# 全局连接池管理器
_connection_pools: Dict[str, 'RedisConnectionPool'] = {}


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
    # 生成连接池的唯一标识符，包含集群相关信息
    pool_key = f"{redis_url}:{is_cluster}:{cluster_nodes}" if cluster_nodes else f"{redis_url}:{is_cluster}"
    
    if pool_key not in _connection_pools:
        _connection_pools[pool_key] = RedisConnectionPool(
            redis_url, 
            is_cluster=is_cluster, 
            cluster_nodes=cluster_nodes, 
            **kwargs
        )
    return _connection_pools[pool_key]


async def close_all_pools():
    """关闭所有连接池"""
    global _connection_pools
    
    for pool in _connection_pools.values():
        await pool.close()
    
    _connection_pools.clear()


class RedisKeyManager:
    """Redis Key 管理器"""
    
    def __init__(self, project_name: str = "default", spider_name: Optional[str] = None):
        """
        初始化 Redis Key 管理器
        
        Args:
            project_name: 项目名称
            spider_name: 爬虫名称（可选）
        """
        self.project_name = project_name
        self.spider_name = spider_name
        self.logger = None
        
        # 如果提供了 spider_name，则使用更细粒度的命名空间
        if self.spider_name:
            self.namespace = f"{self.project_name}:{self.spider_name}"
        else:
            self.namespace = self.project_name
    
    @property
    def _logger(self):
        """延迟初始化logger"""
        if self.logger is None:
            from crawlo.logging import get_logger
            self.logger = get_logger(self.__class__.__name__)
        return self.logger
    
    def set_spider_name(self, spider_name: str) -> None:
        """
        设置爬虫名称
        
        Args:
            spider_name: 爬虫名称
        """
        self.spider_name = spider_name if spider_name else None
        # 更新命名空间
        if self.spider_name:
            self.namespace = f"{self.project_name}:{self.spider_name}"
        else:
            self.namespace = self.project_name
    
    def _generate_key(self, component: str, sub_component: str) -> str:
        """
        生成 Redis Key
        
        Args:
            component: 组件类型 (queue, filter, item)
            sub_component: 子组件类型
            
        Returns:
            str: 生成的 Redis Key
        """
        key = f"crawlo:{self.namespace}:{component}:{sub_component}"
        
        # 验证生成的 key 是否符合规范
        if not validate_redis_key_naming(key, self.project_name):
            self._logger.warning(f"生成的 Redis Key 不符合命名规范: {key}")
        
        return key
    
    # ==================== 队列相关 Key ====================
    
    def get_requests_queue_key(self) -> str:
        """获取请求队列 Key"""
        return self._generate_key("queue", "requests")
    
    def get_processing_queue_key(self) -> str:
        """获取处理中队列 Key"""
        return self._generate_key("queue", "processing")
    
    def get_failed_queue_key(self) -> str:
        """获取失败队列 Key"""
        return self._generate_key("queue", "failed")
    
    def get_requests_data_key(self) -> str:
        """获取请求数据 Hash Key"""
        return f"{self.get_requests_queue_key()}:data"
    
    def get_processing_data_key(self) -> str:
        """获取处理中数据 Hash Key"""
        return f"{self.get_processing_queue_key()}:data"
    
    def get_failed_retries_key(self, request_key: str) -> str:
        """获取失败重试计数 Key"""
        return f"{self.get_failed_queue_key()}:retries:{request_key}"
    
    # ==================== 过滤器相关 Key ====================
    
    def get_filter_fingerprint_key(self) -> str:
        """获取请求去重过滤器指纹 Key"""
        return self._generate_key("filter", "fingerprint")
    
    # ==================== 数据项相关 Key ====================
    
    def get_item_fingerprint_key(self) -> str:
        """获取数据项去重指纹 Key"""
        return self._generate_key("item", "fingerprint")
    
    # ==================== 静态方法 ====================
    
    @staticmethod
    def from_settings(settings: Any) -> 'RedisKeyManager':
        """
        从配置创建 Redis Key 管理器实例
        
        Args:
            settings: 配置对象
            
        Returns:
            RedisKeyManager: Redis Key 管理器实例
        """
        # 安全获取配置值
        project_name = getattr(settings, 'get', lambda k, d: getattr(settings, k, d))(
            'PROJECT_NAME', 'default'
        )
        
        # 尝试获取 spider_name，这通常在运行时才能确定
        spider_name = getattr(settings, 'get', lambda k, d: getattr(settings, k, d))(
            'SPIDER_NAME', None
        )
        
        return RedisKeyManager(project_name, spider_name)
    
    # ==================== Key 信息提取 ====================
    
    @staticmethod
    def extract_project_name_from_key(key: str) -> Optional[str]:
        """
        从 Redis Key 中提取项目名称
        
        Args:
            key: Redis Key
            
        Returns:
            Optional[str]: 项目名称
        """
        if not key or not key.startswith('crawlo:'):
            return None
            
        parts = key.split(':')
        if len(parts) >= 2:
            return parts[1]
        return None
    
    @staticmethod
    def extract_spider_name_from_key(key: str) -> Optional[str]:
        """
        从 Redis Key 中提取爬虫名称
        
        Args:
            key: Redis Key
            
        Returns:
            Optional[str]: 爬虫名称
        """
        if not key or not key.startswith('crawlo:'):
            return None
            
        parts = key.split(':')
        # 如果格式是 crawlo:project:spider:component:sub_component
        if len(parts) >= 4:
            # 检查是否存在 spider 部分
            if parts[2] not in ['queue', 'filter', 'item']:
                return parts[2]
        return None


# 便利函数
def create_redis_key_manager(project_name: str = "default", spider_name: Optional[str] = None) -> RedisKeyManager:
    """
    创建 Redis Key 管理器实例（便利函数）
    
    Args:
        project_name: 项目名称
        spider_name: 爬虫名称（可选）
        
    Returns:
        RedisKeyManager: Redis Key 管理器实例
    """
    return RedisKeyManager(project_name, spider_name)


def get_redis_key_manager_from_settings(settings: Any) -> RedisKeyManager:
    """
    从配置创建 Redis Key 管理器实例（便利函数）
    
    Args:
        settings: 配置对象
        
    Returns:
        RedisKeyManager: Redis Key 管理器实例
    """
    return RedisKeyManager.from_settings(settings)


class RedisKeyValidator:
    """Redis Key 验证器"""
    
    def __init__(self):
        self.logger = None
    
    @property
    def _logger(self):
        """延迟初始化logger"""
        if self.logger is None:
            from crawlo.logging import get_logger
            self.logger = get_logger(self.__class__.__name__)
        return self.logger
    
    def validate_key_naming(self, key: str, project_name: Optional[str] = None) -> bool:
        """
        验证Redis Key是否符合命名规范
        
        Args:
            key: Redis Key
            project_name: 项目名称（可选）
            
        Returns:
            bool: 是否符合命名规范
        """
        if not isinstance(key, str) or not key:
            return False
        
        # 检查是否以 crawlo: 开头
        if not key.startswith('crawlo:'):
            return False
        
        # 分割Key部分
        parts = key.split(':')
        if len(parts) < 3:
            return False
        
        # 检查基本结构
        if parts[0] != 'crawlo':
            return False
        
        # 检查组件类型
        # 支持两种格式：
        # 1. crawlo:{project}:{component}:{sub_component}
        # 2. crawlo:{project}:{spider}:{component}:{sub_component}
        valid_components = ['filter', 'queue', 'item']
        
        # 检查是否为格式2（包含spider_name）
        if len(parts) >= 4 and parts[3] in valid_components:
            # 格式2: crawlo:{project}:{spider}:{component}:{sub_component}
            project_index = 1
            spider_index = 2
            component_index = 3
            sub_component_index = 4
            
            # 如果提供了项目名称，检查是否匹配
            if project_name and parts[project_index] != project_name:
                return False
            
            # 检查组件类型
            if parts[component_index] not in valid_components:
                return False
            
            # 检查子组件（根据组件类型）
            if parts[component_index] == 'queue':
                valid_subcomponents = ['requests', 'processing', 'failed']
                if len(parts) < sub_component_index + 1 or parts[sub_component_index] not in valid_subcomponents:
                    return False
            elif parts[component_index] == 'filter':
                if len(parts) < sub_component_index + 1 or parts[sub_component_index] != 'fingerprint':
                    return False
            elif parts[component_index] == 'item':
                if len(parts) < sub_component_index + 1 or parts[sub_component_index] != 'fingerprint':
                    return False
        else:
            # 格式1: crawlo:{project}:{component}:{sub_component}
            project_index = 1
            component_index = 2
            sub_component_index = 3
            
            # 如果提供了项目名称，检查是否匹配
            if project_name and parts[project_index] != project_name:
                return False
            
            # 检查组件类型
            if parts[component_index] not in valid_components:
                return False
            
            # 检查子组件（根据组件类型）
            if parts[component_index] == 'queue':
                valid_subcomponents = ['requests', 'processing', 'failed']
                if len(parts) < sub_component_index + 1 or parts[sub_component_index] not in valid_subcomponents:
                    return False
            elif parts[component_index] == 'filter':
                if len(parts) < sub_component_index + 1 or parts[sub_component_index] != 'fingerprint':
                    return False
            elif parts[component_index] == 'item':
                if len(parts) < sub_component_index + 1 or parts[sub_component_index] != 'fingerprint':
                    return False
        
        return True
    
    def validate_multiple_keys(self, keys: List[str], project_name: Optional[str] = None) -> Tuple[bool, List[str]]:
        """
        验证多个Redis Key
        
        Args:
            keys: Redis Key列表
            project_name: 项目名称（可选）
            
        Returns:
            Tuple[bool, List[str]]: (是否全部有效, 无效的Key列表)
        """
        invalid_keys = []
        for key in keys:
            if not self.validate_key_naming(key, project_name):
                invalid_keys.append(key)
        
        return len(invalid_keys) == 0, invalid_keys
    
    def get_key_info(self, key: str) -> dict:
        """
        获取Redis Key的信息
        
        Args:
            key: Redis Key
            
        Returns:
            dict: Key信息
        """
        if not self.validate_key_naming(key):
            return {
                'valid': False,
                'error': 'Key不符合命名规范'
            }
        
        parts = key.split(':')
        info = {
            'valid': True,
            'framework': parts[0]
        }
        
        # 支持两种格式：
        # 1. crawlo:{project}:{component}:{sub_component}
        # 2. crawlo:{project}:{spider}:{component}:{sub_component}
        if len(parts) >= 4 and parts[3] in ['filter', 'queue', 'item']:
            # 格式2: crawlo:{project}:{spider}:{component}:{sub_component}
            info['project'] = parts[1]
            info['spider'] = parts[2]
            info['component'] = parts[3]
            if len(parts) >= 5:
                info['sub_component'] = parts[4]
        else:
            # 格式1: crawlo:{project}:{component}:{sub_component}
            info['project'] = parts[1]
            info['component'] = parts[2]
            if len(parts) >= 4:
                info['sub_component'] = parts[3]
        
        return info


# 便利函数
def validate_redis_key_naming(key: str, project_name: Optional[str] = None) -> bool:
    """
    验证Redis Key是否符合命名规范（便利函数）
    
    Args:
        key: Redis Key
        project_name: 项目名称（可选）
        
    Returns:
        bool: 是否符合命名规范
    """
    validator = RedisKeyValidator()
    return validator.validate_key_naming(key, project_name)


def validate_multiple_redis_keys(keys: List[str], project_name: Optional[str] = None) -> Tuple[bool, List[str]]:
    """
    验证多个Redis Key（便利函数）
    
    Args:
        keys: Redis Key列表
        project_name: 项目名称（可选）
        
    Returns:
        Tuple[bool, List[str]]: (是否全部有效, 无效的Key列表)
    """
    validator = RedisKeyValidator()
    return validator.validate_multiple_keys(keys, project_name)


def get_redis_key_info(key: str) -> dict:
    """
    获取Redis Key的信息（便利函数）
    
    Args:
        key: Redis Key
        
    Returns:
        dict: Key信息
    """
    validator = RedisKeyValidator()
    return validator.get_key_info(key)


def print_validation_report(keys: List[str], project_name: Optional[str] = None):
    """
    打印Redis Key验证报告
    
    Args:
        keys: Redis Key列表
        project_name: 项目名称（可选）
    """
    from crawlo.logging import get_logger
    logger = get_logger('RedisKeyValidator')
    
    validator = RedisKeyValidator()
    is_valid, invalid_keys = validator.validate_multiple_keys(keys, project_name)
    
    logger.info("=" * 50)
    logger.info("Redis Key 命名规范验证报告")
    logger.info("=" * 50)
    
    if is_valid:
        logger.info("所有Redis Key命名规范验证通过")
    else:
        logger.info("发现不符合命名规范的Redis Key:")
        for key in invalid_keys:
            logger.info(f"  - {key}")
    
    logger.info("\nKey 详细信息:")
    for key in keys:
        info = validator.get_key_info(key)
        if info['valid']:
            logger.info(f"  {key}")
            logger.info(f"     框架: {info['framework']}")
            logger.info(f"     项目: {info['project']}")
            logger.info(f"     组件: {info['component']}")
            if 'sub_component' in info:
                logger.info(f"     子组件: {info['sub_component']}")
        else:
            logger.info(f"  {key} - {info.get('error', '无效')}")
    
    logger.info("=" * 50)