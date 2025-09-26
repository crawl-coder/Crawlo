import asyncio
import asyncio
import pickle
import time
import traceback
from typing import Optional, TYPE_CHECKING

import redis.asyncio as aioredis

# 使用 TYPE_CHECKING 避免运行时循环导入
if TYPE_CHECKING:
    from crawlo import Request

from crawlo.utils.error_handler import ErrorHandler
from crawlo.utils.log import get_logger
from crawlo.utils.redis_connection_pool import get_redis_pool, OptimizedRedisConnectionPool
from crawlo.utils.request_serializer import RequestSerializer

# 延迟初始化避免循环依赖
_logger = None
_error_handler = None


def get_module_logger():
    global _logger
    if _logger is None:
        _logger = get_logger(__name__)
    return _logger


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
            redis_url: str = None,
            queue_name: str = None,  # 修改默认值为 None
            processing_queue: str = None,  # 修改默认值为 None
            failed_queue: str = None,  # 修改默认值为 None
            max_retries: int = 3,
            timeout: int = 300,  # 任务处理超时时间（秒）
            max_connections: int = 10,  # 连接池大小
            module_name: str = "default"  # 添加 module_name 参数
    ):
        # 移除直接使用 os.getenv()，要求通过参数传递 redis_url
        if redis_url is None:
            # 如果没有提供 redis_url，则抛出异常，要求在 settings 中配置
            raise ValueError("redis_url must be provided. Configure it in settings instead of using os.getenv()")

        self.redis_url = redis_url
        self.module_name = module_name  # 保存 module_name

        # 如果未提供 queue_name，则根据 module_name 自动生成
        if queue_name is None:
            self.queue_name = f"crawlo:{module_name}:queue:requests"
        else:
            # 处理多重 crawlo 前缀，规范化队列名称
            self.queue_name = self._normalize_queue_name(queue_name)

        # 如果未提供 processing_queue，则根据 queue_name 自动生成
        if processing_queue is None:
            if ":queue:requests" in self.queue_name:
                self.processing_queue = self.queue_name.replace(":queue:requests", ":queue:processing")
            else:
                self.processing_queue = f"{self.queue_name}:processing"
        else:
            self.processing_queue = processing_queue

        # 如果未提供 failed_queue，则根据 queue_name 自动生成
        if failed_queue is None:
            if ":queue:requests" in self.queue_name:
                self.failed_queue = self.queue_name.replace(":queue:requests", ":queue:failed")
            else:
                self.failed_queue = f"{self.queue_name}:failed"
        else:
            self.failed_queue = failed_queue

        self.max_retries = max_retries
        self.timeout = timeout
        self.max_connections = max_connections
        self._redis_pool: Optional[OptimizedRedisConnectionPool] = None
        self._redis: Optional[aioredis.Redis] = None
        self._lock = asyncio.Lock()  # 用于连接初始化的锁
        self.request_serializer = RequestSerializer()  # 处理序列化

    def _normalize_queue_name(self, queue_name: str) -> str:
        """
        规范化队列名称，处理多重 crawlo 前缀
        
        :param queue_name: 原始队列名称
        :return: 规范化后的队列名称
        """
        # 如果队列名称已经符合规范（以 crawlo: 开头且不是 crawlo:crawlo:），则保持不变
        if queue_name.startswith("crawlo:") and not queue_name.startswith("crawlo:crawlo:"):
            return queue_name
            
        # 处理三重 crawlo 前缀，简化为标准格式
        if queue_name.startswith("crawlo:crawlo:crawlo:"):
            # 三重 crawlo 前缀，简化为标准 crawlo: 格式
            remaining = queue_name[21:]  # 去掉 "crawlo:crawlo:crawlo:" 前缀
            if remaining:
                return f"crawlo:{remaining}"
            else:
                return "crawlo:requests"  # 默认名称
                
        # 处理双重 crawlo 前缀
        elif queue_name.startswith("crawlo:crawlo:"):
            # 双重 crawlo 前缀，简化为标准 crawlo: 格式
            remaining = queue_name[14:]  # 去掉 "crawlo:crawlo:" 前缀
            if remaining:
                return f"crawlo:{remaining}"
            else:
                return "crawlo:requests"  # 默认名称
                
        # 处理无 crawlo 前缀的情况
        elif not queue_name.startswith("crawlo:"):
            # 无 crawlo 前缀，添加 crawlo: 前缀
            if queue_name:
                return f"crawlo:{queue_name}"
            else:
                return "crawlo:requests"  # 默认名称
                
        # 其他情况，保持不变
        else:
            return queue_name

    async def connect(self, max_retries=3, delay=1):
        """异步连接 Redis，支持重试"""
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
                        max_connections=self.max_connections,
                        socket_connect_timeout=5,
                        socket_timeout=30,
                        health_check_interval=30,
                        retry_on_timeout=True,
                        decode_responses=False,  # 确保不自动解码响应
                        encoding='utf-8'
                    )

                    self._redis = await self._redis_pool.get_connection()

                    # 测试连接
                    await self._redis.ping()
                    # 只在调试模式下输出详细连接信息
                    # get_module_logger().debug(f"Redis 连接成功 (Module: {self.module_name})")  # 注释掉重复的日志
                    return self._redis
                except Exception as e:
                    error_msg = f"Redis 连接失败 (尝试 {attempt + 1}/{max_retries}, Module: {self.module_name}): {e}"
                    get_module_logger().warning(error_msg)
                    get_module_logger().debug(f"详细错误信息:\n{traceback.format_exc()}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(delay)
                    else:
                        raise ConnectionError(f"无法连接 Redis (Module: {self.module_name}): {e}")

    async def _ensure_connection(self):
        """确保连接有效"""
        if self._redis is None:
            await self.connect()
        try:
            await self._redis.ping()
        except Exception as e:
            get_module_logger().warning(f"Redis 连接失效 (Module: {self.module_name})，尝试重连...: {e}")
            self._redis = None
            await self.connect()

    async def put(self, request, priority: int = 0) -> bool:
        """放入请求到队列"""
        try:
            await self._ensure_connection()
            score = -priority
            key = self._get_request_key(request)

            # 🔥 使用专用的序列化工具清理 Request
            clean_request = self.request_serializer.prepare_for_serialization(request)

            # 确保序列化后的数据可以被正确反序列化
            try:
                serialized = pickle.dumps(clean_request)
                # 验证序列化数据可以被反序列化
                pickle.loads(serialized)
            except Exception as serialize_error:
                get_module_logger().error(f"请求序列化验证失败 (Module: {self.module_name}): {serialize_error}")
                return False

            pipe = self._redis.pipeline()
            pipe.zadd(self.queue_name, {key: score})
            pipe.hset(f"{self.queue_name}:data", key, serialized)
            result = await pipe.execute()

            if result[0] > 0:
                get_module_logger().debug(f"成功入队 (Module: {self.module_name}): {request.url}")  # 注释掉重复的日志
            return result[0] > 0
        except Exception as e:
            get_module_error_handler().handle_error(
                e,
                context=f"放入队列失败 (Module: {self.module_name})",
                raise_error=False
            )
            return False

    async def get(self, timeout: float = 5.0):
        """
        获取请求（带超时）
        :param timeout: 最大等待时间（秒），避免无限轮询
        """
        try:
            await self._ensure_connection()
            start_time = asyncio.get_event_loop().time()

            while True:
                # 尝试获取任务
                result = await self._redis.zpopmin(self.queue_name, count=1)
                if result:
                    key, score = result[0]
                    serialized = await self._redis.hget(f"{self.queue_name}:data", key)
                    if not serialized:
                        continue

                    # 移动到 processing
                    processing_key = f"{key}:{int(time.time())}"
                    pipe = self._redis.pipeline()
                    pipe.zadd(self.processing_queue, {processing_key: time.time() + self.timeout})
                    pipe.hset(f"{self.processing_queue}:data", processing_key, serialized)
                    pipe.hdel(f"{self.queue_name}:data", key)
                    await pipe.execute()

                    # 更安全的反序列化方式
                    try:
                        # 首先尝试标准的 pickle 反序列化
                        request = pickle.loads(serialized)
                        return request
                    except UnicodeDecodeError:
                        # 如果出现编码错误，尝试使用 latin1 解码
                        request = pickle.loads(serialized, encoding='latin1')
                        return request
                    except Exception as pickle_error:
                        # 如果pickle反序列化失败，记录错误并跳过这个任务
                        get_module_logger().error(f"无法反序列化请求数据 (Module: {self.module_name}): {pickle_error}")
                        # 从processing队列中移除这个无效的任务
                        await self._redis.zrem(self.processing_queue, processing_key)
                        await self._redis.hdel(f"{self.processing_queue}:data", processing_key)
                        # 继续尝试下一个任务
                        continue

                # 检查是否超时
                if asyncio.get_event_loop().time() - start_time > timeout:
                    return None

                # 短暂等待，避免空轮询，但减少等待时间以提高响应速度
                await asyncio.sleep(0.001)  # 从0.01减少到0.001

        except Exception as e:
            get_module_error_handler().handle_error(
                e,
                context=f"获取队列任务失败 (Module: {self.module_name})",
                raise_error=False
            )
            return None

    async def ack(self, request: "Request"):
        """确认任务完成"""
        try:
            await self._ensure_connection()
            key = self._get_request_key(request)
            cursor = 0
            while True:
                cursor, keys = await self._redis.zscan(self.processing_queue, cursor, match=f"{key}:*")
                if keys:
                    pipe = self._redis.pipeline()
                    for k in keys:
                        pipe.zrem(self.processing_queue, k)
                        pipe.hdel(f"{self.processing_queue}:data", k)
                    await pipe.execute()
                if cursor == 0:
                    break
        except Exception as e:
            get_module_error_handler().handle_error(
                e,
                context=f"确认任务完成失败 (Module: {self.module_name})",
                raise_error=False
            )

    async def fail(self, request: "Request", reason: str = ""):
        """标记任务失败"""
        try:
            await self._ensure_connection()
            key = self._get_request_key(request)
            await self.ack(request)

            retry_key = f"{self.failed_queue}:retries:{key}"
            retries = await self._redis.incr(retry_key)
            await self._redis.expire(retry_key, 86400)

            if retries <= self.max_retries:
                await self.put(request, priority=request.priority + 1)
                get_module_logger().info(
                    f"任务重试 [{retries}/{self.max_retries}] (Module: {self.module_name}): {request.url}")
            else:
                failed_data = {
                    "url": request.url,
                    "reason": reason,
                    "retries": retries,
                    "failed_at": time.time(),
                    "request_pickle": pickle.dumps(request).hex(),  # 可选：保存完整请求
                }
                await self._redis.lpush(self.failed_queue, pickle.dumps(failed_data))
                get_module_logger().error(f"任务彻底失败 [{retries}次] (Module: {self.module_name}): {request.url}")
        except Exception as e:
            get_module_error_handler().handle_error(
                e,
                context=f"标记任务失败失败 (Module: {self.module_name})",
                raise_error=False
            )

    def _get_request_key(self, request) -> str:
        """生成请求唯一键"""
        return f"{self.module_name}:url:{hash(request.url) & 0x7FFFFFFF}"  # 确保正数

    async def qsize(self) -> int:
        """Get queue size"""
        try:
            await self._ensure_connection()
            return await self._redis.zcard(self.queue_name)
        except Exception as e:
            get_module_error_handler().handle_error(
                e,
                context=f"Failed to get queue size (Module: {self.module_name})",
                raise_error=False
            )
            return 0

    async def close(self):
        """关闭连接"""
        try:
            # 连接池会自动管理连接，这里不需要显式关闭单个连接
            self._redis = None
            self._redis_pool = None
            get_module_logger().debug(f"Redis 连接已释放 (Module: {self.module_name})")
        except Exception as e:
            get_module_error_handler().handle_error(
                e,
                context=f"释放 Redis 连接失败 (Module: {self.module_name})",
                raise_error=False
            )
