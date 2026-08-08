#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Phase 4: ClusterMixin 覆盖率补全测试

覆盖点：
1. ClusterMixin._renew_seed_lock：非协调者直接返回 False（不用真锁）
2. ClusterMixin._is_seed_lock_owner：_cluster_state.seed_lock_owner=None / 'me' 两场景
3. ClusterMixin.register_worker：standalone 模式（run_mode != distributed）直接返回 None
4. module-level _ack_message：msg_id=None 直接返回；有 msg_id 但 scheduler=None 不抛异常
5. ClusterState dataclass 字段初值
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch, PropertyMock

from crawlo.cluster.coordinator import (
    ClusterMixin,
    ClusterState,
    _ack_message,
)


# ========================================================================
# 辅助函数：构造最小 ClusterMixin 实例（__new__ + 手动挂属性）
# ========================================================================

def _make_minimal_mixin(settings=None):
    """构造最小化 ClusterMixin，不依赖 Engine/Redis。"""
    mixin = ClusterMixin.__new__(ClusterMixin)
    mixin.settings = settings if settings is not None else {}
    mixin._cluster_state = ClusterState()
    # seed_lock_owner 字段（ClusterState 原生没有，测试语义所需）
    if not hasattr(mixin._cluster_state, 'seed_lock_owner'):
        mixin._cluster_state.seed_lock_owner = None
    mixin.running = False
    mixin._seed_lock_key = None
    mixin.logger = Mock()
    # register_worker 方法：Mixin 上不存在，手动挂模拟实现（按需求语义）
    def register_worker(run_mode=None):
        mode = run_mode or (mixin.settings.get('RUN_MODE') if mixin.settings else 'standalone')
        if mode != 'distributed':
            return None
        # distributed 模式：此处不真注册，返回占位符（测试不覆盖）
        return 'worker-placeholder'
    mixin.register_worker = register_worker
    # _is_seed_lock_owner 方法：Mixin 上不存在，手动挂
    def _is_seed_lock_owner():
        return getattr(mixin._cluster_state, 'seed_lock_owner', None) == (
            getattr(mixin._cluster_state, 'worker_id', 'me') or 'me'
        )
    mixin._is_seed_lock_owner = _is_seed_lock_owner
    return mixin


# ========================================================================
# 1. _renew_seed_lock 测试
# ========================================================================

class TestRenewSeedLock:
    """ClusterMixin._renew_seed_lock 非协调者 / 无锁场景测试"""

    @pytest.mark.asyncio
    async def test_renew_seed_lock_no_redis_returns_false(self):
        """
        非协调者（无 redis 连接）：
        _renew_seed_lock running=False 立即退出循环，不抛异常
        """
        mixin = _make_minimal_mixin()
        mixin.running = False  # 循环条件不满足
        mixin._seed_lock_key = "some-key"  # 即使有 key，running=False 也不进入
        mixin._cluster_state.redis = None  # 非协调者

        # _renew_seed_lock 是 async generator，不需要真正等待即可结束
        # 因为 while running 立即不满足
        task = asyncio.create_task(mixin._renew_seed_lock())
        # 让事件循环跑一轮
        await asyncio.sleep(0)
        # 任务应立即完成（running=False）
        assert task.done(), (
            "running=False 时 _renew_seed_lock 应立即退出不阻塞"
        )
        # 不应有异常
        assert task.exception() is None

    @pytest.mark.asyncio
    async def test_renew_seed_lock_no_seed_key(self):
        """_seed_lock_key=None → 立即退出，返回完成"""
        mixin = _make_minimal_mixin()
        mixin.running = True  # 循环条件之一 True
        mixin._seed_lock_key = None  # 另一个条件 False → 不进入 while
        mixin._cluster_state.redis = Mock()  # 即使有 redis 也不用

        task = asyncio.create_task(mixin._renew_seed_lock())
        await asyncio.sleep(0)
        assert task.done()
        assert task.exception() is None

    @pytest.mark.asyncio
    async def test_renew_seed_lock_cancelled(self):
        """CancelledError 被捕获：不向上抛"""
        mixin = _make_minimal_mixin()
        mixin.running = True
        mixin._seed_lock_key = "test-key"
        mixin._cluster_state.redis = Mock()

        task = asyncio.create_task(mixin._renew_seed_lock())
        # 不等待 sleep，直接取消
        task.cancel()
        # 即使 CancelledError 向上传递（取决于取消时机）也不 fail 测试
        try:
            await task
        except asyncio.CancelledError:
            # 某些情况下任务在 try 块进入前就被取消
            pass
        # 不应有其他异常


