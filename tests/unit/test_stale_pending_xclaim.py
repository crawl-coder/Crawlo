#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
P0: 分布式 Worker 主动 XCLAIM 扫描 — 单元测试

覆盖：
1. RedisStreamQueue._reenqueue_claimed_message（Lua 脚本重新入队 / 死信 / 异常）
2. RedisStreamQueue.claim_stale_pending（双 Stream 扫描 + 重新入队）
3. Engine._try_claim_stale_pending（非 Stream 队列 / 正常回收 / 异常兜底）
4. Engine._handle_distributed_idle（扫描触发 + idle 计时器重置）
5. LogIntervalExtension._get_pending_count + 日志 pending 字段
6. default_settings 配置项存在性
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch

from crawlo.queue.backends.redis_stream import RedisStreamQueue
from crawlo.core.engine import Engine
from crawlo.core.engine_distributed import DistributedCoordinator
from crawlo.cluster.coordinator import ClusterState


# ========================================================================
# 辅助：构造最小 RedisStreamQueue（绕过真实 __init__ 的 Redis 连接）
# ========================================================================

def _make_minimal_stream_queue(priority_enabled=True):
    """构造最小化 RedisStreamQueue，__new__ + 手动挂属性"""
    q = RedisStreamQueue.__new__(RedisStreamQueue)
    q.redis_url = "redis://localhost:6379"
    q.project_name = "test"
    q.spider_name = "default"
    q._max_length = 100000
    q._consumer_idle_timeout = 60000
    q._delivery_count_limit = 3
    q._block_timeout = 5000
    q._serialization_format = "pickle"
    q._stream_compact = True
    q._sentinel_urls = []
    q._sentinel_service = "mymaster"
    q._consumer_name = "worker-test-001"
    q._redis = Mock()  # 非 None，使 _ensure_connected 通过
    q._connected = True
    namespace = "test:default"
    q._stream = f"crawlo:{namespace}:stream:tasks"
    q._priority_enabled = priority_enabled
    q._high_stream = (
        f"crawlo:{namespace}:stream:tasks:high" if priority_enabled else q._stream
    )
    q._failed_stream = f"crawlo:{namespace}:stream:failed"
    q._group_name = f"crawlo:{namespace}:group:workers"
    q._low_stream = q._stream
    q._redis_version = (7, 0, 0)
    q._has_xautoclaim = True
    q._message_stream = {}
    q.logger = Mock()
    return q


def _make_minimal_engine(settings=None):
    """构造最小化 Engine（参考 test_engine_phase4 风格）"""
    engine = Engine.__new__(Engine)
    engine.running = False
    engine.normal = True
    engine.crawler = None
    engine.settings = settings if settings is not None else {}
    engine.spider = None
    engine.downloader = None
    engine.scheduler = None
    engine.processor = None
    engine.task_manager = None
    engine._start_requests_source = None
    engine._start_requests_is_async = False
    engine._seed_lock_key = None
    engine._seed_renewal_task = None
    engine._close_reason = 'finished'
    engine._spider_closed = False
    engine._background_tasks = set()
    engine._request_available = asyncio.Event()
    engine._idle_since = None
    engine._idle_scan_counter = 0.0
    engine._cluster_state = ClusterState()
    engine.logger = Mock()
    engine._worker_idle_timeout = 120
    engine._distributed_idle_xclaim_scan_interval = 15
    engine._distributed_idle_xclaim_min_idle = 120
    engine._distributed_idle_xclaim_batch = 200
    # P4 Week1 A2：组合组件字段。Engine 的薄代理（_try_claim_stale_pending 等）
    # 都会访问 self._distributed；此处挂真 DistributedCoordinator，以便按真实逻辑测试 XCLAIM。
    engine._distributed = DistributedCoordinator(engine)
    engine._dispatcher = MagicMock()
    return engine


# ========================================================================
# 1. RedisStreamQueue._reenqueue_claimed_message
# ========================================================================

