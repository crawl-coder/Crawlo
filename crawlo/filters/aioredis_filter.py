from typing import Optional, Dict, Any, Union, Awaitable, Literal, TYPE_CHECKING
import redis.asyncio as aioredis
import asyncio
from inspect import iscoroutinefunction

if TYPE_CHECKING:
    from crawlo.crawler import Crawler
    from crawlo.network.request import Request
    from crawlo.settings.setting_manager import SettingManager

# 尝试导入Redis集群支持
try:
    from redis.asyncio.cluster import RedisCluster
    REDIS_CLUSTER_AVAILABLE = True
except ImportError:
    RedisCluster = None
    REDIS_CLUSTER_AVAILABLE = False

from crawlo.filters import BaseFilter
from crawlo.logging import get_logger
from crawlo.utils.redis_connection_pool import get_redis_pool, RedisConnectionPool


def generate_redis_url_from_settings(settings: Any) -> str:
    """
    根据设置生成Redis URL
    
    Args:
        settings: 配置对象
        
    Returns:
        str: Redis URL
    """
    redis_host = settings.get('REDIS_HOST', 'localhost')
    redis_port = settings.get('REDIS_PORT', 6379)
    redis_password = settings.get('REDIS_PASSWORD', '')
    redis_db = settings.get('REDIS_DB', 0)
    
    if redis_password:
        return f'redis://:{redis_password}@{redis_host}:{redis_port}/{redis_db}'
    else:
        return f'redis://{redis_host}:{redis_port}/{redis_db}'


