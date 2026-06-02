#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
基于 Redis Streams + Consumer Groups 的分布式队列

相比 ZSET 方案的改进：
- Consumer Group 原生支持多 Consumer 负载均衡
- XACK 确认机制：任务处理完成后才从 Stream 移除
- XCLAIM/XAUTOCLAIM：崩溃 Worker 的未完成任务自动回收
- XPENDING：可查询处理中的任务状态

优先级设计（与 Memory/Redis ZSET 队列口径一致）：
- priority 作为消息字段存储，数值越小越优先
- 出队采用 FIFO 语义（Stream 天然有序），先入队的先被消费
- 这与 Scrapy 等框架行为一致：seed URL 先入队自然先被消费

Redis 版本要求：基础功能 5.0+，XAUTOCLAIM 需要 6.2+。
低版本自动降级为 XPENDING + XCLAIM 手动 fallback。
"""
import asyncio
import json
import pickle
import time
import uuid
from typing import Optional, Any, Dict, List, Tuple

from crawlo.logging import get_logger
from crawlo.queue.task_tracker import TaskResult
from crawlo.utils.redis.stream_utils import (
    detect_redis_version,
    supports_xautoclaim,
    supports_xstream,
    create_consumer_group_safe,
    stream_read,
    claim_pending_manual,
    get_pending_count,
)
from crawlo.utils.redis.keys import RedisKeyManager


class RedisStreamQueue:
    """
    基于 Redis Streams 的分布式队列。

    使用单 Stream + priority 消息字段，与 Memory/Redis ZSET 队列的优先级口径一致：
    - priority 数值越小越优先
    - 出队 FIFO 语义

    Redis Key 命名：
        crawlo:{project}:{spider}:stream:tasks    — 任务队列
        crawlo:{project}:{spider}:stream:failed   — 死信队列
        crawlo:{project}:{spider}:group:workers   — Consumer Group

    消息格式（每条消息 = 一个 Request）：
        {
            "data": <serialized_request>,
            "priority": <int>,
            "enqueued_at": <timestamp>,
            "retry_count": <int>,
        }
    """

    # 类级别：已输出过版本日志的流名称集合（避免多个实例重复日志）
    _version_logged: set = set()

    def __init__(
        self,
        redis_url: str,
        project_name: str = "default",
        spider_name: Optional[str] = None,
        consumer_name: Optional[str] = None,
        max_length: int = 100000,
        consumer_idle_timeout: int = 60000,
        delivery_count_limit: int = 3,
        block_timeout: int = 5000,
        serialization_format: str = "pickle",
    ):
        """
        初始化 Redis Stream Queue。

        Args:
            redis_url: Redis 连接 URL
            project_name: 项目名称
            spider_name: 爬虫名称
            consumer_name: Consumer 名称（None 则自动生成）
            max_length: Stream 最大长度（近似修剪）
            consumer_idle_timeout: Consumer 空闲超时（ms），超时后任务可被回收
            delivery_count_limit: 最大投递次数，超过则进死信
            block_timeout: XREADGROUP 阻塞超时（ms）
            serialization_format: 序列化格式（pickle | json | msgpack）
        """
        self.redis_url = redis_url
        self.project_name = project_name
        self.spider_name = spider_name or "default"
        self._max_length = max_length
        self._consumer_idle_timeout = consumer_idle_timeout
        self._delivery_count_limit = delivery_count_limit
        self._block_timeout = block_timeout
        self._serialization_format = serialization_format

        # Consumer 标识
        self._consumer_name = consumer_name or self._generate_consumer_name()

        # Redis 客户端（延迟初始化）
        self._redis = None
        self._connected = False

        # Stream keys（单 Stream + 死信 Stream）
        namespace = f"{project_name}:{self.spider_name}"
        self._stream = f"crawlo:{namespace}:stream:tasks"
        self._failed_stream = f"crawlo:{namespace}:stream:failed"
        self._group_name = f"crawlo:{namespace}:group:workers"

        # 兼容旧代码的别名（指向同一个 stream）
        self._high_stream = self._stream
        self._low_stream = self._stream

        # 版本检测标志
        self._redis_version = None
        self._has_xautoclaim = False

        self.logger = get_logger(self.__class__.__name__)

    # -------------------------------
    # 连接管理
    # -------------------------------

    async def connect(self):
        """连接到 Redis 并初始化 Consumer Group"""
        if self._connected:
            # 即使已连接，也确保 Consumer Group 存在
            # (防止外部删除 Stream 导致 Group 丢失)
            await self._ensure_consumer_groups()
            return

        import redis.asyncio as aioredis
        self._redis = aioredis.from_url(
            self.redis_url,
            decode_responses=False,
            max_connections=50,
            health_check_interval=30,
            retry_on_timeout=True,
        )

        # 检测 Redis 版本（首次连接输出 INFO，后续仅 debug 避免重复日志）
        try:
            self._redis_version = await detect_redis_version(self._redis)
            self._has_xautoclaim = await supports_xautoclaim(self._redis)
            msg = (
                f"Redis {self._redis_version[0]}.{self._redis_version[1]}.{self._redis_version[2]} "
                f"connected (XAUTOCLAIM: {'yes' if self._has_xautoclaim else 'no, using XPENDING+XCLAIM'})"
            )
            if self._stream not in self._version_logged:
                self._version_logged.add(self._stream)
                self.logger.info(msg)
            else:
                self.logger.debug(msg)
        except Exception:
            self.logger.warning("Failed to detect Redis version, assuming 5.0+")
            self._has_xautoclaim = False

        # 创建 Consumer Group（幂等操作）
        await self._ensure_consumer_groups()

        self._connected = True
        self.logger.debug(
            f"Consumer '{self._consumer_name}' connected to group '{self._group_name}'"
        )

    async def _ensure_consumer_groups(self):
        """确保 Consumer Group 存在（幂等，安全重复调用）"""
        ok = await create_consumer_group_safe(
            self._redis, self._stream, self._group_name, self._consumer_name
        )
        if not ok:
            self.logger.warning(f"Failed to ensure consumer group on {self._stream}")

    async def close(self):
        """关闭连接"""
        if self._redis:
            await self._redis.close()
            self._redis = None
            self._connected = False
        self.logger.debug("Stream queue connection closed")

    # -------------------------------
    # 队列操作
    # -------------------------------

    async def put(self, request, priority: int = 0) -> bool:
        """
        XADD 入队。

        所有请求写入同一个 Stream，priority 作为消息字段保留，
        与 Memory/Redis ZSET 队列口径一致（数值越小越优先）。

        Args:
            request: Request 对象
            priority: 优先级（数值越小越优先，0 = 最高优先）

        Returns:
            入队是否成功
        """
        self._ensure_connected()

        # 序列化请求
        data = self._serialize_request(request)

        # 消息字段
        fields = {
            "data": data,
            "priority": str(priority),
            "enqueued_at": str(time.time()),
            "retry_count": "0",
        }

        try:
            await self._redis.xadd(
                self._stream, fields,
                maxlen=self._max_length, approximate=True
            )
            return True
        except Exception as e:
            self.logger.error(f"XADD failed: {e}")
            return False

    async def get(self, consumer_name: Optional[str] = None, timeout: float = 0.01) -> Optional[Any]:
        """
        非阻塞出队（兼容 IQueue.get API）。

        timeout 为 0 或负数时完全非阻塞。
        """
        self._ensure_connected()
        consumer = consumer_name or self._consumer_name
        block = int(timeout * 1000) if timeout and timeout > 0 else None

        try:
            msgs = await self._read(consumer, count=1, block=block)
            if not msgs:
                return None

            return self._parse_message(msgs[0])
        except Exception as e:
            self.logger.debug(f"Stream get failed: {e}")
            return None

    async def get_blocking(self, timeout: float = 30.0) -> Optional[Any]:
        """
        阻塞出队（分布式模式专用）。

        默认超时 30s。
        """
        self._ensure_connected()
        consumer = self._consumer_name
        block = int(timeout * 1000)

        try:
            msgs = await self._read(consumer, count=1, block=block)
            if not msgs:
                return None

            return self._parse_message(msgs[0])
        except Exception as e:
            self.logger.debug(f"Blocking get failed: {e}")
            return None

    async def get_with_receipt(self, timeout: float = 30.0) -> Optional[Tuple[Any, str]]:
        """
        带 ACK 语义的出队。

        返回 (request, receipt)，receipt = message_id，用于后续 ack/nack。

        Returns:
            (Request, message_id) 或 None
        """
        self._ensure_connected()
        consumer = self._consumer_name
        block = int(timeout * 1000)

        try:
            msgs = await self._read(consumer, count=1, block=block)
            if not msgs:
                return None

            request, message_id = self._parse_message_with_id(msgs[0])
            return (request, message_id)
        except Exception as e:
            self.logger.debug(f"get_with_receipt failed: {e}")
            return None

    # -------------------------------
    # ACK / NACK
    # -------------------------------

    async def ack(self, message_id: str) -> bool:
        """
        XACK 确认消息处理完成。
        """
        self._ensure_connected()
        try:
            result = await self._redis.xack(self._stream, self._group_name, message_id)
            return result > 0
        except Exception as e:
            self.logger.error(f"XACK failed for {message_id}: {e}")
            return False

    async def nack(
        self,
        message_id: str,
        error: Optional[str] = None,
        result: TaskResult = TaskResult.RETRY,
    ) -> bool:
        """
        NACK 处理失败的消息。

        根据 result 类型：
        - RETRY: 重新 XADD 入队（增加重试计数）
        - DEAD_LETTER: 转入失败 Stream
        - ACK (for errors): 直接 XACK（终态错误）
        """
        self._ensure_connected()

        if result == TaskResult.ACK:
            # 终态错误 → 直接 XACK
            return await self.ack(message_id)

        if result == TaskResult.DEAD_LETTER:
            return await self._escalate_to_dead_letter(message_id, error)

        # RETRY: 重新入队
        return await self._retry_message(message_id, error)

    # -------------------------------
    # 故障恢复
    # -------------------------------

    async def claim_pending(
        self,
        min_idle_ms: Optional[int] = None,
        count: int = 10,
    ) -> List[Tuple[str, Any]]:
        """
        回收超时未 ACK 的消息。

        Redis 6.2+：使用 XAUTOCLAIM（一步完成）
        Redis 5.0-6.1：使用 XPENDING + XCLAIM（两步）

        Returns:
            [(message_id, request, retry_count), ...]
        """
        self._ensure_connected()
        idle_ms = min_idle_ms or self._consumer_idle_timeout

        if self._has_xautoclaim:
            return await self._claim_with_xautoclaim(idle_ms, count)
        else:
            return await self._claim_manual(idle_ms, count)

    async def pending_info(self) -> Dict[str, Any]:
        """查询 Pending 状态"""
        self._ensure_connected()
        try:
            count = await get_pending_count(
                self._redis, self._stream, self._group_name
            )
            return {"pending": count, "total": count}
        except Exception:
            return {"pending": 0, "total": 0}

    # -------------------------------
    # 队列状态
    # -------------------------------

    async def size(self) -> int:
        """获取队列大小（近似）"""
        self._ensure_connected()
        try:
            info = await self._redis.xinfo_stream(self._stream)
            return info.get("length", 0)
        except Exception:
            return 0

    async def empty(self) -> bool:
        """检查队列是否为空"""
        return await self.size() == 0

    # ============================
    # 内部方法
    # ============================

    def _ensure_connected(self):
        """确保已连接到 Redis"""
        if not self._connected or not self._redis:
            raise RuntimeError("Stream queue not connected. Call connect() first.")

    def _generate_consumer_name(self) -> str:
        """生成 Consumer 名称"""
        import socket
        import os
        host = socket.gethostname()
        pid = os.getpid()
        uid = uuid.uuid4().hex[:8]
        return f"worker-{host}-{pid}-{uid}"

    def _serialize_request(self, request) -> bytes:
        """序列化 Request 对象（先转为 dict 剥离回调，避免 pickle 无法序列化）"""
        try:
            if self._serialization_format == "json":
                from crawlo.utils.request import request_to_dict
                data = request_to_dict(request)
                return json.dumps(data).encode("utf-8")
            else:
                # 使用框架标准序列化：先转为 dict（剥离 callback/middleware 等不可序列化引用）
                from crawlo.utils.request.request_serializer import RequestSerializer
                serializer = RequestSerializer(serialization_format=self._serialization_format)
                data = serializer.prepare_for_serialization(request)
                return pickle.dumps(data)
        except Exception as e:
            self.logger.error(f"Serialization failed: {e}")
            return pickle.dumps(request)  # fallback

    def _deserialize_request(self, raw: bytes):
        """反序列化 Request（dict → Request，callback 由 Scheduler 恢复）"""
        try:
            if self._serialization_format == "json":
                data = json.loads(raw.decode("utf-8"))
                from crawlo.utils.request import request_from_dict
                return request_from_dict(data)
            else:
                data = pickle.loads(raw)
                if isinstance(data, dict):
                    from crawlo import Request
                    return Request.from_dict(data)
                return data  # 可能是回退的 pickle Request
        except Exception as e:
            self.logger.error(f"Deserialization failed: {e}")
            return None

    async def _read(
        self, consumer: str, count: int = 1, block: Optional[int] = None
    ) -> Optional[List[Tuple[bytes, Dict[bytes, bytes]]]]:
        """单 Stream 读取"""
        return await stream_read(
            self._redis,
            self._group_name,
            consumer,
            self._stream,
            count=count,
            block=block,
        )

    async def _read_with_priority(
        self, consumer: str, count: int = 1, block: int = 5000
    ) -> Optional[List[Tuple[bytes, Dict[bytes, bytes]]]]:
        """[兼容旧接口] 单 Stream 读取"""
        return await self._read(consumer, count=count, block=block if block > 0 else None)

    def _parse_message(
        self, stream_msg: Tuple[bytes, List[Tuple[bytes, Dict[bytes, bytes]]]]
    ) -> Optional[Any]:
        """解析 XREADGROUP 返回的消息（只返回 Request）"""
        _, messages = stream_msg
        if not messages:
            return None
        _, fields = messages[0]
        raw_data = fields.get(b"data")
        if raw_data:
            return self._deserialize_request(raw_data)
        return None

    def _parse_message_with_id(
        self, stream_msg: Tuple[bytes, List[Tuple[bytes, Dict[bytes, bytes]]]]
    ) -> Tuple[Optional[Any], Optional[str]]:
        """解析消息，同时返回 Request 和 message_id"""
        stream, messages = stream_msg
        if not messages:
            return (None, None)
        msg_id_raw, fields = messages[0]
        message_id = msg_id_raw.decode("utf-8") if isinstance(msg_id_raw, bytes) else str(msg_id_raw)
        raw_data = fields.get(b"data")
        request = self._deserialize_request(raw_data) if raw_data else None

        # 获取重试次数
        retry_count = int(fields.get(b"retry_count", b"0"))

        # 标记重试计数到 meta
        if request and hasattr(request, "meta"):
            request.meta["__stream_message_id"] = message_id
            request.meta["__stream_retry_count"] = retry_count
            request.meta["__stream"] = stream.decode("utf-8") if isinstance(stream, bytes) else stream

        return (request, message_id)

    async def _retry_message(self, message_id: str, error: Optional[str] = None) -> bool:
        """
        重试消息：读取原始消息字段，增加 retry_count 后重新 XADD。
        """
        try:
            msgs = await self._redis.xrange(self._stream, min=message_id, max=message_id, count=1)
            if msgs:
                _, fields = msgs[0]
                retry_count = int(fields.get(b"retry_count", b"0")) + 1

                if retry_count >= self._delivery_count_limit:
                    return await self._escalate_to_dead_letter(message_id, error)

                # XACK 当前消息
                await self._redis.xack(self._stream, self._group_name, message_id)

                # 重新入队（保留原始数据，更新重试计数）
                new_fields = {
                    k: v for k, v in fields.items()
                    if k not in (b"retry_count",)
                }
                new_fields[b"retry_count"] = str(retry_count).encode()
                new_fields[b"last_error"] = (error or "unknown").encode()
                new_fields[b"reenqueued_at"] = str(time.time()).encode()

                await self._redis.xadd(
                    self._stream, new_fields,
                    maxlen=self._max_length, approximate=True
                )
                return True
        except Exception as e:
            self.logger.debug(f"Retry read failed for {message_id}: {e}")

        # 读取不到原始消息 → 直接 XACK（可能是已过期/已处理）
        return await self.ack(message_id)

    async def _escalate_to_dead_letter(
        self, message_id: str, error: Optional[str] = None
    ) -> bool:
        """将消息升级到死信队列"""
        try:
            msgs = await self._redis.xrange(self._stream, min=message_id, max=message_id, count=1)
            if msgs:
                _, fields = msgs[0]
                retry_count = int(fields.get(b"retry_count", b"0"))

                # XACK 原消息
                await self._redis.xack(self._stream, self._group_name, message_id)

                # 写入死信 Stream
                dead_fields = dict(fields)
                dead_fields[b"original_message_id"] = message_id.encode()
                dead_fields[b"dead_at"] = str(time.time()).encode()
                dead_fields[b"dead_reason"] = (error or "max retries exceeded").encode()
                dead_fields[b"retry_count"] = str(retry_count).encode()

                await self._redis.xadd(
                    self._failed_stream, dead_fields,
                    maxlen=self._max_length // 10, approximate=True
                )
                self.logger.warning(
                    f"Message {message_id} escalated to dead letter (retries: {retry_count})"
                )
                return True
        except Exception as e:
            self.logger.debug(f"Dead letter escalation failed: {e}")
        return False

    async def _claim_with_xautoclaim(
        self, min_idle_ms: int, count: int
    ) -> List[Tuple[str, Any]]:
        """使用 XAUTOCLAIM 回收消息（Redis 6.2+）"""
        claimed = []
        try:
            result = await self._redis.xautoclaim(
                self._stream, self._group_name, self._consumer_name,
                min_idle_time=min_idle_ms,
                count=count,
            )
            if result:
                # XAUTOCLAIM returns (cursor, messages, [deleted_ids])
                _, messages, _ = result
                for msg in messages:
                    msg_id, fields = msg
                    raw_data = fields.get(b"data")
                    request = self._deserialize_request(raw_data) if raw_data else None
                    retry_count = int(fields.get(b"retry_count", b"0"))
                    claimed.append((msg_id, request, retry_count))
        except Exception as e:
            self.logger.warning(f"XAUTOCLAIM failed on {self._stream}: {e}")
        return claimed

    async def _claim_manual(
        self, min_idle_ms: int, count: int
    ) -> List[Tuple[str, Any]]:
        """手动 XPENDING + XCLAIM（Redis 5.0-6.1 fallback）"""
        claimed = []
        try:
            msgs = await claim_pending_manual(
                self._redis, self._stream, self._group_name,
                self._consumer_name, min_idle_ms=min_idle_ms, batch_size=count,
            )
            for msg_id, fields in msgs:
                raw_data = fields.get(b"data", fields.get("data"))
                request = self._deserialize_request(raw_data) if raw_data else None
                retry_count = int(fields.get(b"retry_count", fields.get("retry_count", b"0")))
                claimed.append((msg_id, request, retry_count))
        except Exception as e:
            self.logger.warning(f"Manual claim failed on {self._stream}: {e}")
        return claimed


__all__ = [
    "RedisStreamQueue",
]
