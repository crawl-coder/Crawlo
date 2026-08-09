"""
Phase 5: ClusterMixin 覆盖率补全测试（面向 P1-4 门槛 25%）

覆盖 _init_cluster 早退路径、集群后台任务启停、控制/配置消息、
Leader 锁获取/释放、协调退出条件、优雅关闭与在途任务 drain。
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch

from crawlo.cluster.coordinator import ClusterMixin, ClusterState


def _make_mixin(settings=None):
    mixin = ClusterMixin.__new__(ClusterMixin)
    mixin.settings = settings if settings is not None else {}
    mixin.running = True
    mixin.scheduler = None
    mixin._background_tasks = set()
    mixin._start_requests_source = None
    mixin.logger = Mock()
    mixin._logger = Mock()
    mixin._cluster_state = ClusterState()
    return mixin


class TestInitClusterEarlyReturns:
    """_init_cluster 非分布式/非 Redis 队列时直接返回"""

    async def _run(self, run_mode='standalone', queue_type='memory', **overrides):
        settings = {'RUN_MODE': run_mode, 'QUEUE_TYPE': queue_type}
        settings.update(overrides)
        mixin = _make_mixin(settings)
        await mixin._init_cluster()
        return mixin

    @pytest.mark.asyncio
    async def test_standalone_returns(self):
        mixin = await self._run(run_mode='standalone', queue_type='redis_stream')
        assert mixin._cluster_state.worker_id is None

    @pytest.mark.asyncio
    async def test_distributed_non_redis_queue_returns(self):
        mixin = await self._run(run_mode='distributed', queue_type='memory')
        assert mixin._cluster_state.worker_id is None


class TestStartClusterTasks:
    """_start_cluster_tasks 启动/跳过后台任务"""

    @pytest.mark.asyncio
    async def test_no_worker_id_returns(self):
        mixin = _make_mixin()
        mixin._cluster_state.heartbeat = AsyncMock()
        await mixin._start_cluster_tasks()
        mixin._cluster_state.heartbeat.start.assert_not_called()

    @pytest.mark.asyncio
    async def test_starts_all_tasks(self):
        mixin = _make_mixin()
        state = mixin._cluster_state
        state.worker_id = 'worker-1'
        state.heartbeat = Mock()
        state.heartbeat.start = AsyncMock(return_value=Mock())
        state.messenger = AsyncMock()
        state.failover = Mock()
        state.coordinated_shutdown_enabled = True
        state.dynamic_config = Mock()

        await mixin._start_cluster_tasks()

        state.heartbeat.start.assert_awaited_once()
        state.messenger.start.assert_awaited_once()
        state.messenger.subscribe.assert_any_await('control', mixin._on_control_message)
        state.messenger.subscribe.assert_any_await('config', mixin._on_config_message)
        assert state.failover_task is not None
        assert state.leader_shutdown_task is not None

        # 清理后台任务
        state.failover_task.cancel()
        state.leader_shutdown_task.cancel()
        await asyncio.gather(state.failover_task, state.leader_shutdown_task, return_exceptions=True)


class TestControlAndConfigMessages:
    """控制消息与配置消息处理"""

    @pytest.mark.asyncio
    async def test_pause_resume_shutdown(self):
        mixin = _make_mixin()
        await mixin._on_control_message({'action': 'pause'})
        assert mixin._cluster_state.paused is True
        await mixin._on_control_message({'action': 'resume'})
        assert mixin._cluster_state.paused is False
        await mixin._on_control_message({'action': 'shutdown'})
        assert mixin.running is False
        await mixin._on_control_message({'action': 'unknown'})

    @pytest.mark.asyncio
    async def test_rate_limit_message(self):
        mixin = _make_mixin()
        mixin.scheduler = Mock()
        mixin._cluster_state.rate_limiter = AsyncMock()
        await mixin._on_config_message({'action': 'rate_limit', 'domain': 'x.com', 'rate': 5})
        mixin._cluster_state.rate_limiter.set_rate.assert_awaited_once_with('x.com', 5)

    @pytest.mark.asyncio
    async def test_seed_urls_message(self):
        mixin = _make_mixin()
        mixin.scheduler = Mock()
        mixin.scheduler.enqueue_request = AsyncMock()
        mixin._cluster_state.dynamic_config = AsyncMock()
        mixin._cluster_state.dynamic_config.pop_seed_urls = AsyncMock(
            return_value=['http://a.com', 'http://b.com']
        )
        await mixin._on_config_message({'action': 'seed_urls'})
        assert mixin.scheduler.enqueue_request.await_count == 2


class TestLeaderLock:
    """Leader 锁获取/释放"""

    @pytest.mark.asyncio
    async def test_acquire_no_lock_returns_false(self):
        mixin = _make_mixin()
        mixin._cluster_state.leader_lock = None
        assert await mixin._try_acquire_leader_lock(30) is False

    @pytest.mark.asyncio
    async def test_acquire_extend_success(self):
        mixin = _make_mixin()
        lock = Mock()
        lock.acquired = True
        lock.holder_id = 'me'
        lock.extend = AsyncMock(return_value=True)
        mixin._cluster_state.leader_lock = lock
        assert await mixin._try_acquire_leader_lock(30) is True
        lock.extend.assert_awaited_once_with(30)

    @pytest.mark.asyncio
    async def test_acquire_fresh(self):
        mixin = _make_mixin()
        lock = Mock()
        lock.acquired = False
        lock.acquire = AsyncMock(return_value='lock-token')
        mixin._cluster_state.leader_lock = lock
        assert await mixin._try_acquire_leader_lock(30) is True
        lock.acquire.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_acquire_exception_returns_false(self):
        mixin = _make_mixin()
        lock = Mock()
        lock.acquired = False
        lock.acquire = AsyncMock(side_effect=RuntimeError('redis down'))
        mixin._cluster_state.leader_lock = lock
        assert await mixin._try_acquire_leader_lock(30) is False

    @pytest.mark.asyncio
    async def test_release_no_lock(self):
        mixin = _make_mixin()
        mixin._cluster_state.leader_lock = None
        await mixin._release_leader_lock()  # 不抛异常即可

    @pytest.mark.asyncio
    async def test_release_calls_release(self):
        mixin = _make_mixin()
        lock = Mock()
        lock.release = AsyncMock()
        mixin._cluster_state.leader_lock = lock
        await mixin._release_leader_lock()
        lock.release.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_release_swallows_exception(self):
        mixin = _make_mixin()
        lock = Mock()
        lock.release = AsyncMock(side_effect=RuntimeError('boom'))
        mixin._cluster_state.leader_lock = lock
        await mixin._release_leader_lock()  # 不抛异常即可


class TestLeaderShutdownConditions:
    """协调退出条件检查"""

    @pytest.mark.asyncio
    async def test_start_requests_source_not_exhausted(self):
        mixin = _make_mixin()
        mixin._start_requests_source = object()
        assert await mixin._check_leader_shutdown_conditions() is False

    @pytest.mark.asyncio
    async def test_queue_not_empty(self):
        mixin = _make_mixin()
        mixin.scheduler = Mock()
        mixin.scheduler.async_idle = AsyncMock(return_value=False)
        assert await mixin._check_leader_shutdown_conditions() is False

    @pytest.mark.asyncio
    async def test_background_tasks_pending(self):
        mixin = _make_mixin()
        mixin._background_tasks.add(Mock())
        assert await mixin._check_leader_shutdown_conditions() is False

    @pytest.mark.asyncio
    async def test_worker_still_processing(self):
        mixin = _make_mixin()
        mixin.scheduler = Mock()
        mixin.scheduler.async_idle = AsyncMock(return_value=True)
        mixin._cluster_state.worker_id = 'me'
        registry = Mock()
        registry.get_active_workers = AsyncMock(return_value=[
            {'id': 'me', 'tasks_processing': 0},
            {'id': 'other', 'tasks_processing': 2},
        ])
        mixin._cluster_state.registry = registry
        assert await mixin._check_leader_shutdown_conditions() is False

    @pytest.mark.asyncio
    async def test_registry_error_returns_false(self):
        mixin = _make_mixin()
        mixin.scheduler = Mock()
        mixin.scheduler.async_idle = AsyncMock(return_value=True)
        registry = Mock()
        registry.get_active_workers = AsyncMock(side_effect=RuntimeError('redis down'))
        mixin._cluster_state.registry = registry
        assert await mixin._check_leader_shutdown_conditions() is False

    @pytest.mark.asyncio
    async def test_all_idle_returns_true(self):
        mixin = _make_mixin()
        mixin.scheduler = Mock()
        mixin.scheduler.async_idle = AsyncMock(return_value=True)
        mixin._cluster_state.worker_id = 'me'
        registry = Mock()
        registry.get_active_workers = AsyncMock(return_value=[
            {'id': 'me', 'tasks_processing': 0},
            {'id': 'other', 'tasks_processing': 0},
        ])
        mixin._cluster_state.registry = registry
        # 2s 重检等待：接受真实 sleep
        assert await mixin._check_leader_shutdown_conditions() is True


class TestShutdownAndDrain:
    """优雅关闭与在途任务 drain"""

    @pytest.mark.asyncio
    async def test_shutdown_no_worker_id(self):
        mixin = _make_mixin()
        await mixin._shutdown_cluster()

    @pytest.mark.asyncio
    async def test_shutdown_full_path(self):
        mixin = _make_mixin()
        state = mixin._cluster_state
        state.worker_id = 'worker-1'
        state.registry = AsyncMock()
        state.messenger = AsyncMock()
        state.heartbeat = AsyncMock()
        await mixin._shutdown_cluster()
        state.registry.update_status.assert_awaited_once()
        state.messenger.stop.assert_awaited_once()
        state.heartbeat.stop.assert_awaited_once()
        state.registry.deregister.assert_awaited_once_with('worker-1')

    @pytest.mark.asyncio
    async def test_drain_no_inflight(self):
        mixin = _make_mixin()
        await mixin._drain_inflight_tasks()

    @pytest.mark.asyncio
    async def test_drain_completes_tasks(self):
        mixin = _make_mixin()

        async def slow():
            await asyncio.sleep(0.01)

        task = asyncio.create_task(slow())
        mixin._background_tasks.add(task)
        await mixin._drain_inflight_tasks()
        assert task.done()

    @pytest.mark.asyncio
    async def test_drain_timeout_cancels(self):
        mixin = _make_mixin({'CLUSTER_GRACEFUL_SHUTDOWN_TIMEOUT': 1})

        async def slow():
            await asyncio.sleep(10)

        task = asyncio.create_task(slow())
        mixin._background_tasks.add(task)
        await mixin._drain_inflight_tasks()
        assert task.done()
        assert task.cancelled()


class TestFailoverLoop:
    """故障检测循环（单轮迭代）"""

    @pytest.mark.asyncio
    async def test_loop_with_dead_workers(self):
        mixin = _make_mixin()
        state = mixin._cluster_state
        state.failover = Mock()
        state.failover.failover_interval = 0.01

        async def check_and_recover():
            mixin.running = False  # 单轮后退出
            return {'dead_workers': 2}

        state.failover.check_and_recover = check_and_recover
        mixin._inc_stats_counter = Mock()
        await mixin._failover_loop()
        mixin._inc_stats_counter.assert_called_once_with('cluster/worker/heartbeat_lost', 2)

    @pytest.mark.asyncio
    async def test_loop_exception_continues(self):
        mixin = _make_mixin()
        state = mixin._cluster_state
        state.failover = Mock()
        state.failover.failover_interval = 0.01
        calls = {'n': 0}

        async def check_and_recover():
            calls['n'] += 1
            if calls['n'] == 1:
                raise RuntimeError('boom')
            mixin.running = False
            return {}

        state.failover.check_and_recover = check_and_recover
        await mixin._failover_loop()
        assert calls['n'] == 2


class TestLeaderShutdownLoop:
    """Leader 协调退出循环"""

    @pytest.mark.asyncio
    async def test_no_dynamic_config_returns(self):
        mixin = _make_mixin()
        mixin._cluster_state.dynamic_config = None
        await mixin._leader_shutdown_loop()

    @pytest.mark.asyncio
    async def test_shutdown_path(self):
        mixin = _make_mixin()
        state = mixin._cluster_state
        state.dynamic_config = AsyncMock()
        state.dynamic_config.get_control_state = AsyncMock(return_value='running')
        state.dynamic_config.shutdown_cluster = AsyncMock()
        state.leader_lock = Mock()

        mixin._try_acquire_leader_lock = AsyncMock(return_value=True)
        mixin._check_leader_shutdown_conditions = AsyncMock(return_value=True)

        await mixin._leader_shutdown_loop()

        state.dynamic_config.shutdown_cluster.assert_awaited_once_with(cleanup=False)
        assert mixin.running is False

    @pytest.mark.asyncio
    async def test_control_state_shutdown_breaks(self):
        mixin = _make_mixin()
        state = mixin._cluster_state
        state.dynamic_config = AsyncMock()
        state.dynamic_config.get_control_state = AsyncMock(return_value='shutdown')
        state.leader_lock = Mock()
        mixin._try_acquire_leader_lock = AsyncMock(return_value=True)

        await mixin._leader_shutdown_loop()

        assert mixin.running is False
