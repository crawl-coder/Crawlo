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
- seed URL 先入队自然先被消费

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
        stream_compact: bool = True,
        priority_enabled: bool = True,
        sentinel_urls: Optional[List[str]] = None,
        sentinel_service: str = "mymaster",
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
            sentinel_urls: Sentinel 地址列表（空 = 直连模式）
            sentinel_service: Sentinel 监控的 Master 名称
        """
        self.redis_url = redis_url
        self.project_name = project_name
        self.spider_name = spider_name or "default"
        self._max_length = max_length
        self._consumer_idle_timeout = consumer_idle_timeout
        self._delivery_count_limit = delivery_count_limit
        self._block_timeout = block_timeout
        self._serialization_format = serialization_format
        self._stream_compact = stream_compact
        self._sentinel_urls = sentinel_urls or []
        self._sentinel_service = sentinel_service

        # Consumer 标识
        self._consumer_name = consumer_name or self._generate_consumer_name()

        # Redis 客户端（延迟初始化）
        self._redis = None
        self._connected = False

        # Stream keys：主 Stream + 可选高优 Stream + 死信 Stream
        # priority_enabled=True  → 双 Stream（priority < 0 → 高优）
        # priority_enabled=False → 单 Stream（所有 priority → 同一个）
        namespace = f"{project_name}:{self.spider_name}"
        self._stream = f"crawlo:{namespace}:stream:tasks"
        self._priority_enabled = priority_enabled
        self._high_stream = f"crawlo:{namespace}:stream:tasks:high" if priority_enabled else self._stream
        self._failed_stream = f"crawlo:{namespace}:stream:failed"
        self._group_name = f"crawlo:{namespace}:group:workers"

        # 兼容旧代码的别名
        self._low_stream = self._stream

        # 版本检测标志
        self._redis_version = None
        self._has_xautoclaim = False

        # message_id → stream_key 映射（支持双 Stream 的 ACK/NACK）
        self._message_stream: dict = {}

        self.logger = get_logger(self.__class__.__name__)

    # ---- 公开属性（供 FailoverManager 等外部组件使用） ----

    @property
    def group_name(self) -> str:
        """Consumer Group 名称"""
        return self._group_name

    @property
    def max_length(self) -> int:
        """Stream 最大长度"""
        return self._max_length

    @property
    def high_stream(self) -> str:
        """高优 Stream key"""
        return self._high_stream

    @property
    def stream(self) -> str:
        """主 Stream key"""
        return self._stream

    @property
    def failed_stream(self) -> str:
        """死信 Stream key"""
        return self._failed_stream

    @property
    def consumer_idle_timeout(self) -> int:
        """Consumer 空闲超时（ms）"""
        return self._consumer_idle_timeout

    @property
    def delivery_count_limit(self) -> int:
        """最大投递次数上限"""
        return self._delivery_count_limit

    # -------------------------------
    # 连接管理
    # -------------------------------

    async def connect(self, sentinel_urls: Optional[List[str]] = None):
        """
        连接到 Redis 并初始化 Consumer Group。

        支持两种模式：
        - 直连：使用 redis_url 直接连接单 Redis 实例
        - Sentinel：通过 sentinel_urls 列表连接 Redis Sentinel 集群自动发现 Master

        Args:
            sentinel_urls: Sentinel 地址列表，如 ['redis://10.0.0.1:26379', 'redis://10.0.0.2:26379']
                          为空则使用构造函数中传入的 sentinel_urls / 直连模式
        """
        sentinel_urls = sentinel_urls if sentinel_urls is not None else self._sentinel_urls
        if self._connected:
            await self._ensure_consumer_groups()
            return

        import redis.asyncio as aioredis

        if sentinel_urls:
            # Sentinel 模式：自动发现 Master，故障转移时自动切换
            sentinels = []
            for url in sentinel_urls:
                from urllib.parse import urlparse
                parsed = urlparse(url)
                sentinels.append((parsed.hostname, parsed.port or 26379))

            self._sentinel = aioredis.Sentinel(
                sentinels,
                socket_connect_timeout=3,
                socket_keepalive=True,
            )
            self._redis = self._sentinel.master_for(
                self._sentinel_service or "mymaster",
                db=0,
                decode_responses=False,
                max_connections=50,
                health_check_interval=30,
                retry_on_timeout=True,
            )
            self.logger.info(f"Sentinel mode: {len(sentinels)} sentinel(s)")
        else:
            # 直连模式
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

        # 标记已连接（_recover_orphan_pending 内部调用 claim_pending 需要 _connected=True）
        self._connected = True

        # 回收孤儿 pending 消息（上一轮运行遗留的已读未 ACK 消息）
        await self._recover_orphan_pending()
        self.logger.debug(
            f"Consumer '{self._consumer_name}' connected to group '{self._group_name}'"
        )

    async def _ensure_consumer_groups(self):
        """确保 Consumer Group 存在（幂等，安全重复调用）"""
        streams = {self._stream, self._high_stream}  # 去重：priority 关闭时两者相同
        for stream in streams:
            ok = await create_consumer_group_safe(
                self._redis, stream, self._group_name, self._consumer_name
            )
            if not ok:
                self.logger.warning(f"Failed to ensure consumer group on {stream}")

    async def close(self):
        """关闭连接"""
        if self._redis:
            await self._redis.close()
            self._redis = None
            self._connected = False
        self.logger.debug("Stream queue connection closed")

    def _get_message_stream(self, message_id: str) -> str:
        """根据 message_id 返回正确的 Stream key（支持双 Stream）"""
        return self._message_stream.pop(message_id, self._stream)

    async def _recover_orphan_pending(self):
        """
        启动时回收两个 Stream 的孤儿 pending 消息。

        仅在「重启恢复」场景触发：Consumer Group 存在但无活跃消费者
        （上一轮 Worker 已全部退出）。并发启动场景跳过——
        此时其他 Worker 正在处理消息，不应回收其 pending。

        策略：
        1. 检查 Consumer Group 是否有活跃消费者，有则跳过
        2. XPENDING 检查是否有 pending 消息
        3. XAUTOCLAIM / XPENDING+XCLAIM 将消息 claim 到当前 Consumer
        4. 对每条消息：XRANGE 读原始字段 → XACK+XDEL 原消息 → XADD 重新入队
        5. 重新入队的消息可被任何 Worker 通过 XREADGROUP 正常消费
        """
        # 检查是否为并发启动：若任一流存在活跃消费者（idle < threshold），跳过回收
        idle_threshold = getattr(self, '_orphan_idle_threshold_ms', 30000)
        for check_stream in {self._stream, self._high_stream}:
            try:
                consumers = await self._redis.xinfo_consumers(check_stream, self._group_name)
                if consumers:
                    active = [
                        c for c in consumers
                        if (c.get('idle', c.get(b'idle', 0)) if isinstance(c, dict) else 0) < idle_threshold
                    ]
                    if active:
                        self.logger.debug(
                            f"Active consumers detected in group '{self._group_name}' "
                            f"(stream={check_stream}, idle<{idle_threshold}ms), skipping orphan recovery"
                        )
                        return
            except Exception:
                pass

        streams = {self._stream, self._high_stream}  # 去重：priority 关闭时两者相同
        for stream in streams:
            await self._recover_stream_orphans(stream)

    async def _recover_stream_orphans(self, stream_key: str):
        """回收单个 Stream 的孤儿 pending 消息"""
        try:
            pending_count = await get_pending_count(self._redis, stream_key, self._group_name)
            if pending_count == 0:
                return

            self.logger.info(
                f"Found {pending_count} pending messages in {stream_key}, "
                f"recovering orphan tasks..."
            )

            total_recovered = 0

            while True:
                claimed_messages = await self.claim_pending(
                    min_idle_ms=1,
                    count=100,
                    stream=stream_key,
                )
                if not claimed_messages:
                    break

                for msg_id, request, retry_count in claimed_messages:
                    try:
                        result = await self._redis.eval(
                            (
                                "local msgs = redis.call('XRANGE', KEYS[1], ARGV[1], ARGV[1], 'COUNT', 1) "
                                "if #msgs == 0 then redis.call('XACK', KEYS[1], ARGV[2], ARGV[1]); return {-2, 0} end "
                                "local flat = msgs[1][2]; local fields = {} "
                                "for i = 1, #flat, 2 do fields[flat[i]] = flat[i + 1] end "
                                "local rc = 1; if fields['retry_count'] then rc = tonumber(fields['retry_count']) + 1 end "
                                "redis.call('XACK', KEYS[1], ARGV[2], ARGV[1]) "
                                "redis.call('XDEL', KEYS[1], ARGV[1]) "
                                "if rc >= tonumber(ARGV[5]) then return {0, rc, flat} end "
                                "fields['retry_count'] = tostring(rc) "
                                "fields['reenqueued_at'] = ARGV[3] "
                                "fields['recovered_orphan'] = ARGV[4] "
                                "local nf = {}; for k, v in pairs(fields) do nf[#nf+1]=k; nf[#nf+1]=v end "
                                "redis.call('XADD', KEYS[1], 'MAXLEN', '~', tonumber(ARGV[6]), '*', unpack(nf)) "
                                "return {1, rc}"
                            ),
                            1, stream_key, msg_id, self._group_name,
                            str(time.time()), "true",
                            str(self._delivery_count_limit), str(self._max_length)
                        )
                        if result and len(result) >= 2:
                            action = int(result[0])
                            if action == 0:
                                # 超限进死信
                                flat = result[2]
                                dead_fields = {}
                                it = iter(flat)
                                for k in it:
                                    v = next(it)
                                    k_str = k.decode() if isinstance(k, bytes) else str(k)
                                    dead_fields[k_str.encode()] = v if isinstance(v, bytes) else str(v).encode()
                                dead_fields[b'original_message_id'] = msg_id.encode() if isinstance(msg_id, str) else msg_id
                                dead_fields[b'dead_at'] = str(time.time()).encode()
                                dead_fields[b'dead_reason'] = b"orphan pending on startup, max retries exceeded"
                                dead_fields[b'retry_count'] = str(int(result[1])).encode()
                                await self._redis.xadd(
                                    self._failed_stream, dead_fields,
                                    maxlen=self._max_length // 10, approximate=True
                                )

                        total_recovered += 1
                    except Exception as e:
                        self.logger.warning(f"Failed to recover orphan message {msg_id}: {e}")

            if total_recovered > 0:
                self.logger.info(
                    f"Recovered {total_recovered} orphan pending messages from {stream_key}, "
                    f"re-enqueued for processing"
                )

        except Exception as e:
            self.logger.warning(f"Orphan pending recovery failed for {stream_key}: {e}")

    # -------------------------------
    # 队列操作
    # -------------------------------

    async def put(self, request, priority: int = 0) -> bool:
        """
        XADD 入队。

        priority < 0 → 高优 Stream (tasks:high)
        priority >= 0 → 普通 Stream (tasks)

        Args:
            request: Request 对象
            priority: 优先级（数值越小越优先，负数为高优）

        Returns:
            入队是否成功
        """
        self._ensure_connected()

        # 序列化请求
        data = self._serialize_request(request)

        # 选择目标 Stream（优先级关闭时一律走主 Stream）
        target_stream = self._high_stream if (self._priority_enabled and priority < 0) else self._stream

        # 消息字段
        fields = {
            "data": data,
            "priority": str(priority),
            "enqueued_at": str(time.time()),
            "retry_count": "0",
        }

        try:
            await self._redis.xadd(
                target_stream, fields,
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
        原子性地 XACK + XDEL，消除两条命令之间的崩溃窗口。
        """
        self._ensure_connected()
        stream = self._get_message_stream(message_id)
        lua = (
            "local acked = redis.call('XACK', KEYS[1], ARGV[1], ARGV[2]) "
            "if acked > 0 then redis.call('XDEL', KEYS[1], ARGV[2]) end "
            "return tostring(acked)"
        )
        try:
            result = await self._redis.eval(lua, 1, stream, self._group_name, message_id)
            return result and int(result) > 0
        except Exception as e:
            self.logger.error(f"Atomic ACK failed for {message_id}: {e}")
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
        stream: Optional[str] = None,
    ) -> List[Tuple[str, Any]]:
        """
        回收超时未 ACK 的消息。

        Redis 6.2+：使用 XAUTOCLAIM（一步完成）
        Redis 5.0-6.1：使用 XPENDING + XCLAIM（两步）

        Args:
            min_idle_ms: 最小空闲时间（ms），超过此时间的 pending 消息才回收
            count: 一次最多回收数量
            stream: 目标 Stream key（默认 self._stream）

        Returns:
            [(message_id, request, retry_count), ...]
        """
        self._ensure_connected()
        idle_ms = min_idle_ms if min_idle_ms is not None else self._consumer_idle_timeout
        target_stream = stream or self._stream

        if self._has_xautoclaim:
            return await self._claim_with_xautoclaim(idle_ms, count, target_stream)
        else:
            return await self._claim_manual(idle_ms, count, target_stream)

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
        """获取队列大小（近似，含 Stream 总数）"""
        self._ensure_connected()
        total = 0
        try:
            streams = {self._stream, self._high_stream}
            for stream in streams:
                try:
                    info = await self._redis.xinfo_stream(stream)
                    total += info.get("length", 0)
                except Exception:
                    pass
            return total
        except Exception:
            return 0

    async def empty(self) -> bool:
        """检查两个 Stream 是否都为空"""
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

    # 不再使用 _REQUEST_DEFAULTS 硬编码默认值表
    # 原因：维护默认值表容易与 Request.__init__ 不同步，曾导致 encoding 乱码 bug
    # 现在改为：仅跳过 None/空值字段，反序列化时由 Request.from_dict() 自行补全默认值

    def _serialize_request(self, request) -> bytes:
        """序列化 Request 对象"""
        try:
            from crawlo.utils.request.request_serializer import RequestSerializer
            serializer = RequestSerializer(serialization_format=self._serialization_format)

            if self._stream_compact:
                data = self._compact_request_dict(request)
            else:
                data = serializer.prepare_for_serialization(request)

            if self._serialization_format == "json":
                return json.dumps(data, ensure_ascii=False).encode("utf-8")
            else:
                return pickle.dumps(data)
        except Exception as e:
            self.logger.error(f"Serialization failed: {e}")
            return pickle.dumps(request)  # fallback

    def _compact_request_dict(self, request) -> dict:
        """
        精简序列化：只存储非默认值字段，节省 Redis 内存。

        核心策略：
        - 跳过 priority/headers（已有其他机制处理）
        - 跳过 None/空容器/空字符串
        - 跳过与 Request.from_dict() 默认值相同的字段
        - 注意：encoding 不在默认值表中，因为其默认值是 None（自动检测），
          必须保留为 None 时跳过、非 None 时存储

        反序列化时由 Request.from_dict() 自动补全缺失字段的默认值。
        """
        from crawlo.utils.request.request_serializer import RequestSerializer
        serializer = RequestSerializer(serialization_format=self._serialization_format)
        full = serializer.prepare_for_serialization(request)

        # 与 Request.from_dict() 中的默认值保持一致
        # 注意：encoding 不在此表中！其默认值 None 表示"自动检测"，
        # 而非某个具体编码值，跳过 None 后 from_dict 会正确补全
        _SKIP_DEFAULTS = {
            'method': 'GET',
            'dont_filter': False,
            'allow_redirects': True,
            'verify': True,
            'use_dynamic_loader': False,
        }

        compact = {}
        for key, value in full.items():
            # 跳过 priority（已在 Stream 消息的 priority 字段中）
            if key == 'priority':
                continue
            # 跳过 headers（由 DefaultHeaderMiddleware 在出队时注入）
            if key == 'headers':
                continue
            # 跳过 cookies（由 CookiesMiddleware 在出队时注入）
            if key == 'cookies':
                continue
            # 跳过值为 None 的字段（encoding=None、body=None 等）
            if value is None:
                continue
            # 跳过空容器
            if isinstance(value, (dict, list)) and len(value) == 0:
                continue
            # 跳过空字符串
            if isinstance(value, str) and value == '':
                continue
            # 跳过与 from_dict() 默认值相同的字段
            if key in _SKIP_DEFAULTS and value == _SKIP_DEFAULTS[key]:
                continue
            compact[key] = value

        return compact

    def _deserialize_request(self, raw: bytes):
        """反序列化 Request"""
        try:
            if self._serialization_format == "json":
                data = json.loads(raw.decode("utf-8"))
            else:
                data = pickle.loads(raw)

            if isinstance(data, dict):
                if self._stream_compact:
                    data = self._expand_compact_dict(data)
                from crawlo import Request
                return Request.from_dict(data)
            return data  # 可能是回退的 pickle Request
        except Exception as e:
            self.logger.error(f"Deserialization failed: {e}")
            return None

    def _expand_compact_dict(self, data: dict) -> dict:
        """将精简 dict 还原为完整 dict（由 Request.from_dict() 补全默认值）"""
        # Request.from_dict() 已为所有缺失字段提供正确的默认值：
        # method='GET', dont_filter=False, allow_redirects=True, verify=True,
        # encoding=None（自动检测）, use_dynamic_loader=False 等
        # 无需手动补全，直接返回即可
        data.setdefault('method', 'GET')  # 仅做保底，from_dict 也会处理
        return data

    async def _read(
        self, consumer: str, count: int = 1, block: Optional[int] = None
    ) -> Optional[List[Tuple[bytes, Dict[bytes, bytes]]]]:
        """
        Stream 读取：优先高优，普通兜底。

        1. 若启用双 Stream：先非阻塞检查高优 Stream（10ms）
        2. 阻塞读取普通 Stream（带完整超时）
        """
        if self._priority_enabled and self._high_stream != self._stream:
            try:
                high_msgs = await stream_read(
                    self._redis, self._group_name, consumer,
                    self._high_stream, count=count, block=10,
                )
                if high_msgs:
                    return high_msgs
            except Exception:
                pass

        return await stream_read(
            self._redis, self._group_name, consumer,
            self._stream, count=count, block=block,
        )

    async def _read_with_priority(
        self, consumer: str, count: int = 1, block: int = 5000
    ) -> Optional[List[Tuple[bytes, Dict[bytes, bytes]]]]:
        """[兼容旧接口] 单 Stream 读取"""
        return await self._read(consumer, count=count, block=block if block > 0 else None)

    def _parse_message(
        self, stream_msg: Tuple[bytes, List[Tuple[bytes, Dict[bytes, bytes]]]]
    ) -> Optional[Any]:
        """解析 XREADGROUP 返回的消息（返回 Request，并在 meta 中注入 message_id 用于 ACK）"""
        stream, messages = stream_msg
        if not messages:
            return None
        msg_id_raw, fields = messages[0]
        message_id = msg_id_raw.decode("utf-8") if isinstance(msg_id_raw, bytes) else str(msg_id_raw)
        raw_data = fields.get(b"data")
        if raw_data:
            request = self._deserialize_request(raw_data)
            # 注入 message_id 到 meta，使 ACK/NACK 可用
            if request and hasattr(request, "meta"):
                request.meta["__stream_message_id"] = message_id
                retry_count = int(fields.get(b"retry_count", b"0"))
                request.meta["__stream_retry_count"] = retry_count
                stream_key = stream.decode("utf-8") if isinstance(stream, bytes) else stream
                request.meta["__stream"] = stream_key
            # 记录 message_id → stream 映射
            if message_id:
                self._message_stream[message_id] = stream_key
            return request
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
            request.meta["__stream"] = stream_key = stream.decode("utf-8") if isinstance(stream, bytes) else stream

        # 记录 message_id → stream 映射（用于 ACK/NACK 定位正确 Stream）
        self._message_stream[message_id] = stream_key

        return (request, message_id)

    async def _retry_message(self, message_id: str, error: Optional[str] = None) -> bool:
        """
        原子重试：读取原消息 → XACK+XDEL → XADD 重新入队。
        全程使用 Lua 脚本在 Redis 服务端原子执行。
        """
        stream = self._get_message_stream(message_id)
        lua_retry = (
            "local msgs = redis.call('XRANGE', KEYS[1], ARGV[1], ARGV[1], 'COUNT', 1) "
            "if #msgs == 0 then return {-1, 0} end "
            "local flat = msgs[1][2] "
            "local fields = {} "
            "for i = 1, #flat, 2 do fields[flat[i]] = flat[i + 1] end "
            "local retry_count = 1 "
            "if fields['retry_count'] then retry_count = tonumber(fields['retry_count']) + 1 end "
            "if retry_count >= tonumber(ARGV[5]) then "
            "  redis.call('XACK', KEYS[1], ARGV[2], ARGV[1]) "
            "  redis.call('XDEL', KEYS[1], ARGV[1]) "
            "  return {0, retry_count} "
            "end "
            "redis.call('XACK', KEYS[1], ARGV[2], ARGV[1]) "
            "redis.call('XDEL', KEYS[1], ARGV[1]) "
            "fields['retry_count'] = tostring(retry_count) "
            "fields['last_error'] = ARGV[3] "
            "fields['reenqueued_at'] = ARGV[4] "
            "local nf = {} "
            "for k, v in pairs(fields) do nf[#nf + 1] = k; nf[#nf + 1] = v end "
            "redis.call('XADD', KEYS[1], 'MAXLEN', '~', tonumber(ARGV[6]), '*', unpack(nf)) "
            "return {1, retry_count}"
        )
        try:
            result = await self._redis.eval(
                lua_retry, 1, stream,
                message_id, self._group_name,
                (error or "unknown"), str(time.time()),
                str(self._delivery_count_limit), str(self._max_length)
            )
            if result:
                action = int(result[0]) if len(result) > 0 else -1
                if action == -1:
                    return False
                if action == 0:
                    return await self._escalate_to_dead_letter(message_id, error)
                return True
        except Exception as e:
            self.logger.debug(f"Atomic retry failed for {message_id}: {e}")
        return await self.ack(message_id)

    async def _escalate_to_dead_letter(
        self, message_id: str, error: Optional[str] = None
    ) -> bool:
        """原子地将消息从主 Stream 移除，然后 Python 层写入死信"""
        stream = self._get_message_stream(message_id)
        lua_claim = (
            "local msgs = redis.call('XRANGE', KEYS[1], ARGV[1], ARGV[1], 'COUNT', 1) "
            "if #msgs == 0 then return nil end "
            "redis.call('XACK', KEYS[1], ARGV[2], ARGV[1]) "
            "redis.call('XDEL', KEYS[1], ARGV[1]) "
            "local flat = msgs[1][2] "
            "local out = {} "
            "for i = 1, #flat, 2 do out[#out + 1] = flat[i]; out[#out + 1] = flat[i + 1] end "
            "return out"
        )
        try:
            raw_fields = await self._redis.eval(
                lua_claim, 1, stream, message_id, self._group_name
            )
            if raw_fields:
                # 解析 Lua 返回的平铺数组 → dict
                dead_fields = {}
                retry_count = 0
                it = iter(raw_fields)
                for k in it:
                    v = next(it)
                    k_str = k.decode() if isinstance(k, bytes) else str(k)
                    v_bytes = v if isinstance(v, bytes) else str(v).encode()
                    dead_fields[k_str.encode()] = v_bytes
                    if k_str == 'retry_count':
                        retry_count = int(v_bytes)

                dead_fields[b'original_message_id'] = message_id.encode()
                dead_fields[b'dead_at'] = str(time.time()).encode()
                dead_fields[b'dead_reason'] = (error or "max retries exceeded").encode()
                dead_fields[b'retry_count'] = str(retry_count).encode()

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
        self, min_idle_ms: int, count: int, stream: str
    ) -> List[Tuple[str, Any]]:
        """使用 XAUTOCLAIM 回收消息（Redis 6.2+）"""
        claimed = []
        try:
            result = await self._redis.xautoclaim(
                stream, self._group_name, self._consumer_name,
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
            self.logger.warning(f"XAUTOCLAIM failed on {stream}: {e}")
        return claimed

    async def _claim_manual(
        self, min_idle_ms: int, count: int, stream: str
    ) -> List[Tuple[str, Any]]:
        """手动 XPENDING + XCLAIM（Redis 5.0-6.1 fallback）"""
        claimed = []
        try:
            msgs = await claim_pending_manual(
                self._redis, stream, self._group_name,
                self._consumer_name, min_idle_ms=min_idle_ms, batch_size=count,
            )
            for msg_id, fields in msgs:
                raw_data = fields.get(b"data", fields.get("data"))
                request = self._deserialize_request(raw_data) if raw_data else None
                retry_count = int(fields.get(b"retry_count", fields.get("retry_count", b"0")))
                claimed.append((msg_id, request, retry_count))
        except Exception as e:
            self.logger.warning(f"Manual claim failed on {stream}: {e}")
        return claimed


__all__ = [
    "RedisStreamQueue",
]
