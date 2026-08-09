#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
Engine 分布式协调子模块（组合模式，非 Mixin）

DistributedCoordinator 封装了 Engine 中所有与「distributed 模式」强相关的状态机方法，
避免 Engine 主骨架承载过多职责。

组合模式：DistributedCoordinator 通过持有 Engine 实例的引用（弱语义，不参与 Engine MRO），
可以访问 Engine 的所有 public / 受保护属性（scheduler / _cluster_state / logger 等）。
Engine 主骨架保留同名薄代理方法（`return self._distributed.check_control_state()`），
对外方法签名 100% 兼容。

迁出的方法：
- _check_control_state()        → check_control_state()
- _handle_distributed_idle()    → handle_distributed_idle()
- _try_claim_stale_pending()    → try_claim_stale_pending()
"""
from __future__ import annotations

import time
from typing import TYPE_CHECKING

from crawlo.utils.misc import safe_get_config

if TYPE_CHECKING:
    from crawlo.core.engine import Engine


class DistributedCoordinator:
    """分布式模式的协调器（组合持有 Engine）。

    处理 control:state 检查、idle 超时退出、主动 XCLAIM 扫描回收三类分布式专属动作。
    独立的好处：
    1. 所有分布式逻辑集中在一个文件，修改不影响 standalone/auto 代码路径；
    2. 单元测试可以 mock 整个 DistributedCoordinator，不再需要真的 set up Redis；
    3. 将来如果改分布式算法（比如从 Stream 改为 Raft 片段），改动范围可控。
    """

    def __init__(self, engine: "Engine"):
        self.engine = engine
        # 别名，减少 self.engine.xxx 的重复
        self._cluster_state = engine._cluster_state
        self._scheduler_ref = lambda: engine.scheduler  # 懒获取，scheduler 启动后才非 None
        self._logger = engine.logger
        self._settings = engine.settings
        self._running_ref = lambda: engine.running
        self._request_available_ref = lambda: engine._request_available

        # 直接读 Engine 上的 idle 配置（由 Engine._init_configs 初始化），
        # 不再复制一份配置，保持单一 source of truth。
        self._idle_timeout = lambda: engine._worker_idle_timeout
        self._xclaim_scan_interval = lambda: engine._distributed_idle_xclaim_scan_interval
        self._xclaim_min_idle = lambda: engine._distributed_idle_xclaim_min_idle
        self._xclaim_batch = lambda: engine._distributed_idle_xclaim_batch

        # idle 状态由 Engine 持有（主循环也要读写），这里仅做 alias
        self._idle_since_ref = lambda s=None, g=None: (
            (engine._idle_since if s is None else setattr(engine, "_idle_since", s)),
            (engine._idle_scan_counter if g is None else setattr(engine, "_idle_scan_counter", g)),
        )

    # ------------------------------------------------------------------
    # control state（对应旧 _check_control_state）
    # ------------------------------------------------------------------
    async def check_control_state(self) -> bool:
        """检查集群控制状态，返回 True 继续运行。

        包含 P3-B-02 的「方案 B」自动修复：
        - 若 settings.CLUSTER_AUTO_CLEAR_SHUTDOWN_ON_START=True（默认）
        - 且 control:state == shutdown 持久化残留
        - 且 registry 中没有其他活跃 Worker（即上次运行异常退出）
        → 自动把 control:state 重置为 running，避免本次启动即退出。
        """
        try:
            if self._cluster_state.dynamic_config is None:
                return True
            state = await self._cluster_state.dynamic_config.get_control_state()
            if state == "paused":
                self._cluster_state.paused = True
            elif state == "running":
                self._cluster_state.paused = False
            elif state == "shutdown":
                auto_clear = safe_get_config(
                    self._settings, 'CLUSTER_AUTO_CLEAR_SHUTDOWN_ON_START', True, bool
                )
                registry = getattr(self._cluster_state, 'registry', None)
                if auto_clear and registry is not None:
                    active_workers = await registry.get_active_workers()
                    others_alive = [
                        w for w in active_workers
                        if w.get('id') != self._cluster_state.worker_id
                    ]
                    if not others_alive:
                        self._logger.warning(
                            "[AutoFix P3-B-02] 检测到 control:state = shutdown 残留，"
                            f"但 registry 中只有 {len(active_workers)} 个活跃 Worker（本 Worker 自己）。"
                            " 已自动重置 control:state → running，"
                            "避免上次异常退出导致本次启动即退出。"
                        )
                        await self._cluster_state.dynamic_config.resume_spider()
                        self._cluster_state.paused = False
                        return True

                self._logger.warning("Persistent shutdown state detected, exiting")
                self.engine.running = False
                return False
        except Exception as e:
            # 检查代码出异常不应影响 run_mode != distributed 的路径
            self._logger.debug(f"check_control_state error (harmless): {e}")
        return True

    # ------------------------------------------------------------------
    # idle 状态机 + 主动 XCLAIM 扫描（对应旧 _handle_distributed_idle）
    # ------------------------------------------------------------------
    async def handle_distributed_idle(self, idle_count: int) -> bool:
        """分布式模式下的空闲处理，返回 True 表示应退出。

        集成主动 XCLAIM 扫描（双层回收的主动层）：
        - 累计 idle 时间达到阈值后，扫描 stale pending 消息并重新入队
        - 回收到消息时重置 idle 计时器，避免在新任务消费前超时退出
        """
        engine = self.engine
        idle_timeout = self._idle_timeout()
        if idle_timeout > 0:
            if engine._idle_since is not None:
                remaining = idle_timeout - (time.monotonic() - engine._idle_since)
            else:
                remaining = idle_timeout
            if remaining <= 0:
                self._logger.info(f"Worker idle for {idle_timeout}s, exiting")
                return True
        else:
            remaining = 30.0

        wait_timeout = min(30.0, max(1.0, remaining))
        scan_start = time.monotonic()
        scheduler = self._scheduler_ref()
        request = await scheduler.next_request_blocking(timeout=wait_timeout) if scheduler else None
        actual_wait = time.monotonic() - scan_start

        if request:
            engine._idle_since = None
            engine._idle_scan_counter = 0.0
            engine._create_background_task(engine._crawl(request))
        else:
            if engine._idle_since is None:
                engine._idle_since = time.monotonic()

            engine._idle_scan_counter += actual_wait
            if engine._idle_scan_counter >= self._xclaim_scan_interval():
                engine._idle_scan_counter = 0.0
                # queue/xclaim/scan_runs Counter（真的触发 scan 时 +1）
                self._inc_stats_counter('queue/xclaim/scan_runs', 1)
                claimed = await self.try_claim_stale_pending()
                # queue/xclaim/recovered_total Counter（主路径记录）
                if claimed > 0:
                    self._inc_stats_counter('queue/xclaim/recovered_total', claimed)
                    engine._idle_since = None

            if idle_timeout > 0 and engine._idle_since is not None:
                if time.monotonic() - engine._idle_since >= idle_timeout:
                    self._logger.info(
                        f"Distributed worker idle for {idle_timeout}s, exiting"
                    )
                    return True
        return False

    # ------------------------------------------------------------------
    # 统计埋点 helper（fail-safe：stats 缺失或异常直接忽略）
    # ------------------------------------------------------------------

    def _inc_stats_counter(self, key: str, count: int = 1) -> None:
        """向 StatsCollector.inc_value 写入 Counter，任一环缺失都静默忽略。"""
        try:
            if count <= 0:
                return
            crawler = getattr(self.engine, 'crawler', None)
            if crawler is None:
                return
            stats = getattr(crawler, 'stats', None)
            if stats is None:
                return
            stats.inc_value(key, count=count)
        except Exception:
            pass

    def _set_stats_gauge(self, key: str, value: float) -> None:
        try:
            crawler = getattr(self.engine, 'crawler', None)
            if crawler is None:
                return
            stats = getattr(crawler, 'stats', None)
            if stats is None:
                return
            stats.set_value(key, value)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # XCLAIM 主动扫描（对应旧 _try_claim_stale_pending）
    # ------------------------------------------------------------------
    async def try_claim_stale_pending(self) -> int:
        """主动扫描并回收 stale pending 消息（分布式 idle 期间调用）。

        通过 scheduler.queue_manager._queue 访问底层 RedisStreamQueue，
        调用其 claim_stale_pending 方法将 stale 消息重新入队。

        Returns:
            成功重新入队的消息数（0 表示无可回收或非 Stream 队列）
        """
        try:
            scheduler = self._scheduler_ref()
            queue_manager = getattr(scheduler, 'queue_manager', None)
            if queue_manager is None:
                return 0
            inner = getattr(queue_manager, '_queue', None)
            if inner is None or not hasattr(inner, 'claim_stale_pending'):
                return 0
            claimed = await inner.claim_stale_pending(
                min_idle_sec=self._xclaim_min_idle(),
                count=self._xclaim_batch(),
            )
            if claimed > 0:
                self._logger.info(
                    f"Actively claimed {claimed} stale pending tasks during idle, "
                    f"re-enqueued for processing"
                )
                self._request_available_ref().set()
            return claimed
        except Exception as e:
            self._logger.debug(f"Stale pending scan failed: {e}")
            return 0


__all__ = ['DistributedCoordinator']