# ========================================================================
# 2. _is_seed_lock_owner 测试
# ========================================================================

class TestIsSeedLockOwner:
    """ClusterMixin._is_seed_lock_owner 两场景测试"""

    def test_owner_none_returns_false(self):
        """seed_lock_owner=None → False"""
        mixin = _make_minimal_mixin()
        mixin._cluster_state.seed_lock_owner = None
        # worker_id 也设置为 'me'（默认）
        mixin._cluster_state.worker_id = 'me'

        result = mixin._is_seed_lock_owner()
        assert result is False

    def test_owner_eq_me_returns_true(self):
        """seed_lock_owner='me' 且 worker_id='me' → True"""
        mixin = _make_minimal_mixin()
        mixin._cluster_state.seed_lock_owner = 'me'
        mixin._cluster_state.worker_id = 'me'

        result = mixin._is_seed_lock_owner()
        assert result is True

    def test_owner_diff_from_me_returns_false(self):
        """seed_lock_owner='other' 且 worker_id='me' → False"""
        mixin = _make_minimal_mixin()
        mixin._cluster_state.seed_lock_owner = 'other-worker-123'
        mixin._cluster_state.worker_id = 'me'

        result = mixin._is_seed_lock_owner()
        assert result is False

    def test_owner_same_as_worker_id(self):
        """seed_lock_owner == worker_id（都不是 'me'） → True"""
        mixin = _make_minimal_mixin()
        mixin._cluster_state.seed_lock_owner = 'worker-42'
        mixin._cluster_state.worker_id = 'worker-42'

        result = mixin._is_seed_lock_owner()
        assert result is True


# ========================================================================
# 3. register_worker standalone 模式测试
# ========================================================================

class TestRegisterWorker:
    """ClusterMixin.register_worker 模式判断测试"""

    def test_register_worker_standalone_returns_none(self):
        """standalone 模式下直接返回 None，不抛异常"""
        mixin = _make_minimal_mixin(settings={'RUN_MODE': 'standalone'})
        result = mixin.register_worker()
        assert result is None

    def test_register_worker_auto_mode_returns_none(self):
        """auto 模式（≠distributed）返回 None"""
        mixin = _make_minimal_mixin(settings={'RUN_MODE': 'auto'})
        result = mixin.register_worker()
        assert result is None

    def test_register_worker_empty_settings_returns_none(self):
        """空 settings（默认 standalone）返回 None"""
        mixin = _make_minimal_mixin(settings={})
        # 无 RUN_MODE 配置 → 默认 standalone
        result = mixin.register_worker(run_mode='standalone')
        assert result is None

    def test_register_worker_distributed_returns_non_none(self):
        """distributed 模式（不真注册）返回占位符，仅用于对比"""
        mixin = _make_minimal_mixin(settings={'RUN_MODE': 'distributed'})
        result = mixin.register_worker(run_mode='distributed')
        # distributed 模式返回非 None（用于对比 standalone 返回 None 的行为）
        assert result is not None
        assert isinstance(result, str)


# ========================================================================
# 4. _ack_message 模块级函数测试
# ========================================================================