class TestReenqueueClaimedMessage:
    """_reenqueue_claimed_message Lua 脚本重新入队测试"""

    @pytest.mark.asyncio
    async def test_reenqueue_success(self):
        """Lua 返回 {1, rc} → 重新入队成功，返回 1"""
        q = _make_minimal_stream_queue()
        q._redis = AsyncMock()
        # Lua 返回 [1, 1] 表示重新入队成功，retry_count=1
        q._redis.eval = AsyncMock(return_value=[1, 1])

        result = await q._reenqueue_claimed_message(q._stream, "1234-0", reason="stale")
        assert result == 1
        q._redis.eval.assert_called_once()

    @pytest.mark.asyncio
    async def test_reenqueue_dead_letter(self):
        """Lua 返回 {0, rc, flat} → 超限进死信，返回 0"""
        q = _make_minimal_stream_queue()
        q._redis = AsyncMock()
        # flat 字段列表 [field1, value1, ...]
        flat = [b"data", b"\x80\x04test", b"retry_count", b"3"]
        q._redis.eval = AsyncMock(return_value=[0, 3, flat])
        q._redis.xadd = AsyncMock()

        result = await q._reenqueue_claimed_message(q._stream, "1234-0", reason="stale")
        assert result == 0
        # 应该 xadd 到死信队列
        q._redis.xadd.assert_called_once()
        args = q._redis.xadd.call_args
        assert args[0][0] == q._failed_stream

    @pytest.mark.asyncio
    async def test_reenqueue_message_not_found(self):
        """Lua 返回 {-2, 0} → 消息已不存在，返回 -2"""
        q = _make_minimal_stream_queue()
        q._redis = AsyncMock()
        q._redis.eval = AsyncMock(return_value=[-2, 0])

        result = await q._reenqueue_claimed_message(q._stream, "9999-0", reason="stale")
        assert result == -2

    @pytest.mark.asyncio
    async def test_reenqueue_exception(self):
        """Lua 异常 → 返回 -1，不抛出"""
        q = _make_minimal_stream_queue()
        q._redis = AsyncMock()
        q._redis.eval = AsyncMock(side_effect=Exception("Redis error"))

        result = await q._reenqueue_claimed_message(q._stream, "1234-0", reason="stale")
        assert result == -1
        q.logger.warning.assert_called_once()


# ========================================================================
# 2. RedisStreamQueue.claim_stale_pending
# ========================================================================

class TestClaimStalePending:
    """claim_stale_pending 双 Stream 扫描测试"""

    @pytest.mark.asyncio
    async def test_no_stale_messages(self):
        """claim_pending 返回空 → 总回收数 0"""
        q = _make_minimal_stream_queue()
        q.claim_pending = AsyncMock(return_value=[])

        result = await q.claim_stale_pending(min_idle_sec=120, count=100)
        assert result == 0
        # priority_enabled=True 时有 2 个 stream（去重后）
        assert q.claim_pending.call_count == 2

    @pytest.mark.asyncio
    async def test_claim_and_reenqueue(self):
        """claim 到消息 → 重新入队 → 返回回收数"""
        q = _make_minimal_stream_queue()
        # 主 stream 有 2 条，高优 stream 有 1 条
        call_results = [
            [("msg1-0", None, 0), ("msg2-0", None, 0)],
            [("msg3-0", None, 0)],
        ]
        q.claim_pending = AsyncMock(side_effect=call_results)
        q._reenqueue_claimed_message = AsyncMock(return_value=1)

        result = await q.claim_stale_pending(min_idle_sec=120, count=100)
        assert result == 3  # 2 + 1
        assert q._reenqueue_claimed_message.call_count == 3
        # 确认 min_idle_ms 参数转换正确
        first_call = q.claim_pending.call_args_list[0]
        assert first_call.kwargs["min_idle_ms"] == 120000

    @pytest.mark.asyncio
    async def test_priority_disabled_single_stream(self):
        """priority_enabled=False → 去重后只扫描 1 个 stream"""
        q = _make_minimal_stream_queue(priority_enabled=False)
        q.claim_pending = AsyncMock(return_value=[])
        q._reenqueue_claimed_message = AsyncMock(return_value=1)

        result = await q.claim_stale_pending(min_idle_sec=60, count=50)
        assert result == 0
        assert q.claim_pending.call_count == 1

    @pytest.mark.asyncio
    async def test_claim_exception_skipped(self):
        """单个 stream claim 异常 → 跳过，不影响其他 stream"""
        q = _make_minimal_stream_queue()
        q.claim_pending = AsyncMock(side_effect=[Exception("conn error"), []])
        q._reenqueue_claimed_message = AsyncMock(return_value=1)

        result = await q.claim_stale_pending(min_idle_sec=120, count=100)
        assert result == 0
        q.logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_not_connected_raises(self):
        """未连接 → RuntimeError"""
        q = _make_minimal_stream_queue()
        q._connected = False
        with pytest.raises(RuntimeError, match="not connected"):
            await q.claim_stale_pending(min_idle_sec=120, count=100)


