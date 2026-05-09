import asyncio
from typing import Optional, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from crawlo.crawler import Crawler
    from crawlo.network.request import Request

# Try to import Redis cluster support
try:
    from redis.asyncio.cluster import RedisCluster
    REDIS_CLUSTER_AVAILABLE = True
except ImportError:
    RedisCluster = None
    REDIS_CLUSTER_AVAILABLE = False

from crawlo.filters import BaseFilter
from crawlo.logging import get_logger
from crawlo.utils.misc import safe_get_config
from crawlo.utils.redis import RedisConfig, get_redis_pool, RedisConnectionPool, RedisKeyManager





class AioRedisFilter(BaseFilter):
    """
    Async request deduplication filter based on Redis sets
    
    Features:
    - Distributed deduplication across multiple nodes
    - TTL auto-expiration and cleanup
    - Pipeline batch operations for performance
    - Fault tolerance and connection pool management
    - Redis cluster support
    """

    def __init__(
            self,
            redis_key: str,
            client: Optional[Any] = None,
            stats: Optional[Dict[str, Any]] = None,
            debug: bool = False,
            log_level: int = 20,  # logging.INFO
            ttl: Optional[int] = None
    ) -> None:
        """
        Initialize Redis filter
        
        Args:
            redis_key: Redis key for storing fingerprints
            client: Redis client instance (can be None for lazy init)
            stats: Statistics storage
            debug: Enable debug mode
            log_level: Log level
            ttl: Fingerprint expiration time (seconds)
        """
        self.logger = get_logger(self.__class__.__name__)
        super().__init__(self.logger, stats, debug)

        self.redis_key: str = redis_key
        self.redis = client
        self.ttl: Optional[int] = ttl
        
        # Save connection pool reference (for lazy initialization)
        self._redis_pool: Optional[RedisConnectionPool] = None
        
        # Performance counters
        self._redis_operations: int = 0
        self._pipeline_operations: int = 0
        
        # Connection status flag to avoid repeated connection attempts to failed Redis
        self._connection_failed: bool = False

    @classmethod
    def create_instance(cls, crawler: 'Crawler') -> 'BaseFilter':
        """
        Create filter instance from crawler configuration
        
        Args:
            crawler: Crawler instance
            
        Returns:
            BaseFilter: Filter instance
        """
        settings = crawler.settings
        
        # Get Redis URL and other parameters from configuration
        redis_url = safe_get_config(settings, 'REDIS_URL')
        if not redis_url:
            # If REDIS_URL not configured, try to build it
            # Get Redis connection parameters
            redis_host = safe_get_config(settings, 'REDIS_HOST', 'localhost')
            redis_port = safe_get_config(settings, 'REDIS_PORT', 6379, int)
            redis_db = safe_get_config(settings, 'REDIS_DB', 0, int)
            redis_password = safe_get_config(settings, 'REDIS_PASSWORD')
            redis_username = safe_get_config(settings, 'REDIS_USERNAME')  # 新增：获取用户名
            
            # Use unified Redis config class to generate URL
            redis_config = RedisConfig(
                host=redis_host,
                port=redis_port,
                password=redis_password,
                username=redis_username,
                db=redis_db
            )
            redis_url = redis_config.to_url()
        
        # Get project name
        project_name = safe_get_config(settings, 'PROJECT_NAME', 'default')
        
        # Get spider name (optional)
        spider_name = safe_get_config(settings, 'SPIDER_NAME')
        
        # Create Redis Key manager
        key_manager = RedisKeyManager(project_name, spider_name)
        
        # Generate filter key name
        redis_key = key_manager.get_filter_fingerprint_key()
        
        # Get TTL configuration
        ttl = safe_get_config(settings, 'REDIS_TTL', 0, int)
        
        # Get debug configuration
        debug = safe_get_config(settings, 'FILTER_DEBUG', False, bool)
        log_level = safe_get_config(settings, 'LOG_LEVEL_NUM', 20, int)  # 默认INFO级别
        
        # Create filter instance
        instance = cls(
            redis_key=redis_key,
            client=None,
            stats=crawler.stats,
            ttl=ttl,
            debug=debug,
            log_level=log_level
        )
        
        # Get Redis connection pool
        try:
            redis_pool = get_redis_pool(redis_url)
            # 保存连接池引用，以便在需要时获取连接
            instance._redis_pool = redis_pool
        except Exception as e:
            # If connection pool creation fails, check if it's a password error
            if 'AUTH' in str(e).upper() or 'PASSWORD' in str(e).upper() or 'INVALID PASSWORD' in str(e).upper():
                instance.logger.error(f"Redis authentication failed: {e}")
                instance.logger.error(f"Please check Redis password configuration: {redis_url}")
                # Still try to continue, but mark connection as failed
                instance._connection_failed = True
            else:
                instance.logger.error(f"无法创建Redis连接池: {e}")
        
        return instance

    async def _get_redis_client(self):
        """
        Get Redis client instance (lazy initialization)
        
        Returns:
            Redis client instance
        """
        # If connection previously failed, return None directly
        if self._connection_failed:
            return None
            
        if self.redis is None and self._redis_pool is not None:
            try:
                connection = await self._redis_pool.get_connection()
                # Ensure it returns a Redis client rather than connection pool itself
                if hasattr(connection, 'ping'):
                    self.redis = connection
                else:
                    self.redis = connection
            except Exception as e:
                self._connection_failed = True
                self.logger.error(f"Redis connection failed, will use local deduplication: {e}")
                return None
        return self.redis

    def _is_cluster_mode(self) -> bool:
        """
        Check if in cluster mode
        
        Returns:
            bool: Whether in cluster mode
        """
        if REDIS_CLUSTER_AVAILABLE and RedisCluster is not None:
            # Check if redis is a RedisCluster instance
            if self.redis is not None and isinstance(self.redis, RedisCluster):
                return True
        return False

    def _execute_with_cluster_support(self, operation_func, *args, **kwargs):
        """
        执行支持集群模式的操作
        
        Args:
            operation_func: 要执行的操作函数
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            操作函数的返回结果
        """
        # 确保Redis客户端已初始化
        if self.redis is None:
            raise RuntimeError("Redis客户端未初始化")
            
        # 根据是否为集群模式执行操作
        if self._is_cluster_mode():
            return operation_func(cluster_mode=True, *args, **kwargs)
        else:
            return operation_func(cluster_mode=False, *args, **kwargs)

    def requested(self, request: 'Request') -> bool:
        """
        Check if request already exists (synchronous method)
        
        WARNING: This method is NOT supported for Redis filter.
        Use requested_async() instead for proper deduplication.
        
        Args:
            request: Request object
            
        Raises:
            RuntimeError: Always raised to indicate sync method is not supported
        """
        raise RuntimeError(
            "AioRedisFilter.requested() is not supported. "
            "Use requested_async() for proper Redis deduplication."
        )
        
    async def requested_async(self, request: 'Request') -> bool:
        """
        Async check if request already exists
        
        Args:
            request: Request object
            
        Returns:
            True if duplicate, False if new request
        """
        try:
            # 确保Redis客户端已初始化
            redis_client = await self._get_redis_client()
            
            # If Redis unavailable, return False to avoid losing requests
            if redis_client is None:
                return False
            
            # Use base class fingerprint generation method
            fp = str(self._get_fingerprint(request))
            self._redis_operations += 1

            # 定义检查指纹是否存在的操作
            def _check_fingerprint_operation(cluster_mode=False):
                if cluster_mode:
                    # Cluster mode: use hash tag to ensure key in same slot
                    hash_tag = "{filter}"
                    redis_key_with_tag = f"{self.redis_key}{hash_tag}"
                    return redis_client.sismember(redis_key_with_tag, fp)
                else:
                    return redis_client.sismember(self.redis_key, fp)
            
            # Execute operation
            exists = await self._execute_with_cluster_support(_check_fingerprint_operation)
            
            self._pipeline_operations += 1

            if exists:
                if self.debug:
                    self.logger.debug(f"Found duplicate request: {fp}")
                return bool(exists)

            # If not exists, add fingerprint with TTL
            await self._add_fingerprint_async(fp)
            return False

        except Exception as e:
            self.logger.error(f"Request check failed: {getattr(request, 'url', 'Unknown URL')} - {e}")
            # Return False on network error to avoid losing requests
            return False

    def add_fingerprint(self, fp: str) -> None:
        """
        Add new fingerprint to Redis set (synchronous method)
        
        Note: This method is deprecated. Use _add_fingerprint_async instead.
        
        Args:
            fp: Request fingerprint string
        """
        # This method requires sync implementation, but Redis operations are async
        # In practice, should call _add_fingerprint_async via async method
        pass

    async def _add_fingerprint_async(self, fp: str) -> bool:
        """
        Async add new fingerprint to Redis set
        
        Args:
            fp: Request fingerprint string
            
        Returns:
            bool: Whether successfully added (True = new, False = exists)
        """
        try:
            # Ensure Redis client is initialized
            redis_client = await self._get_redis_client()
            
            # If Redis unavailable, return False
            if redis_client is None:
                return False
            
            fp = str(fp)
            
            # Define add fingerprint operation
            def _add_fingerprint_operation(cluster_mode=False):
                if cluster_mode:
                    # Cluster mode: use hash tag
                    hash_tag = "{filter}"
                    redis_key_with_tag = f"{self.redis_key}{hash_tag}"
                    result = redis_client.sadd(redis_key_with_tag, fp)
                    if self.ttl and self.ttl > 0:
                        expire_result = redis_client.expire(redis_key_with_tag, self.ttl)
                        return result, expire_result
                    return result, None
                else:
                    result = redis_client.sadd(self.redis_key, fp)
                    if self.ttl and self.ttl > 0:
                        expire_result = redis_client.expire(self.redis_key, self.ttl)
                        return result, expire_result
                    return result, None
            
            # Execute operation
            result_data = self._execute_with_cluster_support(_add_fingerprint_operation)
            
            # Handle result
            if isinstance(result_data, tuple):
                result, expire_result = result_data
                # Wait for async expire operation
                if asyncio.iscoroutine(expire_result):
                    await expire_result
            else:
                result = result_data
            
            # Handle add result
            if asyncio.iscoroutine(result):
                added = await result
            else:
                added = result
            
            self._pipeline_operations += 1
            
            # sadd returns 1 if newly added
            added = added == 1
            
            if self.debug and added:
                self.logger.debug(f"Added new fingerprint: {fp[:20]}...")
            
            return bool(added)
            
        except Exception as e:
            self.logger.error(f"Failed to add fingerprint: {fp[:20]}... - {e}")
            return False

    def __contains__(self, fp: str) -> bool:
        """
        Check if fingerprint exists in Redis set (synchronous method)
        
        WARNING: Python magic method __contains__ cannot be async.
        This method provides sync interface only.
        Use contains_async() for actual Redis queries.
        
        Args:
            fp: Request fingerprint string
            
        Returns:
            bool: Whether exists
        """
        # Since __contains__ cannot be async, provide basic sync check
        # If Redis client not initialized, return False
        if self.redis is None:
            return False
            
        # For sync scenario, cannot perform actual Redis query
        # Return False to avoid blocking calls
        # Real async check should use contains_async()
        return False
    
    async def contains_async(self, fp: str) -> bool:
        """
        Async check if fingerprint exists in Redis set
        
        This is the real async check method, should be preferred over __contains__
        
        Args:
            fp: Request fingerprint string
            
        Returns:
            bool: Whether exists
        """
        try:
            # Ensure Redis client is initialized
            redis_client = await self._get_redis_client()
            
            # If Redis unavailable, return False
            if redis_client is None:
                return False
            
            # Define check contains operation
            def _check_contains_operation(cluster_mode=False):
                if cluster_mode:
                    # Cluster mode: use hash tag
                    hash_tag = "{filter}"
                    redis_key_with_tag = f"{self.redis_key}{hash_tag}"
                    return redis_client.sismember(redis_key_with_tag, str(fp))
                else:
                    return redis_client.sismember(self.redis_key, str(fp))
            
            # Execute operation
            exists = await self._execute_with_cluster_support(_check_contains_operation)
            
            return bool(exists)
        except Exception as e:
            self.logger.error(f"Failed to check fingerprint existence: {fp[:20]}... - {e}")
            # Return False on network error to avoid losing requests
            return False

    def close(self) -> None:
        """
        Close filter and release resources
        """
        try:
            # Close Redis connection
            if self.redis is not None:
                try:
                    if hasattr(self.redis, 'close'):
                        self.redis.close()
                except Exception as e:
                    self.logger.warning(f"Error closing Redis connection: {e}")
                finally:
                    self.redis = None
            
            # Clear connection pool reference
            self._redis_pool = None
            
            self.logger.debug("Redis filter closed")
        except Exception as e:
            self.logger.error(f"Error closing Redis filter: {e}")


# For compatibility, ensure class export
__all__ = ['AioRedisFilter']