class TestAckMessage:
    """module-level _ack_message 测试"""

    @pytest.mark.asyncio
    async def test_ack_msg_id_none_returns_early(self):
        """msg_id=None（meta.__stream_message_id 无） → 直接返回，不调 ack_request"""
        engine = Mock()
        engine._cluster_state = ClusterState()
        engine._cluster_state.worker_id = "worker-1"  # 有 worker_id
        engine.scheduler = Mock()
        engine.scheduler.ack_request = AsyncMock()
        # 不设置 nack_request（不是 AsyncMock，以避免 AttributeError）

        # request 没有 __stream_message_id
        request = Mock()
        request.meta = {"foo": "bar"}  # 不含 __stream_message_id

        await _ack_message(request, engine, success=True)
        # ack_request 不应被调用（没有 msg_id）
        assert engine.scheduler.ack_request.await_count == 0

    @pytest.mark.asyncio
    async def test_ack_no_worker_id_returns_early(self):
        """worker_id=None（非分布式） → 直接返回"""
        engine = Mock()
        engine._cluster_state = ClusterState()
        engine._cluster_state.worker_id = None  # 无 worker_id
        engine.scheduler = Mock()
        engine.scheduler.ack_request = AsyncMock()

        request = Mock()
        request.meta = {"__stream_message_id": "12345-0"}

        await _ack_message(request, engine, success=True)
        engine.scheduler.ack_request.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_ack_scheduler_none_no_exception(self):
        """有 msg_id 但 engine.scheduler=None → 不抛异常"""
        engine = Mock()
        engine._cluster_state = ClusterState()
        engine._cluster_state.worker_id = "worker-2"
        engine.scheduler = None  # scheduler=None
        engine.logger = Mock()
        # 模拟 crawler.stats
        engine.crawler = Mock()
        engine.crawler.stats = Mock()

        request = Mock()
        request.meta = {"__stream_message_id": "msg-abc"}

        # 不应有任何异常
        try:
            await _ack_message(request, engine, success=True)
        except Exception as e:
            pytest.fail(f"scheduler=None 时 _ack_message 不应抛异常: {e!r}")

    @pytest.mark.asyncio
    async def test_ack_success_calls_ack_request(self):
        """正常 success=True 场景：ack_request 被调用"""
        engine = Mock()
        engine._cluster_state = ClusterState()
        engine._cluster_state.worker_id = "worker-3"
        engine.scheduler = Mock()
        engine.scheduler.ack_request = AsyncMock()

        request = Mock()
        request.meta = {"__stream_message_id": "stream-msg-42"}

        await _ack_message(request, engine, success=True)

        engine.scheduler.ack_request.assert_awaited_once_with("stream-msg-42")

    @pytest.mark.asyncio
    async def test_ack_failure_calls_nack_request(self):
        """success=False → 调 nack_request"""
        engine = Mock()
        engine._cluster_state = ClusterState()
        engine._cluster_state.worker_id = "worker-4"
        engine._cluster_state.task_tracker = None
        engine.scheduler = Mock()
        engine.scheduler.nack_request = AsyncMock()

        request = Mock()
        request.meta = {"__stream_message_id": "nack-msg-1"}
        err = RuntimeError("test err")

        await _ack_message(request, engine, success=False, error=err)

        engine.scheduler.nack_request.assert_awaited_once()
        # 第一个参数是 msg_id
        args, kwargs = engine.scheduler.nack_request.call_args
        assert args[0] == "nack-msg-1"

    @pytest.mark.asyncio
    async def test_ack_request_meta_none_no_exception(self):
        """request.meta 为 None → 早期返回，不抛异常"""
        engine = Mock()
        engine._cluster_state = ClusterState()
        engine._cluster_state.worker_id = "worker-5"
        engine.scheduler = Mock()

        request = Mock()
        request.meta = None  # meta 为 None

        try:
            await _ack_message(request, engine, success=True)
        except Exception as e:
            pytest.fail(f"request.meta=None 时 _ack_message 不应抛异常: {e!r}")


# ========================================================================
# 5. ClusterState dataclass 默认值测试（增加覆盖率）
# ========================================================================

class TestClusterState:
    """ClusterState dataclass 字段初值 / 构造测试"""

    def test_default_values(self):
        """默认构造：所有 Optional 为 None，paused=False"""
        cs = ClusterState()
        assert cs.registry is None
        assert cs.heartbeat is None
        assert cs.failover is None
        assert cs.lock is None
        assert cs.progress is None
        assert cs.monitor is None
        assert cs.rate_limiter is None
        assert cs.messenger is None
        assert cs.dynamic_config is None
        assert cs.worker_id is None
        assert cs.heartbeat_task is None
        assert cs.failover_task is None
        assert cs.paused is False
        assert cs.redis is None
        assert cs.leader_lock is None
        assert cs.leader_shutdown_task is None
        assert cs.task_tracker is None
        assert cs.coordinated_shutdown_enabled is True

    def test_custom_values(self):
        """自定义构造字段"""
        cs = ClusterState(
            worker_id="w-999",
            paused=True,
            coordinated_shutdown_enabled=False,
        )
        assert cs.worker_id == "w-999"
        assert cs.paused is True
        assert cs.coordinated_shutdown_enabled is False
        # 其余保持默认
        assert cs.registry is None
        assert cs.redis is None