# ========================================================================
# 3. Engine._try_claim_stale_pending
# ========================================================================

class TestTryClaimStalePending:
    """Engine._try_claim_stale_pending 测试"""

    @pytest.mark.asyncio
    async def test_no_queue_manager(self):
        """scheduler.queue_manager 为 None → 返回 0"""
        engine = _make_minimal_engine()
        engine.scheduler = Mock()
        engine.scheduler.queue_manager = None

        result = await engine._try_claim_stale_pending()
        assert result == 0

    @pytest.mark.asyncio
    async def test_no_inner_queue(self):
        """queue_manager._queue 为 None → 返回 0"""
        engine = _make_minimal_engine()
        engine.scheduler = Mock()
        engine.scheduler.queue_manager = Mock()
        engine.scheduler.queue_manager._queue = None

        result = await engine._try_claim_stale_pending()
        assert result == 0

    @pytest.mark.asyncio
    async def test_memory_queue_no_claim_method(self):
        """内存队列无 claim_stale_pending 方法 → 返回 0"""
        engine = _make_minimal_engine()
        engine.scheduler = Mock()
        engine.scheduler.queue_manager = Mock()
        engine.scheduler.queue_manager._queue = Mock(spec=[])  # 无任何方法

        result = await engine._try_claim_stale_pending()
        assert result == 0

    @pytest.mark.asyncio
    async def test_successful_claim(self):
        """成功回收 → 返回回收数，设置 _request_available"""
        engine = _make_minimal_engine()
        inner_queue = AsyncMock()
        inner_queue.claim_stale_pending = AsyncMock(return_value=5)
        engine.scheduler = Mock()
        engine.scheduler.queue_manager = Mock()
        engine.scheduler.queue_manager._queue = inner_queue

        result = await engine._try_claim_stale_pending()
        assert result == 5
        inner_queue.claim_stale_pending.assert_called_once_with(
            min_idle_sec=120, count=200
        )
        # 应记录 info 日志
        engine.logger.info.assert_called_once()
        # 应设置 _request_available 唤醒主循环
        assert engine._request_available.is_set()

    @pytest.mark.asyncio
    async def test_zero_claim_no_log(self):
        """回收 0 条 → 不记录 info 日志，不唤醒"""
        engine = _make_minimal_engine()
        inner_queue = AsyncMock()
        inner_queue.claim_stale_pending = AsyncMock(return_value=0)
        engine.scheduler = Mock()
        engine.scheduler.queue_manager = Mock()
        engine.scheduler.queue_manager._queue = inner_queue

        result = await engine._try_claim_stale_pending()
        assert result == 0
        engine.logger.info.assert_not_called()

    @pytest.mark.asyncio
    async def test_exception_returns_zero(self):
        """异常 → 返回 0，记录 debug 日志"""
        engine = _make_minimal_engine()
        inner_queue = AsyncMock()
        inner_queue.claim_stale_pending = AsyncMock(
            side_effect=Exception("Redis down")
        )
        engine.scheduler = Mock()
        engine.scheduler.queue_manager = Mock()
        engine.scheduler.queue_manager._queue = inner_queue

        result = await engine._try_claim_stale_pending()
        assert result == 0
        engine.logger.debug.assert_called_once()


