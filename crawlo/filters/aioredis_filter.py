import asyncio
from typing import Optional, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from crawlo.crawler import Crawler
    from crawlo.network.request import Request

# 尝试导入Redis集群支持
try:
    from redis.asyncio.cluster import RedisCluster
    REDIS_CLUSTER_AVAILABLE = True
except ImportError:
    RedisCluster = None
    REDIS_CLUSTER_AVAILABLE = False

from crawlo.filters import BaseFilter
from crawlo.logging import get_logger
from crawlo.utils.redis_manager import get_redis_pool, RedisConnectionPool, RedisKeyManager
from crawlo.utils.misc import safe_get_config


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
            ttl: 指纹过期时间（秒）
        """
        self.logger = get_logger(self.__class__.__name__)
        super().__init__(self.logger, stats, debug)

        self.redis_key: str = redis_key
        self.redis = client
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
        settings = crawler.settings
        
        # 从配置中获取Redis URL和其他参数
        redis_url = safe_get_config(settings, 'REDIS_URL')
        if not redis_url:
            # 如果没有配置REDIS_URL，尝试构建
            redis_host = safe_get_config(settings, 'REDIS_HOST', '127.0.0.1')
            redis_port = safe_get_config(settings, 'REDIS_PORT', 6379, int)
            redis_password = safe_get_config(settings, 'REDIS_PASSWORD')
            redis_user = safe_get_config(settings, 'REDIS_USER')  # 获取用户名配置
            redis_db = safe_get_config(settings, 'REDIS_DB', 0, int)
            
            # 根据是否有用户名和密码构建URL
            if redis_user and redis_password:
                # 包含用户名和密码的格式
                redis_url = f"redis://{redis_user}:{redis_password}@{redis_host}:{redis_port}/{redis_db}"
            elif redis_password:
                # 仅包含密码的格式（标准Redis认证）
                redis_url = f"redis://:{redis_password}@{redis_host}:{redis_port}/{redis_db}"
            else:
                # 无认证格式
                redis_url = f"redis://{redis_host}:{redis_port}/{redis_db}"
        
        # 获取项目名称
        project_name = safe_get_config(settings, 'PROJECT_NAME', 'default')
        
        # 获取爬虫名称（可选）
        spider_name = safe_get_config(settings, 'SPIDER_NAME')
        
        # 创建 Redis Key 管理器
        key_manager = RedisKeyManager(project_name, spider_name)
        
        # 生成过滤器键名
        redis_key = key_manager.get_filter_fingerprint_key()
        
        # 获取其他配置参数
        server = safe_get_config(settings, 'REDIS_SERVER', 'localhost:6379')
        db = safe_get_config(settings, 'REDIS_DB', 0, int)
        redis_cls = safe_get_config(settings, 'REDIS_CLASS', 'crawlo.utils.redis_manager.get_redis_pool')
        ttl = safe_get_config(settings, 'REDIS_TTL', 0, int)
        decode_responses = safe_get_config(settings, 'DECODE_RESPONSES', True, bool)
        
        # 获取调试配置
        debug = safe_get_config(settings, 'FILTER_DEBUG', False, bool)
        log_level = safe_get_config(settings, 'LOG_LEVEL_NUM', 20, int)  # 默认INFO级别
        
        # 创建过滤器实例
        instance = cls(
            redis_key=redis_key,
            client=None,
            stats=crawler.stats,
            ttl=ttl,
            debug=debug,
            log_level=log_level
        )
        
        # 获取Redis连接池
        try:
            redis_pool = get_redis_pool(redis_url)
            # 保存连接池引用，以便在需要时获取连接
            instance._redis_pool = redis_pool
        except Exception as e:
            # 如果连接池创建失败，检查是否是密码错误
            if 'AUTH' in str(e).upper() or 'PASSWORD' in str(e).upper() or 'INVALID PASSWORD' in str(e).upper():
                instance.logger.error(f"Redis密码认证失败: {e}")
                instance.logger.error(f"请检查Redis密码配置: {redis_url}")
                # 仍然尝试继续，但标记连接失败
                instance._connection_failed = True
            else:
                instance.logger.error(f"无法创建Redis连接池: {e}")
        
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

            # 定义检查指纹是否存在的操作
            def _check_fingerprint_operation(cluster_mode=False):
                if cluster_mode:
                    # 集群模式下使用哈希标签确保键在同一个slot
                    hash_tag = "{filter}"
                    redis_key_with_tag = f"{self.redis_key}{hash_tag}"
                    # 直接调用异步方法
                    result = redis_client.sismember(redis_key_with_tag, fp)
                else:
                    # 直接调用异步方法
                    result = redis_client.sismember(self.redis_key, fp)
                
                # 处理异步结果
                if asyncio.iscoroutine(result):
                    return result
                else:
                    return result
            
            # 执行操作
            result = self._execute_with_cluster_support(_check_fingerprint_operation)
            exists = await result if asyncio.iscoroutine(result) else result
            
            self._pipeline_operations += 1

            if exists:
                if self.debug:
                    self.logger.debug(f"发现重复请求: {fp}")
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
            
            # 定义添加指纹的操作
            def _add_fingerprint_operation(cluster_mode=False):
                if cluster_mode:
                    # 集群模式下使用哈希标签确保键在同一个slot
                    hash_tag = "{filter}"
                    redis_key_with_tag = f"{self.redis_key}{hash_tag}"
                    # 直接调用异步方法
                    result = redis_client.sadd(redis_key_with_tag, fp)
                    if self.ttl and self.ttl > 0:
                        expire_result = redis_client.expire(redis_key_with_tag, self.ttl)
                        # 处理异步结果
                        if asyncio.iscoroutine(expire_result):
                            return result, expire_result
                        else:
                            return result, None
                    return result, None
                else:
                    # 直接调用异步方法
                    result = redis_client.sadd(self.redis_key, fp)
                    if self.ttl and self.ttl > 0:
                        expire_result = redis_client.expire(self.redis_key, self.ttl)
                        # 处理异步结果
                        if asyncio.iscoroutine(expire_result):
                            return result, expire_result
                        else:
                            return result, None
                    return result, None
            
            # 执行操作
            result_data = self._execute_with_cluster_support(_add_fingerprint_operation)
            
            # 处理结果
            if isinstance(result_data, tuple):
                result, expire_result = result_data
                # 等待异步的expire操作完成
                if asyncio.iscoroutine(expire_result):
                    await expire_result
            else:
                result = result_data
                expire_result = None
            
            # 处理添加结果
            if asyncio.iscoroutine(result):
                added = await result
            else:
                added = result
            
            self._pipeline_operations += 1
            
            # sadd 返回 1 表示新添加
            added = added == 1
            
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
            
            # 定义检查指纹是否存在的操作
            def _check_contains_operation(cluster_mode=False):
                if cluster_mode:
                    # 集群模式下使用哈希标签确保键在同一个slot
                    hash_tag = "{filter}"
                    redis_key_with_tag = f"{self.redis_key}{hash_tag}"
                    # 直接调用异步方法
                    result = redis_client.sismember(redis_key_with_tag, str(fp))
                else:
                    # 直接调用异步方法
                    result = redis_client.sismember(self.redis_key, str(fp))
                
                # 处理异步结果
                if asyncio.iscoroutine(result):
                    return result
                else:
                    return result
            
            # 执行操作
            result = self._execute_with_cluster_support(_check_contains_operation)
            exists = await result if asyncio.iscoroutine(result) else result
            
            return bool(exists)
        except Exception as e:
            self.logger.error(f"检查指纹存在性失败: {fp[:20]}... - {e}")
            # 在网络异常时返回False，避免丢失请求
            return False

    def close(self) -> None:
        """
        关闭过滤器，释放资源
        """
        try:
            # 关闭Redis连接
            if self.redis is not None:
                try:
                    if hasattr(self.redis, 'close'):
                        self.redis.close()
                except Exception as e:
                    self.logger.warning(f"关闭Redis连接时出错: {e}")
                finally:
                    self.redis = None
            
            # 清理连接池引用
            self._redis_pool = None
            
            self.logger.debug("Redis过滤器已关闭")
        except Exception as e:
            self.logger.error(f"关闭Redis过滤器时出错: {e}")


# 为了兼容性，确保导出类
__all__ = ['AioRedisFilter']