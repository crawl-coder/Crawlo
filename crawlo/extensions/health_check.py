#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
Health Check Extension
Monitor crawler health status including response time, error rates etc.
"""
import asyncio
from collections import deque
from datetime import datetime
from typing import Any, Deque, Dict, Optional, Tuple

from crawlo.event import CrawlerEvent
from .monitor.base import BaseMonitorExtension


class HealthCheckExtension(BaseMonitorExtension):
    """
    健康检查扩展
    监控爬虫的健康状态，包括响应时间、错误率等指标
    """

    monitor_id = 'health_check_monitor'
    config_key = 'HEALTH_CHECK_ENABLED'
    default_enabled = True
    extra_events = [
        ('response_received', CrawlerEvent.RESPONSE_RECEIVED),
        ('request_scheduled', CrawlerEvent.REQUEST_SCHEDULED),
    ]

    def __init__(self, crawler: Any):
        super().__init__(crawler)

        self.check_interval = self.settings.get_int('HEALTH_CHECK_INTERVAL', 60)
        self.stats: Dict[str, Any] = {
            'start_time': None,
            'total_requests': 0,
            'total_responses': 0,
            'error_responses': 0,
            'last_check_time': None,
        }

        # filter/duplicate_rps 每秒采样环
        # 每 1s 记录 (timestamp, dedup/count) 快照；用 60s 窗口内 delta/t 算 RPS
        self._dedup_snapshots: Deque[Tuple[float, int]] = deque(maxlen=65)
        # 保存派生 task，在 spider_closed 时统一 cancel，避免 orphan task 在 logger=None 后仍写日志
        self._extra_tasks: list[asyncio.Task] = []

    # ---- 小工具：安全写 logger & 安全生成 task 并挂引用 ----

    def _safe_log(self, level: str, msg: str, *args, **kwargs) -> None:
        """logger=None 时直接吞掉（避免 orphan task 醒来 NoneType has no attr debug/error）。"""
        if self.logger is None:
            return
        getattr(self.logger, level)(msg, *args, **kwargs)

    def _track_task(self, coro) -> Optional[asyncio.Task]:
        try:
            loop = asyncio.get_event_loop()
            if not loop.is_running():
                return None
            t = loop.create_task(coro)
            self._extra_tasks.append(t)

            def _on_done(task, _lst_ref=self._extra_tasks):
                # 注意：_cancel_extra_tasks() 里会直接 clear() 整个 list，
                # 这里用 `if task in lst` 再 remove，避免 list.remove(x) not in list。
                try:
                    if task in _lst_ref:
                        _lst_ref.remove(task)
                except (ValueError, ReferenceError):
                    pass

            t.add_done_callback(_on_done)
            return t
        except RuntimeError:
            return None

    def _cancel_extra_tasks(self) -> None:
        for t in list(self._extra_tasks):
            if not t.done():
                t.cancel()
        # 注意：不直接 clear。task 的 done_callback 里负责安全移除。
        # （如果任务刚被调度又被 cancel，仍然会触发 done_callback。）

    # ---- spider_closed 清理 ----

    def _on_spider_closed_cleanup(self) -> None:
        """取消所有派生 task → 输出最终健康报告 → 清内部缓存。"""
        # 先 cancel 派生 task：_dedup_rps_loop、以及历史遗留的旧 _log 类异步任务
        self._cancel_extra_tasks()

        # 清缓存（break closure→crawler 引用链）
        self._dedup_snapshots.clear()

        async def _log():
            try:
                await self._check_health()
            except asyncio.CancelledError:
                pass
            except Exception as e:
                self.logger.debug("Suppressed exception: %s", e)
        self._track_task(_log())

    # ---- 事件回调 ----

    async def spider_opened(self) -> None:
        """爬虫启动时记录起始时间，并启动 duplicate_rps 采样循环"""
        if not self.enabled:
            return
        self.stats['start_time'] = datetime.now()
        # 启动每秒一次的 duplicate_rps 采样任务（fail-safe，异常不影响主循环）
        self._track_task(self._dedup_rps_loop())
        await super().spider_opened()

    async def _dedup_rps_loop(self) -> None:
        """每秒拍一张 dedup 计数快照并写入 filter/duplicate_rps gauge。"""
        import time as _time
        while True:
            try:
                await asyncio.sleep(1.0)
                # 直接用 StatsBackend 接口（get_value / set_value），避免 backend 差异。
                crawler_stats = getattr(self.crawler, 'stats', None)
                if crawler_stats is None:
                    continue
                # dedup/new_count：Pipeline 层新 item 接受数（随 item 处理持续增加）。
                # {FilterClass}/filtered_count：Scheduler 层重复请求过滤数（请求级去重，优先作为 RPS 来源，列表页即产生）。
                # dedup/duplicate_count：某些后端会写入重复请求计数；若存在则作为补充。
                ordered_candidates = [
                    'AioRedisFilter/filtered_count',  # 优先：Redis 持久化去重过滤的请求数
                    'MemoryFilter/filtered_count',    # 其次：内存去重过滤的请求数
                    'dedup/duplicate_count',          # 次选：通用重复请求计数
                    'dedup/new_count',                # 兜底：新 item 接受数
                ]
                cur = 0
                for key in ordered_candidates:
                    v = crawler_stats.get_value(key, 0)
                    if isinstance(v, (int, float)) and v > cur:
                        cur = int(v)
                        # 继续遍历后面的 candidate，取所有里的最大值
                now = _time.monotonic()
                self._dedup_snapshots.append((now, cur))

                # 窗口（最多 60s）内 delta/t 算 RPS
                if len(self._dedup_snapshots) >= 2:
                    t0, v0 = self._dedup_snapshots[0]
                    dt = now - t0
                    if dt > 0:
                        delta = max(0, cur - v0)
                        rps = delta / min(60.0, dt)
                        try:
                            crawler_stats.set_value('filter/duplicate_rps', float(rps))
                        except Exception as e:
                            self.logger.debug("Suppressed exception: %s", e)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._safe_log('debug', f"dedup_rps_loop error (skipped): {e}")
                await asyncio.sleep(1.0)

    async def request_scheduled(self, request: Any, spider: Any) -> None:
        """记录调度的请求（排除重试）"""
        if not self.enabled:
            return
        if not request.meta.get('is_retry', False):
            self.stats['total_requests'] += 1

    async def response_received(self, response: Any, spider: Any) -> None:
        """记录接收到的响应"""
        if not self.enabled:
            return
        self.stats['total_responses'] += 1
        if hasattr(response, 'status') and response.status >= 400:
            self.stats['error_responses'] += 1

    # ---- 监控循环 ----

    async def _monitor_loop(self) -> None:
        """健康检查循环"""
        while True:
            try:
                await asyncio.sleep(self.check_interval)
                await self._check_health()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._safe_log('error', f"Error in health check loop: {e}")

    async def _check_health(self) -> None:
        """执行健康检查并输出报告（logger=None 时静默，防止 orphan task 醒来抛错）。"""
        try:
            now_time = datetime.now()
            self.stats['last_check_time'] = now_time

            runtime = (now_time - self.stats['start_time']).total_seconds() if self.stats['start_time'] else 0
            req_per_sec = self.stats['total_requests'] / runtime if runtime > 0 else 0
            resp_per_sec = self.stats['total_responses'] / runtime if runtime > 0 else 0
            error_rate = (
                self.stats['error_responses'] / self.stats['total_responses']
                if self.stats['total_responses'] > 0 else 0
            )

            report = {
                'runtime_seconds': round(runtime, 2),
                'total_requests': self.stats['total_requests'],
                'total_responses': self.stats['total_responses'],
                'requests_per_second': round(req_per_sec, 2),
                'responses_per_second': round(resp_per_sec, 2),
                'error_responses': self.stats['error_responses'],
                'error_rate': f"{error_rate:.2%}",
            }

            if error_rate > 0.1:
                self._safe_log('warning', f"Health check report: {report}")
            elif error_rate > 0.05:
                self._safe_log('info', f"Health check report: {report}")
            else:
                self._safe_log('debug', f"Health check report: {report}")
        except Exception as e:
            self._safe_log('error', f"Error in health check: {e}")