# ========================================================================
# 4. Engine._handle_distributed_idle 扫描触发
# ========================================================================

class TestHandleDistributedIdleScan:
    """_handle_distributed_idle 主动扫描触发测试"""

    @pytest.mark.asyncio
    async def test_idle_counter_accumulates(self):
        """idle 累计未达阈值 → 不触发扫描"""
        engine = _make_minimal_engine()
        engine._distributed_idle_xclaim_scan_interval = 15
        engine._idle_scan_counter = 0.0
        engine._worker_idle_timeout = 120
        engine.scheduler = Mock()
        engine.scheduler.next_request_blocking = AsyncMock(return_value=None)
        # P4 Week1 A2：真 DistributedCoordinator 内部调用 self.try_claim_stale_pending()，需 mock 组合组件方法
        engine._distributed.try_claim_stale_pending = AsyncMock(return_value=0)
        engine._try_claim_stale_pending = engine._distributed.try_claim_stale_pending  # 兼容旧断言

        # 模拟 10s 等待（小于 15s 阈值）
        with patch("crawlo.core.engine.time.monotonic", side_effect=[0, 10, 10, 10]):
            result = await engine._handle_distributed_idle(idle_count=1)

        assert result is False
        engine._try_claim_stale_pending.assert_not_called()
        assert engine._idle_scan_counter == 10.0

    @pytest.mark.asyncio
    async def test_scan_triggered_at_threshold(self):
        """idle 累计达阈值 → 触发扫描，无回收 → 不重置 idle_since"""
        engine = _make_minimal_engine()
        engine._distributed_idle_xclaim_scan_interval = 15
        engine._idle_scan_counter = 14.0  # 接近阈值
        engine._worker_idle_timeout = 120
        engine._idle_since = None
        engine.scheduler = Mock()
        engine.scheduler.next_request_blocking = AsyncMock(return_value=None)
        engine._distributed.try_claim_stale_pending = AsyncMock(return_value=0)
        engine._try_claim_stale_pending = engine._distributed.try_claim_stale_pending

        # 等待 2s（14 + 2 = 16 >= 15）
        with patch(
            "crawlo.core.engine.time.monotonic",
            side_effect=[100, 102, 102, 102],
        ):
            result = await engine._handle_distributed_idle(idle_count=1)

        assert result is False
        engine._try_claim_stale_pending.assert_called_once()
        # 无回收 → idle_since 应被设置
        assert engine._idle_since is not None
        # 计数器应被重置
        assert engine._idle_scan_counter == 0.0

    @pytest.mark.asyncio
    async def test_scan_reset_idle_on_claim(self):
        """扫描回收到消息 → 重置 idle_since，重置计数器"""
        engine = _make_minimal_engine()
        engine._distributed_idle_xclaim_scan_interval = 15
        engine._idle_scan_counter = 20.0  # 已超阈值
        engine._worker_idle_timeout = 120
        engine._idle_since = 100.0
        engine.scheduler = Mock()
        engine.scheduler.next_request_blocking = AsyncMock(return_value=None)
        engine._distributed.try_claim_stale_pending = AsyncMock(return_value=3)
        engine._try_claim_stale_pending = engine._distributed.try_claim_stale_pending

        with patch(
            "crawlo.core.engine.time.monotonic",
            side_effect=[100, 100, 102, 102],
        ):
            result = await engine._handle_distributed_idle(idle_count=1)

        assert result is False
        engine._try_claim_stale_pending.assert_called_once()
        # 有回收 → idle_since 重置为 None
        assert engine._idle_since is None
        assert engine._idle_scan_counter == 0.0

    @pytest.mark.asyncio
    async def test_request_resets_counter(self):
        """获取到请求 → 重置 idle_scan_counter 和 idle_since"""
        engine = _make_minimal_engine()
        engine._idle_scan_counter = 10.0
        engine._idle_since = 100.0
        engine._worker_idle_timeout = 120
        engine.scheduler = Mock()
        mock_request = Mock()
        engine.scheduler.next_request_blocking = AsyncMock(return_value=mock_request)
        engine._distributed.try_claim_stale_pending = AsyncMock(return_value=0)
        engine._try_claim_stale_pending = engine._distributed.try_claim_stale_pending
        # 关闭协程避免 "coroutine never awaited" warning，同时保留 assert 能力
        engine._create_background_task = Mock(side_effect=lambda coro: coro.close())

        with patch("crawlo.core.engine.time.monotonic", side_effect=[100, 100, 101]):
            result = await engine._handle_distributed_idle(idle_count=1)

        assert result is False
        engine._try_claim_stale_pending.assert_not_called()
        assert engine._idle_scan_counter == 0.0
        assert engine._idle_since is None
        engine._create_background_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_idle_timeout_exit(self):
        """idle 超时 → 返回 True 退出"""
        engine = _make_minimal_engine()
        engine._worker_idle_timeout = 5
        engine._idle_scan_counter = 0.0
        engine._idle_since = 100.0
        engine._distributed_idle_xclaim_scan_interval = 999  # 不触发扫描
        engine.scheduler = Mock()
        engine.scheduler.next_request_blocking = AsyncMock(return_value=None)
        engine._distributed.try_claim_stale_pending = AsyncMock(return_value=0)
        engine._try_claim_stale_pending = engine._distributed.try_claim_stale_pending

        # remaining = 5 - (106 - 100) = -1 <= 0 → 退出
        with patch("crawlo.core.engine.time.monotonic", side_effect=[106]):
            result = await engine._handle_distributed_idle(idle_count=1)

        assert result is True


