import asyncio
import pickle
import time
import traceback
from typing import Optional, TYPE_CHECKING, List, Any

# 尝试导入Redis集群支持
try:
    from redis.asyncio.cluster import RedisCluster
    REDIS_CLUSTER_AVAILABLE = True
except ImportError:
    RedisCluster = None
    REDIS_CLUSTER_AVAILABLE = False

# 使用 TYPE_CHECKING 避免运行时循环导入
if TYPE_CHECKING:
    from crawlo import Request

from crawlo.logging import get_logger
from crawlo.utils.request.request_serializer import RequestSerializer
try:
    import msgpack
    MSGPACK_AVAILABLE = True
except ImportError:
    MSGPACK_AVAILABLE = False
from crawlo.utils.error_handler import ErrorHandler, ErrorContext
from crawlo.utils.redis import get_redis_pool, RedisConnectionPool, RedisKeyManager

# 创建logger实例
logger = get_logger(__name__)

# 延迟初始化避免循环依赖
_error_handler = None


def get_module_error_handler():
    global _error_handler
    if _error_handler is None:
        _error_handler = ErrorHandler(__name__)
    return _error_handler


class RedisPriorityQueue:
    """
    基于 Redis 的分布式异步优先级队列
    """

    def __init__(
            self,
            redis_url: Optional[str] = None,
            queue_name: Optional[str] = None,
            failed_queue: Optional[str] = None,
            max_retries: int = 3,
            timeout: int = 300,
            max_connections: int = 10,
            project_name: str = "default",
            spider_name: Optional[str] = None,
            is_cluster: bool = False,
            cluster_nodes: Optional[List[str]] = None,
            serialization_format: str = 'pickle',  # 新增：序列化格式
            redis_shared_mode: bool = True,  # 新增：Redis连接池共享模式
    ) -> None:
        """
        初始化 Redis 优先级队列
        
        Args:
            redis_url: Redis连接URL
            queue_name: 队列名称（可选，自动生成）
            failed_queue: 失败队列名称（可选，自动生成）
            max_retries: 最大重试次数
            timeout: 超时时间（秒）
            max_connections: 最大连接数
            project_name: 项目名称
            spider_name: 爬虫名称（可选）
            is_cluster: 是否为集群模式
            cluster_nodes: 集群节点列表
            serialization_format: 序列化格式
            redis_shared_mode: Redis连接池共享模式，True为共享模式，False为独立模式
        """
        # 移除直接使用 os.getenv()，要求通过参数传递 redis_url
        if redis_url is None:
            # 如果没有提供 redis_url，则抛出异常，要求在 settings 中配置
            raise ValueError("redis_url must be provided. Configure it in settings instead of using os.getenv()")

        self.redis_url: str = redis_url
        self.is_cluster: bool = is_cluster
        self.cluster_nodes: Optional[List[str]] = cluster_nodes
        
        # 存储Redis连接池共享模式
        self._redis_shared_mode = redis_shared_mode  # 存储Redis连接池共享模式
        
        # 创建 Redis Key 管理器
        self.key_manager = RedisKeyManager(project_name, spider_name)
        
        # 添加调试信息
        logger.debug(f"RedisPriorityQueue initialized with project_name: {project_name}, spider_name: {spider_name}")

        # 如果未提供 queue_name，则根据 key_manager 自动生成
        self.queue_name = queue_name or self.key_manager.get_requests_queue_key()

        # 如果未提供 failed_queue，则根据 key_manager 自动生成
        self.failed_queue = failed_queue or self.key_manager.get_failed_queue_key()

        self.max_retries: int = max_retries
        self.timeout: int = timeout
        self.max_connections: int = max_connections
        self._redis_pool: Optional[RedisConnectionPool] = None
        self._redis: Optional[Any] = None
        self._lock: asyncio.Lock = asyncio.Lock()
        self.request_serializer: RequestSerializer = RequestSerializer(serialization_format=serialization_format)
        self.serialization_format: str = serialization_format  # 新增：存储序列化格式

    async def connect(self, max_retries: int = 3, delay: int = 1) -> Optional[Any]:
        """
        异步连接 Redis，支持重试
        
        Args:
            max_retries: 最大重试次数
            delay: 重试延迟时间（秒）
            
        Returns:
            Optional[Any]: Redis 客户端实例
        """
        async with self._lock:
            if self._redis is not None:
                # 如果已经连接，测试连接是否仍然有效
                try:
                    await self._redis.ping()
                    return self._redis
                except Exception:
                    # 连接失效，重新连接
                    self._redis = None

            for attempt in range(max_retries):
                try:
                    # 使用优化的连接池，确保 decode_responses=False 以避免编码问题
                    self._redis_pool = get_redis_pool(
                        self.redis_url,
                        is_cluster=self.is_cluster,
                        cluster_nodes=self.cluster_nodes,
                        max_connections=self.max_connections,
                        socket_connect_timeout=5,
                        socket_timeout=30,
                        health_check_interval=30,
                        retry_on_timeout=True,
                        decode_responses=False,  # 确保不自动解码响应
                        encoding='utf-8',
                        shared=self._redis_shared_mode  # 使用配置的连接池管理模式
                    )

                    self._redis = await self._redis_pool.get_connection()

                    # 测试连接
                    if self._redis:
                        await self._redis.ping()
                    return self._redis
                except Exception as e:
                    error_msg = f"Redis 连接失败 (尝试 {attempt + 1}/{max_retries}, Project: {self.key_manager.project_name}, Spider: {self.key_manager.spider_name}): {e}"
                    logger.warning(error_msg)
                    logger.debug(f"详细错误信息:\n{traceback.format_exc()}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(delay)
                    else:
                        raise ConnectionError(f"无法连接 Redis (Project: {self.key_manager.project_name}, Spider: {self.key_manager.spider_name}): {e}")

    async def _ensure_connection(self) -> None:
        """确保连接有效"""
        if self._redis is None:
            await self.connect()
        try:
            if self._redis:
                await self._redis.ping()
        except Exception as e:
            logger.warning(f"Redis 连接失效 (Project: {self.key_manager.project_name}, Spider: {self.key_manager.spider_name})，尝试重连...: {e}")
            self._redis = None
            await self.connect()

    def _is_cluster_mode(self) -> bool:
        """
        检查是否为集群模式
        
        Returns:
            bool: 是否为集群模式
        """
        if REDIS_CLUSTER_AVAILABLE and RedisCluster is not None:
            # 检查 _redis 是否为 RedisCluster 实例
            if self._redis is not None and isinstance(self._redis, RedisCluster):
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
        # 确保连接有效
        if self._redis is None:
            raise RuntimeError("Redis连接未初始化")
            
        # 根据是否为集群模式执行操作
        if self._is_cluster_mode():
            return operation_func(cluster_mode=True, *args, **kwargs)
        else:
            return operation_func(cluster_mode=False, *args, **kwargs)

    async def put(self, request: 'Request', priority: int = 0) -> bool:
        """
        放入请求到队列
        
        Args:
            request: 请求对象
            priority: 优先级
            
        Returns:
            bool: 是否成功放入队列
        """
        try:
            await self._ensure_connection()
            if not self._redis:
                return False
                
            # 修复优先级行为一致性问题
            # 原来: score = -priority （导致priority大的先出队）
            # 现在: score = priority （确保priority小的先出队，与内存队列一致）
            score = priority
            key = self._get_request_key(request)

            # 🔥 使用专用的序列化工具清理 Request
            clean_request = self.request_serializer.prepare_for_serialization(request)

            # 根据配置的序列化格式进行序列化
            try:
                if self.serialization_format == 'msgpack' and MSGPACK_AVAILABLE:
                    # 使用msgpack序列化
                    serialized = msgpack.packb(clean_request, default=str)
                    # 验证序列化数据可以被反序列化
                    msgpack.unpackb(serialized, raw=False)
                else:
                    # 使用pickle序列化
                    serialized = pickle.dumps(clean_request)
                    # 验证序列化数据可以被反序列化
                    pickle.loads(serialized)
            except Exception as serialize_error:
                logger.error(f"请求序列化验证失败 (Project: {self.key_manager.project_name}, Spider: {self.key_manager.spider_name}): {serialize_error}")
                return False

            # 处理集群模式下的操作
            try:
                if self._is_cluster_mode():
                    # 在集群模式下，确保所有键都在同一个slot中
                    # 可以通过在键名中添加相同的哈希标签来实现
                    hash_tag = "{queue}"  # 使用哈希标签确保键在同一个slot
                    queue_name_with_tag = f"{self.queue_name}{hash_tag}"
                    data_key_with_tag = self.key_manager.get_requests_data_key() + hash_tag
                    
                    pipe = self._redis.pipeline()
                    pipe.zadd(queue_name_with_tag, {key: score})
                    pipe.hset(data_key_with_tag, key, serialized)
                    result = await pipe.execute()
                    
                    # 记录序列化格式信息
                    logger.debug(f"Request enqueued with {self.serialization_format} serialization (Project: {self.key_manager.project_name}, Spider: {self.key_manager.spider_name}): {request.url}")
                else:
                    pipe = self._redis.pipeline()
                    pipe.zadd(self.queue_name, {key: score})
                    pipe.hset(self.key_manager.get_requests_data_key(), key, serialized)
                    result = await pipe.execute()
                    
                    # 记录序列化格式信息
                    logger.debug(f"Request enqueued with {self.serialization_format} serialization (Project: {self.key_manager.project_name}, Spider: {self.key_manager.spider_name}): {request.url}")
            except Exception as e:
                logger.error(f"Redis队列操作失败 (Project: {self.key_manager.project_name}, Spider: {self.key_manager.spider_name}): {e}")
                logger.debug(f"详细错误信息:\n{traceback.format_exc()}")
                return False

            if result and result[0] > 0:
                logger.debug(f"成功入队 (Project: {self.key_manager.project_name}, Spider: {self.key_manager.spider_name}): {request.url}")
                # 记录成功统计
                if hasattr(self, '_stats'):
                    self._stats['successful_puts'] = self._stats.get('successful_puts', 0) + 1
                else:
                    self._stats = {'successful_puts': 1}
            else:
                logger.warning(f"入队失败 (Project: {self.key_manager.project_name}, Spider: {self.key_manager.spider_name}): {request.url}")
                # 记录失败统计
                if hasattr(self, '_stats'):
                    self._stats['failed_puts'] = self._stats.get('failed_puts', 0) + 1
                else:
                    self._stats = {'failed_puts': 1}
            
            success = result and result[0] > 0 if result else False
            return success
        except Exception as e:
            error_context = ErrorContext(
                context=f"放入队列失败 (Project: {self.key_manager.project_name}, Spider: {self.key_manager.spider_name})"
            )
            ErrorHandler(__name__).handle_error(
                e,
                context=error_context,
                raise_error=False
            )
            return False

    async def get(self, timeout: float = 5.0) -> Optional['Request']:
        """
        获取请求（带超时）
        
        Args:
            timeout: 最大等待时间（秒），避免无限轮询
            
        Returns:
            Optional[Request]: 请求对象或 None
        """
        try:
            await self._ensure_connection()
            if not self._redis:
                return None
                
            start_time = asyncio.get_event_loop().time()

            while True:
                # 尝试获取任务
                if self._is_cluster_mode():
                    # 集群模式处理
                    hash_tag = "{queue}"
                    queue_name_with_tag = f"{self.queue_name}{hash_tag}"
                    result = await self._redis.zpopmin(queue_name_with_tag, count=1)
                else:
                    result = await self._redis.zpopmin(self.queue_name, count=1)
                    
                if result:
                    key, score = result[0]
                    data_key = self.key_manager.get_requests_data_key()
                    if self._is_cluster_mode():
                        hash_tag = "{queue}"
                        data_key = self.key_manager.get_requests_data_key() + hash_tag
                        
                    serialized = await self._redis.hget(data_key, key)
                    if not serialized:
                        continue

                    # 根据序列化格式进行反序列化
                    try:
                        if self.serialization_format == 'msgpack' and MSGPACK_AVAILABLE:
                            # 使用msgpack反序列化
                            request = msgpack.unpackb(serialized, raw=False)
                        else:
                            # 使用pickle反序列化
                            try:
                                # 首先尝试标准的 pickle 反序列化
                                request = pickle.loads(serialized)
                            except UnicodeDecodeError:
                                # 如果出现编码错误，尝试使用 latin1 解码
                                request = pickle.loads(serialized, encoding='latin1')
                        return request
                    except Exception as deserialize_error:
                        # 如果反序列化失败，记录错误并跳过这个任务
                        logger.error(f"无法反序列化请求数据 (Project: {self.key_manager.project_name}, Spider: {self.key_manager.spider_name}): {deserialize_error}")
                        # 继续尝试下一个任务
                        continue

                # 检查是否超时
                if asyncio.get_event_loop().time() - start_time > timeout:
                    return None

                # 短暂等待，避免空轮询，但减少等待时间以提高响应速度
                await asyncio.sleep(0.001)  # 从0.01减少到0.001

        except Exception as e:
            error_context = ErrorContext(
                context=f"获取队列任务失败 (Project: {self.key_manager.project_name}, Spider: {self.key_manager.spider_name})"
            )
            ErrorHandler(__name__).handle_error(
                e,
                context=error_context,
                raise_error=False
            )
            return None

    async def ack(self, request: 'Request') -> None:
        """
        确认任务完成
        
        Args:
            request: 请求对象
        """
        # 由于我们不再使用处理队列，ack方法现在是一个空操作
        # 任务在从主队列取出时就已经被认为是完成的
        logger.debug(f"任务确认完成 (Project: {self.key_manager.project_name}, Spider: {self.key_manager.spider_name}): {request.url}")

    async def fail(self, request: 'Request', reason: str = "") -> None:
        """
        标记任务失败
        
        Args:
            request: 请求对象
            reason: 失败原因
        """
        try:
            await self._ensure_connection()
            if not self._redis:
                return
                
            key = self._get_request_key(request)
            await self.ack(request)

            retry_key = f"{self.failed_queue}:retries:{key}"
            failed_queue = self.failed_queue
            
            if self._is_cluster_mode():
                hash_tag = "{queue}"
                retry_key = f"{self.failed_queue}:retries:{key}{hash_tag}"
                failed_queue = f"{self.failed_queue}{hash_tag}"

            retries = await self._redis.incr(retry_key)
            await self._redis.expire(retry_key, 86400)

            if retries <= self.max_retries:
                await self.put(request, priority=request.priority + 1)
                logger.info(
                    f"任务重试 [{retries}/{self.max_retries}] (Project: {self.key_manager.project_name}, Spider: {self.key_manager.spider_name}): {request.url}")
            else:
                failed_data = {
                    "url": request.url,
                    "reason": reason,
                    "retries": retries,
                    "failed_at": time.time(),
                    "request_pickle": pickle.dumps(request).hex(),  # 可选：保存完整请求
                }
                await self._redis.lpush(failed_queue, pickle.dumps(failed_data))
                logger.error(f"任务彻底失败 [{retries}次] (Project: {self.key_manager.project_name}, Spider: {self.key_manager.spider_name}): {request.url}")
        except Exception as e:
            error_context = ErrorContext(
                context=f"标记任务失败失败 (Project: {self.key_manager.project_name}, Spider: {self.key_manager.spider_name})"
            )
            ErrorHandler(__name__).handle_error(
                e,
                context=error_context,
                raise_error=False
            )

    def _get_request_key(self, request: 'Request') -> str:
        """
        生成请求唯一键
        
        Args:
            request: 请求对象
            
        Returns:
            str: 请求唯一键
        """
        # 使用key_manager的namespace来确保一致性
        return f"{self.key_manager.namespace}:url:{hash(request.url) & 0x7FFFFFFF}"  # 确保正数

    async def qsize(self) -> int:
        """
        Get queue size (只检查主队列)

        Returns:
            int: 队列大小（只检查主队列）
        """
        try:
            await self._ensure_connection()
            if not self._redis:
                return 0

            # 只检查主队列大小，不再检查处理中队列
            main_queue_size = 0

            if self._is_cluster_mode():
                hash_tag = "{queue}"
                queue_name_with_tag = f"{self.queue_name}{hash_tag}"
                main_queue_size = await self._redis.zcard(queue_name_with_tag)
            else:
                main_queue_size = await self._redis.zcard(self.queue_name)

            logger.debug(f"队列大小检查 - 主队列: {main_queue_size} (Project: {self.key_manager.project_name}, Spider: {self.key_manager.spider_name})")

            return main_queue_size
        except Exception as e:
            error_context = ErrorContext(
                context=f"Failed to get queue size (Project: {self.key_manager.project_name}, Spider: {self.key_manager.spider_name})"
            )
            get_module_error_handler().handle_error(
                e,
                context=error_context,
                raise_error=False
            )
            return 0

    async def close(self) -> None:
        """关闭连接"""
        try:
            # 显式关闭Redis连接
            if self._redis is not None:
                try:
                    # 不再自动清理Redis数据，保留数据以支持断点续爬
                    logger.debug(f"保留Redis数据以支持断点续爬 (Project: {self.key_manager.project_name}, Spider: {self.key_manager.spider_name})")
                    
                    # 尝试关闭连接
                    if hasattr(self._redis, 'close'):
                        close_result = self._redis.close()
                        if asyncio.iscoroutine(close_result):
                            await close_result
                    
                    # 等待连接关闭完成
                    if hasattr(self._redis, 'wait_closed'):
                        wait_result = self._redis.wait_closed()
                        if asyncio.iscoroutine(wait_result):
                            await wait_result
                except Exception as close_error:
                    logger.warning(
                        f"Error closing Redis connection (Project: {self.key_manager.project_name}, Spider: {self.key_manager.spider_name}): {close_error}"
                    )
                finally:
                    self._redis = None
            
            # 释放连接池引用（连接池由全局管理器管理）
            self._redis_pool = None
            
            logger.debug(f"Redis 连接已释放 (Project: {self.key_manager.project_name}, Spider: {self.key_manager.spider_name})")
        except Exception as e:
            error_context = ErrorContext(
                context=f"释放 Redis 连接失败 (Project: {self.key_manager.project_name}, Spider: {self.key_manager.spider_name})"
            )
            ErrorHandler(__name__).handle_error(
                e,
                context=error_context,
                raise_error=False
            )

    def get_stats(self) -> dict:
        """
        获取队列统计信息
        
        Returns:
            dict: 队列统计信息
        """
        stats = getattr(self, '_stats', {})
        stats['project_name'] = self.key_manager.project_name
        stats['spider_name'] = self.key_manager.spider_name
        stats['queue_name'] = self.queue_name
        return stats