class AioRedisFilter(BaseFilter):
    """
    基于Redis集合实现的异步请求去重过滤器
    
    支持特性:
    - 分布式爬虫多节点共享去重数据
    - TTL 自动过期清理机制
    - Pipeline 批量操作优化性能
    - 容错设计和连接池管理
    - Redis集群支持
    """

    def __init__(
            self,
            redis_key: str,
            client = None,
            stats: Optional[Dict[str, Any]] = None,
            debug: bool = False,
            log_level: int = 20,  # logging.INFO
            cleanup_fp: bool = False,
            ttl: Optional[int] = None
    ) -> None:
        """
        初始化Redis过滤器
        
        Args:
            redis_key: Redis中存储指纹的键名
            client: Redis客户端实例（可以为None，稍后初始化）
            stats: 统计信息存储
            debug: 是否启用调试模式
            log_level: 日志级别
            cleanup_fp: 关闭时是否清理指纹
            ttl: 指纹过期时间（秒）
        """
        self.logger = get_logger(self.__class__.__name__)
        super().__init__(self.logger, stats, debug)

        self.redis_key: str = redis_key
        self.redis = client
        self.cleanup_fp: bool = cleanup_fp
        self.ttl: Optional[int] = ttl
        
        # 保存连接池引用（用于延迟初始化）
        self._redis_pool: Optional[RedisConnectionPool] = None
        
        # 性能计数器
        self._redis_operations: int = 0
        self._pipeline_operations: int = 0
        
        # 连接状态标记，避免重复尝试连接失败的Redis
        self._connection_failed: bool = False

    @classmethod
    def create_instance(cls, crawler: 'Crawler') -> 'BaseFilter':
        """
        从爬虫配置创建过滤器实例
        
        Args:
            crawler: 爬虫实例
            
        Returns:
            BaseFilter: 过滤器实例
        """
        # 首先尝试直接获取REDIS_URL
        settings = crawler.settings if crawler.settings is not None else {}
        redis_url = settings.get('REDIS_URL') if hasattr(settings, 'get') else None
        
        # 如果没有直接设置REDIS_URL，则根据其他参数生成
        if not redis_url:
            redis_url = generate_redis_url_from_settings(settings)
        
        # 确保 decode_responses=False 以避免编码问题
        decode_responses = False  # settings.get_bool('DECODE_RESPONSES', False) if hasattr(settings, 'get_bool') else False
        ttl_setting = settings.get('REDIS_TTL') if hasattr(settings, 'get') else None

        # 处理TTL设置
        ttl = None
        if ttl_setting is not None:
            ttl = max(0, int(ttl_setting)) if ttl_setting > 0 else None

        try:
            # 使用优化的连接池，确保 decode_responses=False
            # 降低最大连接数以避免连接过多问题
            redis_pool = get_redis_pool(
                redis_url,
                max_connections=10,  # 从20降低到10
                socket_connect_timeout=5,
                socket_timeout=30,
                health_check_interval=30,
                retry_on_timeout=True,
                decode_responses=decode_responses,  # 确保不自动解码响应
                encoding='utf-8'
            )
            
            # 注意：这里不应该使用 await，因为 create_instance 不是异步方法
            # 我们将在实际使用时获取连接
            redis_client = None  # 延迟初始化
        except Exception as e:
            raise RuntimeError(f"Redis连接池初始化失败: {redis_url} - {str(e)}")

        # 使用统一的Redis key命名规范: crawlo:{project_name}:filter:fingerprint
        project_name = settings.get('PROJECT_NAME', 'default') if hasattr(settings, 'get') else 'default'
        redis_key = f"crawlo:{project_name}:filter:fingerprint"

        instance = cls(
            redis_key=redis_key,
            client=redis_client,
            stats=crawler.stats,
            cleanup_fp=bool(settings.get('CLEANUP_FP', False) if hasattr(settings, 'get') else False),
            ttl=ttl,
            debug=bool(settings.get('FILTER_DEBUG', False) if hasattr(settings, 'get') else False),
            log_level=getattr(settings, 'LOG_LEVEL_NUM', 20) if hasattr(settings, '__dict__') else 20  # 默认INFO级别
        )
        
        # 保存连接池引用，以便在需要时获取连接
        instance._redis_pool = redis_pool
        return instance

    async def _get_redis_client(self):
        """
        获取Redis客户端实例（延迟初始化）
        
        Returns:
            Redis客户端实例
        """
        # 如果之前连接失败，直接返回None
        if self._connection_failed:
            return None
            
        if self.redis is None and self._redis_pool is not None:
            try:
                connection = await self._redis_pool.get_connection()
                # 确保返回的是Redis客户端而不是连接池本身
                if hasattr(connection, 'ping'):
                    self.redis = connection
                else:
                    self.redis = connection
            except Exception as e:
                self._connection_failed = True
                self.logger.error(f"Redis连接失败，将使用本地去重: {e}")
                return None
        return self.redis

    def _is_cluster_mode(self) -> bool:
        """
        检查是否为集群模式
        
        Returns:
            bool: 是否为集群模式
        """
        if REDIS_CLUSTER_AVAILABLE and RedisCluster is not None:
            # 检查 redis 是否为 RedisCluster 实例
            if self.redis is not None and isinstance(self.redis, RedisCluster):
                return True
        return False

    def requested(self, request: 'Request') -> bool:
        """
        检查请求是否已存在（同步方法）
        
        对于Redis过滤器，我们采用特殊处理：
        1. 同步方法返回False，表示不重复（避免阻塞）
        2. 实际的重复检查在异步方法requested_async中进行
        3. 这样可以避免在同步上下文中阻塞Redis操作
        
        Args:
            request: 请求对象
            
        Returns:
            False 表示不重复（总是返回False以避免阻塞）
        """
        # Redis过滤器的同步requested方法总是返回False
        # 实际的重复检查应该在异步方法requested_async中进行
        # 这是为了避免在同步上下文中阻塞Redis操作
        return False
        
    async def requested_async(self, request: 'Request') -> bool:
        """
        异步检查请求是否已存在
        
        Args:
            request: 请求对象
            
        Returns:
            True 表示重复，False 表示新请求
        """
        try:
            # 确保Redis客户端已初始化
            redis_client = await self._get_redis_client()
            
            # 如果Redis不可用，返回False表示不重复（避免丢失请求）
            if redis_client is None:
                return False
            
            # 使用基类的指纹生成方法
            fp = str(self._get_fingerprint(request))
            self._redis_operations += 1

            # 检查指纹是否存在
            if self._is_cluster_mode():
                # 集群模式下使用哈希标签确保键在同一个slot
                hash_tag = "{filter}"
                redis_key_with_tag = f"{self.redis_key}{hash_tag}"
                # 直接调用异步方法
                result = redis_client.sismember(redis_key_with_tag, fp)
                if asyncio.iscoroutine(result):
                    exists = await result
                else:
                    exists = result
            else:
                # 直接调用异步方法
                result = redis_client.sismember(self.redis_key, fp)
                if asyncio.iscoroutine(result):
                    exists = await result
                else:
                    exists = result
            
            self._pipeline_operations += 1

            if exists:
                if self.debug:
                    self.logger.debug(f"发现重复请求: {fp[:20]}...")
                return bool(exists)

            # 如果不存在，添加指纹并设置TTL
            await self._add_fingerprint_async(fp)
            return False

        except Exception as e:
            self.logger.error(f"请求检查失败: {getattr(request, 'url', '未知URL')} - {e}")
            # 在网络异常时返回False，避免丢失请求
            return False

    def add_fingerprint(self, fp: str) -> None:
        """
        添加新指纹到Redis集合（同步方法）
        
        Args:
            fp: 请求指纹字符串
        """
        # 这个方法需要同步实现，但Redis操作是异步的
        # 在实际使用中，应该通过异步方式调用 _add_fingerprint_async
        pass

    async def _add_fingerprint_async(self, fp: str) -> bool:
        """
        异步添加新指纹到Redis集合
        
        Args:
            fp: 请求指纹字符串
            
        Returns:
            bool: 是否成功添加（True 表示新添加，False 表示已存在）
        """
        try:
            # 确保Redis客户端已初始化
            redis_client = await self._get_redis_client()
            
            # 如果Redis不可用，返回False表示添加失败
            if redis_client is None:
                return False
            
            fp = str(fp)
            
            # 添加指纹
            if self._is_cluster_mode():
                # 集群模式下使用哈希标签确保键在同一个slot
                hash_tag = "{filter}"
                redis_key_with_tag = f"{self.redis_key}{hash_tag}"
                # 直接调用异步方法
                result = redis_client.sadd(redis_key_with_tag, fp)
                if asyncio.iscoroutine(result):
                    added = await result
                else:
                    added = result
                if self.ttl and self.ttl > 0:
                    expire_result = redis_client.expire(redis_key_with_tag, self.ttl)
                    if asyncio.iscoroutine(expire_result):
                        await expire_result
                    else:
                        expire_result  # 不需要等待同步结果
                added = added == 1  # sadd 返回 1 表示新添加
            else:
                # 直接调用异步方法
                result = redis_client.sadd(self.redis_key, fp)
                if asyncio.iscoroutine(result):
                    added = await result
                else:
                    added = result
                if self.ttl and self.ttl > 0:
                    expire_result = redis_client.expire(self.redis_key, self.ttl)
                    if asyncio.iscoroutine(expire_result):
                        await expire_result
                    else:
                        expire_result  # 不需要等待同步结果
            
            self._pipeline_operations += 1
            
            if self.debug and added:
                self.logger.debug(f"添加新指纹: {fp[:20]}...")
            
            return bool(added)
            
        except Exception as e:
            self.logger.error(f"添加指纹失败: {fp[:20]}... - {e}")
            return False

    def __contains__(self, fp: str) -> bool:
        """
        检查指纹是否存在于Redis集合中（同步方法）
        
        注意：Python的魔术方法__contains__不能是异步的，
        所以这个方法提供同步接口，仅用于基本的存在性检查。
        对于需要异步检查的场景，请使用 contains_async() 方法。
        
        Args:
            fp: 请求指纹字符串
            
        Returns:
            bool: 是否存在
        """
        # 由于__contains__不能是异步的，我们只能提供一个基本的同步检查
        # 如果Redis客户端未初始化，返回False
        if self.redis is None:
            return False
            
        # 对于同步场景，我们无法进行真正的Redis查询
        # 所以返回False，避免阻塞调用
        # 真正的异步检查应该使用 contains_async() 方法
        return False
    
    async def contains_async(self, fp: str) -> bool:
        """
        异步检查指纹是否存在于Redis集合中
        
        这是真正的异步检查方法，应该优先使用这个方法而不是__contains__
        
        Args:
            fp: 请求指纹字符串
            
        Returns:
            bool: 是否存在
        """
        try:
            # 确保Redis客户端已初始化
            redis_client = await self._get_redis_client()
            
            # 如果Redis不可用，返回False表示不存在
            if redis_client is None:
                return False
            
            # 检查指纹是否存在
            if self._is_cluster_mode():
                # 集群模式下使用哈希标签确保键在同一个slot
                hash_tag = "{filter}"
                redis_key_with_tag = f"{self.redis_key}{hash_tag}"
                # 直接调用异步方法
                result = redis_client.sismember(redis_key_with_tag, str(fp))
                if asyncio.iscoroutine(result):
                    exists = await result
                else:
                    exists = result
            else:
                # 直接调用异步方法
                result = redis_client.sismember(self.redis_key, str(fp))
                if asyncio.iscoroutine(result):
                    exists = await result
                else:
                    exists = result
            return bool(exists)
        except Exception as e:
            self.logger.error(f"检查指纹存在性失败: {fp[:20]}... - {e}")
            # 在网络异常时返回False，避免丢失请求
            return False


# 为了兼容性，确保导出类
__all__ = ['AioRedisFilter']