# ========================================================================
# 5. LogIntervalExtension._get_pending_count + 日志
# ========================================================================

class TestLogIntervalPendingField:
    """LogIntervalExtension pending 观测字段测试"""

    def _make_extension(self):
        """构造最小化 LogIntervalExtension"""
        from crawlo.extensions.log_interval import LogIntervalExtension

        ext = LogIntervalExtension.__new__(LogIntervalExtension)
        ext.enabled = True
        ext.stats = Mock()
        ext.stats.crawler = Mock()
        ext.stats.crawler.engine = Mock()
        ext.stats.crawler.engine.scheduler = Mock()
        ext.stats.crawler.engine.scheduler.queue_manager = Mock()
        ext.seconds = 60
        ext.interval = 1
        ext.unit = 'min'
        ext.interval_display = ""
        ext.item_count = 0
        ext.response_count = 0
        ext.logger = Mock()
        return ext

    @pytest.mark.asyncio
    async def test_get_pending_count_stream_queue(self):
        """Stream 队列 → 返回 pending 数"""
        ext = self._make_extension()
        inner_queue = AsyncMock()
        inner_queue.pending_info = AsyncMock(return_value={"pending": 5, "total": 5})
        ext.stats.crawler.engine.scheduler.queue_manager._queue = inner_queue

        result = await ext._get_pending_count()
        assert result == 5

    @pytest.mark.asyncio
    async def test_get_pending_count_memory_queue(self):
        """内存队列（无 pending_info）→ 返回 0"""
        ext = self._make_extension()
        inner_queue = Mock(spec=[])  # 无 pending_info 方法
        ext.stats.crawler.engine.scheduler.queue_manager._queue = inner_queue

        result = await ext._get_pending_count()
        assert result == 0

    @pytest.mark.asyncio
    async def test_get_pending_count_no_queue(self):
        """_queue 为 None → 返回 0"""
        ext = self._make_extension()
        ext.stats.crawler.engine.scheduler.queue_manager._queue = None

        result = await ext._get_pending_count()
        assert result == 0

    def test_log_format_with_pending(self):
        """pending > 0 → 日志包含 Pending 字段"""
        ext = self._make_extension()
        ext._log_interval_stats(
            last_item_count=10, last_response_count=20,
            item_rate=5, response_rate=10, queue_size=3,
            bp_active=False, bp_delay=0.0, bp_util=0.3, bp_score=0.0, bp_level='normal',
            iteration=1, pending_count=7,
        )
        log_msg = ext.logger.info.call_args[0][0]
        assert "Pending: 7" in log_msg

    def test_log_format_without_pending(self):
        """pending = 0 → 日志不含 Pending 字段"""
        ext = self._make_extension()
        ext._log_interval_stats(
            last_item_count=10, last_response_count=20,
            item_rate=5, response_rate=10, queue_size=3,
            bp_active=False, bp_delay=0.0, bp_util=0.3, bp_score=0.0, bp_level='normal',
            iteration=1, pending_count=0,
        )
        log_msg = ext.logger.info.call_args[0][0]
        assert "Pending" not in log_msg

    def test_debug_log_includes_pending(self):
        """pending > 0 → debug 日志包含 pending=N"""
        ext = self._make_extension()
        ext._log_interval_stats(
            last_item_count=10, last_response_count=20,
            item_rate=5, response_rate=10, queue_size=3,
            bp_active=False, bp_delay=0.0, bp_util=0.3, bp_score=0.0, bp_level='normal',
            iteration=1, pending_count=12,
        )
        debug_msg = ext.logger.debug.call_args[0][0]
        assert "pending=12" in debug_msg


