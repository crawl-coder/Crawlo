import pickle
import time
import asyncio
from typing import Optional
import redis.asyncio as aioredis
import traceback
import os

from crawlo import Request
from crawlo.utils.log import get_logger
from crawlo.utils.request_serializer import RequestSerializer


logger = get_logger(__name__)


class RedisPriorityQueue:
    """
    基于 Redis 的分布式异步优先级队列
    """

    def __init__(
            self,
            redis_url: str = None,
            queue_name: str = "crawlo:requests",
            processing_queue: str = "crawlo:processing",
            failed_queue: str = "crawlo:failed",
            max_retries: int = 3,
            timeout: int = 300,  # 任务处理超时时间（秒）
            max_connections: int = 10,  # 连接池大小
            module_name: str = "default"  # 添加 module_name 参数
    ):
        # 如果没有提供 redis_url，则从环境变量构造
        if redis_url is None:
            redis_host = os.getenv('REDIS_HOST', 'localhost')
            redis_port = os.getenv('REDIS_PORT', '6379')
            redis_db = os.getenv('REDIS_DB', '0')
            redis_password = os.getenv('REDIS_PASSWORD', '')

            if redis_password:
                redis_url = f"redis://:{redis_password}@{redis_host}:{redis_port}/{redis_db}"
            else:
                redis_url = f"redis://{redis_host}:{redis_port}/{redis_db}"

        self.redis_url = redis_url
        self.module_name = module_name  # 保存 module_name
        
        # 使用传入的 queue_name
        self.queue_name = queue_name
        
        # 如果未提供 processing_queue 和 failed_queue，则根据 queue_name 自动生成
        if processing_queue == "crawlo:processing":  # 默认值
            # 从 queue_name 生成 processing_queue 名称
            if ":queue:requests" in queue_name:
                self.processing_queue = queue_name.replace(":queue:requests", ":queue:processing")
            else:
                self.processing_queue = f"{queue_name}:processing"
        else:
            self.processing_queue = processing_queue
            
        if failed_queue == "crawlo:failed":  # 默认值
            # 从 queue_name 生成 failed_queue 名称
            if ":queue:requests" in queue_name:
                self.failed_queue = queue_name.replace(":queue:requests", ":queue:failed")
            else:
                self.failed_queue = f"{queue_name}:failed"
        else:
            self.failed_queue = failed_queue
        
        self.max_retries = max_retries
        self.timeout = timeout
        self.max_connections = max_connections
        self._redis = None
        self._lock = asyncio.Lock()  # 用于连接初始化的锁
        self.request_serializer = RequestSerializer()  # 处理序列化

    async def connect(self, max_retries=3, delay=1):
        """异步连接 Redis，支持重试"""
        async with self._lock:
            if self._redis is not None:
                return self._redis

            for attempt in range(max_retries):
                try:
                    self._redis = await aioredis.from_url(
                        self.redis_url,
                        decode_responses=False,  # pickle 需要 bytes
                        max_connections=self.max_connections,
                        socket_connect_timeout=5,
                        socket_timeout=30,
                    )
                    # 测试连接
                    await self._redis.ping()
                    logger.info(f"✅ Redis 连接成功 (Module: {self.module_name})")
                    return self._redis
                except Exception as e:
                    logger.warning(f"⚠️ Redis 连接失败 (尝试 {attempt + 1}/{max_retries}, Module: {self.module_name}): {e}")
                    logger.warning(f"详细错误信息:\n{traceback.format_exc()}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(delay)
                    else:
                        raise ConnectionError(f"❌ 无法连接 Redis (Module: {self.module_name}): {e}")

    async def _ensure_connection(self):
        """确保连接有效"""
        if self._redis is None:
            await self.connect()
        try:
            await self._redis.ping()
        except Exception as e:
            logger.warning(f"🔄 Redis 连接失效 (Module: {self.module_name})，尝试重连...: {e}")
            self._redis = None
            await self.connect()

    async def put(self, request: Request, priority: int = 0) -> bool:
        """放入请求到队列"""
        await self._ensure_connection()
        score = -priority
        key = self._get_request_key(request)
        try:
            # 🔥 使用专用的序列化工具清理 Request
            clean_request = self.request_serializer.prepare_for_serialization(request)
            
            serialized = pickle.dumps(clean_request)
            pipe = self._redis.pipeline()
            pipe.zadd(self.queue_name, {key: score})
            pipe.hset(f"{self.queue_name}:data", key, serialized)
            result = await pipe.execute()
            
            if result[0] > 0:
                logger.debug(f"✅ 成功入队 (Module: {self.module_name}): {request.url}")
            return result[0] > 0
        except Exception as e:
            logger.error(f"❌ 放入队列失败 (Module: {self.module_name}): {e}")
            logger.error(f"详细错误信息:\n{traceback.format_exc()}")
            return False

    async def get(self, timeout: float = 5.0) -> Optional[Request]:
        """
        获取请求（带超时）
        :param timeout: 最大等待时间（秒），避免无限轮询
        """
        await self._ensure_connection()
        start_time = asyncio.get_event_loop().time()

        while True:
            try:
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

                    return pickle.loads(serialized)

                # 检查是否超时
                if asyncio.get_event_loop().time() - start_time > timeout:
                    return None

                # 短暂等待，避免空轮询
                await asyncio.sleep(0.1)

            except Exception as e:
                logger.error(f"❌ 获取队列任务失败 (Module: {self.module_name}): {e}")
                logger.error(f"详细错误信息:\n{traceback.format_exc()}")
                return None

    async def ack(self, request: Request):
        """确认任务完成"""
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

    async def fail(self, request: Request, reason: str = ""):
        """标记任务失败"""
        await self._ensure_connection()
        key = self._get_request_key(request)
        await self.ack(request)

        retry_key = f"{self.failed_queue}:retries:{key}"
        retries = await self._redis.incr(retry_key)
        await self._redis.expire(retry_key, 86400)

        if retries <= self.max_retries:
            await self.put(request, priority=request.priority + 1)
            logger.info(f"🔁 任务重试 [{retries}/{self.max_retries}] (Module: {self.module_name}): {request.url}")
        else:
            failed_data = {
                "url": request.url,
                "reason": reason,
                "retries": retries,
                "failed_at": time.time(),
                "request_pickle": pickle.dumps(request).hex(),  # 可选：保存完整请求
            }
            await self._redis.lpush(self.failed_queue, pickle.dumps(failed_data))
            logger.error(f"❌ 任务彻底失败 [{retries}次] (Module: {self.module_name}): {request.url}")

    def _get_request_key(self, request: Request) -> str:
        """生成请求唯一键"""
        return f"{self.module_name}:url:{hash(request.url)}"

    async def qsize(self) -> int:
        """获取队列大小"""
        await self._ensure_connection()
        return await self._redis.zcard(self.queue_name)

    async def close(self):
        """关闭连接"""
        if self._redis:
            await self._redis.close()
            self._redis = None