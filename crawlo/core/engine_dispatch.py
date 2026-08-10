#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
Engine 调度派发子模块（组合模式）

RequestDispatcher 封装 Engine 的主循环与请求派发逻辑，将「调度算法」从 Engine 骨架中解耦：
- 主循环 _run_main_loop()            → run_main_loop()
- 派发请求 _dispatch_requests()       → dispatch_requests()
- 组件空闲检查 / 退出判断              → check_components_idle() / should_exit() / check_all_idle() / exit_fast()

Engine 主骨架保留同名薄代理方法，对外签名 100% 兼容。
"""
from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Optional

from crawlo.utils.misc import safe_get_config
from crawlo.core.engine_helpers import has_pending_enqueues

if TYPE_CHECKING:
    from crawlo.core.engine import Engine


class RequestDispatcher:
    """请求派发器（组合持有 Engine）。

    负责：
      1. 主爬取循环的「批量取请求 → 派发 → idle 检测 → 退出检查」状态机；
      2. 将请求列表按并发上限派发为 fire-and-forget 的 background 任务；
      3. 所有退出相关的组件 idle 一致性检查（standalone / auto 模式的正常退出判据）。
    """

    def __init__(self, engine: "Engine"):
        self.engine = engine
        self._logger = engine.logger
        self._settings = engine.settings
        self._cluster_state = engine._cluster_state
        # 运行态属性（Engine 主骨架的属性，保持单点存储，Dispatcher 只是代理）
        self._running = lambda: engine.running
        self._start_requests_source = lambda: engine._start_requests_source
        self._request_available = lambda: engine._request_available

    # ------------------------------------------------------------------
    # 主循环（对应旧 Engine._run_main_loop）
    # ------------------------------------------------------------------
    async def run_main_loop(self):
        """主爬取循环：获取请求 → 流控 → 派发 → 空闲检测"""
        engine = self.engine
        loop_count = 0
        last_exit_check = 0
        last_component_states = None
        batch_size = max(engine.task_manager._concurrency_limit, 10)
        idle_count = 0
        max_inflight = engine.task_manager._concurrency_limit + 3
        exit_check_interval, min_ci, max_ci = 10, 5, 20

        while self._running():
            loop_count += 1

            if self._cluster_state.messenger and self._cluster_state.dynamic_config:
                if not await engine._check_control_state():
                    break
                if self._cluster_state.paused:
                    await asyncio.sleep(0.5)
                    continue

            # 批量获取请求
            requests = []
            for _ in range(batch_size):
                if request := await engine._get_next_request():
                    requests.append(request)
                else:
                    break

            if requests:
                idle_count = 0
                await self.dispatch_requests(requests, max_inflight)
                exit_check_interval = min(exit_check_interval + 1, max_ci)
            else:
                idle_count += 1
                run_mode = safe_get_config(self._settings, 'RUN_MODE', 'standalone')
                if run_mode == 'distributed' and self._start_requests_source() is None:
                    if await engine._handle_distributed_idle(idle_count):
                        break
                    continue

                if idle_count == 1:
                    should_exit, last_component_states = await self.should_exit(last_component_states)
                    if should_exit:
                        await asyncio.sleep(0.001)
                        if await self.check_all_idle():
                            break
                    last_exit_check = loop_count
                exit_check_interval = max(exit_check_interval - 1, min_ci)

            if loop_count - last_exit_check >= exit_check_interval:
                should_exit, last_component_states = await self.should_exit(last_component_states)
                if should_exit:
                    break
                last_exit_check = loop_count

            if requests:
                await asyncio.sleep(0.000001)
            else:
                try:
                    await asyncio.wait_for(
                        self._request_available().wait(),
                        timeout=0.5 if idle_count > 10 else 0.1
                    )
                    self._request_available().clear()
                except asyncio.TimeoutError:
                    pass

        self._logger.debug(f"主爬取循环结束，总共执行了 {loop_count} 次")

    # ------------------------------------------------------------------
    # 派发（对应旧 Engine._dispatch_requests）
    # ------------------------------------------------------------------
    async def dispatch_requests(self, requests, max_inflight):
        """派发请求，控制并发流控"""
        engine = self.engine
        self._request_available().clear()
        for req in requests:
            if len(engine._background_tasks) >= max_inflight:
                if not getattr(engine, '_fc_logged', False):
                    self._logger.debug(
                        f"[流控] 在途={len(engine._background_tasks)}/{max_inflight}，等待释放后派发"
                    )
                    engine._fc_logged = True
                while len(engine._background_tasks) >= max_inflight:
                    await asyncio.sleep(0.01)
            else:
                engine._fc_logged = False
            engine._create_background_task(engine._crawl(req))

    # ------------------------------------------------------------------
    # 组件空闲 / 退出判断（对应旧 Engine._check_components_idle 等）
    # ------------------------------------------------------------------
    async def check_components_idle(
        self, include_background: bool = False
    ) -> tuple[bool, bool, bool, bool, bool]:
        """统一检查各组件是否空闲

        Returns:
            (scheduler_idle, downloader_idle, task_manager_done, processor_idle, background_tasks_done)
        """
        engine = self.engine
        scheduler_idle = False
        downloader_idle = False
        task_manager_done = False
        processor_idle = False
        background_tasks_done = False

        if engine.scheduler is not None:
            scheduler_idle = await engine.scheduler.async_idle()
        if engine.downloader is not None:
            downloader_idle = engine.downloader.idle()
        if engine.task_manager is not None:
            task_manager_done = engine.task_manager.all_done()
        if engine.processor is not None:
            processor_idle = await engine.processor.idle_async()
        if include_background:
            background_tasks_done = len(engine._background_tasks) == 0

        return scheduler_idle, downloader_idle, task_manager_done, processor_idle, background_tasks_done

    async def exit_fast(self) -> bool:
        """快速退出检查（4 组件，不含 background_tasks，有 pending enqueue 时不退出）"""
        s, d, t, p, _ = await self.check_components_idle(include_background=False)
        return s and d and t and p and not has_pending_enqueues(self.engine.scheduler)

    async def check_all_idle(self) -> bool:
        """二次确认所有组件是否仍然空闲（用于瞬时空闲误判）"""
        return await self.exit_fast()

    async def should_exit(self, last_component_states=None) -> tuple[bool, Optional[tuple]]:
        """检查是否应该退出（5 组件 + start_requests 判断）

        standalone / auto 模式：队列空 + 所有组件空闲 → 正常退出
        distributed 模式：不因队列空退出，由 BZPOPMIN 超时 + idle_timeout 决定
        """
        engine = self.engine
        run_mode = safe_get_config(self._settings, 'RUN_MODE', 'standalone')
        if run_mode == 'distributed':
            return False, None

        if self._start_requests_source() is None:
            s, d, t, p, bg = await self.check_components_idle(include_background=True)
            current_states = (s, d, t, p, bg)

            if current_states != last_component_states:
                self._logger.debug(
                    f"组件状态变化 - Scheduler: {s}, "
                    f"Downloader: {d}, TaskManager: {t}, "
                    f"Processor: {p}, BackgroundTasks: {bg}"
                )

            if s and d and t and p and bg and not has_pending_enqueues(engine.scheduler):
                self._logger.info("All components are idle, preparing to exit")
                return True, current_states
        else:
            self._logger.debug("start_requests 不为 None，不退出")
            current_states = None

        return False, current_states


__all__ = ['RequestDispatcher']