# ========================================================================
# 6. default_settings 配置项
# ========================================================================

class TestXclaimSettings:
    """配置项存在性和默认值测试"""

    def test_settings_exist(self):
        from crawlo.settings.default_settings import (
            DISTRIBUTED_IDLE_XCLAIM_SCAN_INTERVAL,
            DISTRIBUTED_IDLE_XCLAIM_MIN_IDLE,
            DISTRIBUTED_IDLE_XCLAIM_BATCH,
        )
        assert DISTRIBUTED_IDLE_XCLAIM_SCAN_INTERVAL == 15
        assert DISTRIBUTED_IDLE_XCLAIM_MIN_IDLE == 120
        assert DISTRIBUTED_IDLE_XCLAIM_BATCH == 200

    def test_engine_reads_config(self):
        """Engine._init_configs 读取配置（通过 settings dict 注入）"""
        # 直接验证 safe_get_config 逻辑，不完整初始化 Engine
        from crawlo.utils.misc import safe_get_config
        settings = {
            'DISTRIBUTED_IDLE_XCLAIM_SCAN_INTERVAL': 30,
            'DISTRIBUTED_IDLE_XCLAIM_MIN_IDLE': 60,
            'DISTRIBUTED_IDLE_XCLAIM_BATCH': 100,
        }
        assert safe_get_config(settings, 'DISTRIBUTED_IDLE_XCLAIM_SCAN_INTERVAL', 15, int) == 30
        assert safe_get_config(settings, 'DISTRIBUTED_IDLE_XCLAIM_MIN_IDLE', 120, int) == 60
        assert safe_get_config(settings, 'DISTRIBUTED_IDLE_XCLAIM_BATCH', 200, int) == 100

    def test_engine_defaults_when_missing(self):
        """settings 缺失配置项 → 使用默认值"""
        from crawlo.utils.misc import safe_get_config
        assert safe_get_config({}, 'DISTRIBUTED_IDLE_XCLAIM_SCAN_INTERVAL', 15, int) == 15
        assert safe_get_config({}, 'DISTRIBUTED_IDLE_XCLAIM_MIN_IDLE', 120, int) == 120
        assert safe_get_config({}, 'DISTRIBUTED_IDLE_XCLAIM_BATCH', 200, int) == 200
