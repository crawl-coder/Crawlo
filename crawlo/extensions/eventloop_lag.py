#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
EventloopLagProbe 扩展
======================

Eventloop Lag 探针（监控 asyncio 事件循环卡顿）。

原理：
    每 SAMPLE_INTERVAL_SEC 调度一个无阻塞 `loop.call_later`，记录"排期时间戳"和
    "实际被调度执行时间"的差值，即事件循环 Lag（ms）。样本存入 RingBuffer
    （容量 60 = 最近 1 分钟窗口）；每 PUBLISH_INTERVAL_SEC 计算并推送
    P50/P95/P99 三个 gauge，并当 P99 > WARN_THRESHOLD_MS 连续 WARN_CONSECUTIVE_TRIGGERS
    个发布周期时打 WARN 告警。

配置项（全部可选）：
    EVENTLOOP_LAG_PROBE_ENABLED  bool  = True
    EVENTLOOP_LAG_SAMPLE_INTERVAL float = 1.0   # 秒，采样间隔
    EVENTLOOP_LAG_PUBLISH_INTERVAL float = 5.0  # 秒，推指标间隔
    EVENTLOOP_LAG_WARN_THRESHOLD_MS int = 200
    EVENTLOOP_LAG_WARN_CONSECUTIVE int = 3
"""
from __future__ import annotations

import asyncio
import time
from typing import Any, Optional

from crawlo.utils.ring_buffer import RingBuffer
from crawlo.logging import get_logger
from .monitor.base import BaseMonitorExtension

try:
    from crawlo.extensions.notifications import async_send_crawler_alert, ChannelType
    _NOTIFY_AVAILABLE = True
except ImportError:
    _NOTIFY_AVAILABLE = False


class EventloopLagProbe(BaseMonitorExtension):
    """事件循环 Lag 探针扩展。"""

    monitor_id = "eventloop_lag_probe"
    config_key = "EVENTLOOP_LAG_PROBE_ENABLED"
    default_enabled = True

    # 默认值按文档规范
    DEFAULT_SAMPLE_INTERVAL: float = 1.0
    DEFAULT_PUBLISH_INTERVAL: float = 5.0
    DEFAULT_WARN_THRESHOLD_MS: int = 200
    DEFAULT_WARN_CONSECUTIVE: int = 3
    RING_CAPACITY: int = 60

    def __init__(self, crawler: Any):
        super().__init__(crawler)
        self.logger = get_logger(self.__class__.__name__)

        s = self.settings
        self._sample_interval: float = max(
            0.1, s.get_float("EVENTLOOP_LAG_SAMPLE_INTERVAL", self.DEFAULT_SAMPLE_INTERVAL)
        )
        self._publish_interval: float = max(
            1.0, s.get_float("EVENTLOOP_LAG_PUBLISH_INTERVAL", self.DEFAULT_PUBLISH_INTERVAL)
        )
        self._warn_threshold_ms: int = max(
            1, s.get_int("EVENTLOOP_LAG_WARN_THRESHOLD_MS", self.DEFAULT_WARN_THRESHOLD_MS)
        )
        self._warn_consecutive: int = max(
            1, s.get_int("EVENTLOOP_LAG_WARN_CONSECUTIVE", self.DEFAULT_WARN_CONSECUTIVE)
        )

        # 最近 60 个样本（默认每 1s 一个 = 1 分钟窗口）
        self._lag_samples = RingBuffer(self.RING_CAPACITY)
        self._consecutive_warn: int = 0
        self._alert_sent: bool = False  # 钉钉告警去重：仅首次触发时发送

        # 循环任务控制
        self._sample_task: Optional[asyncio.Task] = None
        self._publish_task: Optional[asyncio.Task] = None
        self._stopping = False

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------

    @classmethod
    def from_crawler(cls, crawler: Any):
        return cls(crawler)

    async def spider_opened(self) -> None:
        """spider 启动时拉起采样 + 发布双循环。"""
        if not self.enabled:
            return
        loop = asyncio.get_event_loop()
        self._stopping = False
        self._sample_task = loop.create_task(self._sample_loop())
        self._publish_task = loop.create_task(self._publish_loop())
        self.logger.debug(
            "EventloopLagProbe started (sample=%.1fs publish=%.1fs warn_p99>=%dms/%d)",
            self._sample_interval,
            self._publish_interval,
            self._warn_threshold_ms,
            self._warn_consecutive,
        )
        await super().spider_opened()

    async def spider_closed(self, spider: Any = None, reason: str = "") -> None:
        """spider 关闭时取消后台任务，避免 hanging。"""
        self._stopping = True
        for t in (self._sample_task, self._publish_task):
            if t is not None and not t.done():
                t.cancel()
                try:
                    await t
                except (asyncio.CancelledError, Exception):
                    pass
        await super().spider_closed(spider=spider, reason=reason)

    # ------------------------------------------------------------------
    # 采样循环
    # ------------------------------------------------------------------

    async def _sample_loop(self) -> None:
        """按 `_sample_interval` 周期性调度 call_later 探针，测量真实 lag 并存入 RingBuffer。"""
        loop = asyncio.get_event_loop()
        while not self._stopping:
            try:
                t_scheduled = loop.time()
                wall_start = time.monotonic()

                # call_later 事件循环内部排期（高分辨率），当实际执行时计算真实排期差
                fut: asyncio.Future[float] = loop.create_future()

                def _probe():
                    try:
                        if not fut.done():
                            fut.set_result(loop.time() - t_scheduled)
                    except Exception as _e:  # pragma: no cover
                        if not fut.done():
                            fut.set_exception(_e)

                loop.call_later(0, _probe)

                try:
                    loop_lag = await asyncio.wait_for(fut, timeout=max(5.0, self._sample_interval * 3))
                except asyncio.TimeoutError:
                    # 事件循环阻塞导致 probe 未来得及回调，按 wall_clock 估算上限
                    loop_lag = time.monotonic() - wall_start
                except Exception:
                    loop_lag = time.monotonic() - wall_start

                # loop.time() 单位秒 → 转毫秒，下限 0
                lag_ms = max(0.0, loop_lag * 1000.0)
                try:
                    self._lag_samples.append(lag_ms)
                except Exception as e:
                    self.logger.debug("Suppressed exception: %s", e)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.debug(f"eventloop lag sample error (skipped): {e}")

            # 精准 sleep：即使上一个采样被 lag 拉长，也按排期间隔对齐
            await asyncio.sleep(self._sample_interval)

    # ------------------------------------------------------------------
    # 发布循环（写入 StatsCollector / Prometheus gauge + 阈值告警）
    # ------------------------------------------------------------------

    async def _publish_loop(self) -> None:
        """按 `_publish_interval` 计算 P50/P95/P99 并写入 stats；触发告警阈值连续计数。"""
        while not self._stopping:
            try:
                await asyncio.sleep(self._publish_interval)
                p50 = p95 = p99 = None
                try:
                    if len(self._lag_samples) > 0:
                        p50 = self._lag_samples.percentile(50)
                        p95 = self._lag_samples.percentile(95)
                        p99 = self._lag_samples.percentile(99)
                except Exception as e:
                    self.logger.debug(f"eventloop lag percentile calc error: {e}")
                    continue

                stats = getattr(self.crawler, "stats", None)
                if stats is not None:
                    try:
                        if p50 is not None:
                            stats.set_value("resource/eventloop_lag_ms_p50", float(p50))
                        if p95 is not None:
                            stats.set_value("resource/eventloop_lag_ms_p95", float(p95))
                        if p99 is not None:
                            stats.set_value("resource/eventloop_lag_ms_p99", float(p99))
                    except Exception as e:
                        self.logger.debug(f"eventloop lag stats write error: {e}")

                # 阈值告警：P99 持续 >= 阈值 N 个周期打 WARN，其余打 DEBUG
                if p99 is None:
                    continue
                if p99 >= self._warn_threshold_ms:
                    self._consecutive_warn += 1
                    if self._consecutive_warn >= self._warn_consecutive:
                        self.logger.warning(
                            "Event loop lag HIGH: p99=%.1fms (>=%dms, %d consecutive) "
                            "n=%d p50=%.1fms p95=%.1fms — GC/阻塞 IO/大同步函数占坑?",
                            p99, self._warn_threshold_ms, self._consecutive_warn,
                            len(self._lag_samples),
                            p50 if p50 is not None else float("nan"),
                            p95 if p95 is not None else float("nan"),
                        )
                        # P4 钉钉告警规则 #1：EventloopLagHigh — 仅首次触发时发送，恢复后重置
                        if not self._alert_sent and _NOTIFY_AVAILABLE:
                            self._alert_sent = True
                            try:
                                await async_send_crawler_alert(
                                    title="事件循环 Lag 告警",
                                    content=(
                                        f"P99={p99:.1f}ms (阈值={self._warn_threshold_ms}ms, "
                                        f"连续{self._consecutive_warn}次) — 可能存在 GC 压力/阻塞 IO/大同步函数"
                                    ),
                                    channel=ChannelType.DINGTALK,
                                )
                            except Exception as e:
                                self.logger.debug(f"Failed to send DingTalk alert: {e}")
                    else:
                        self.logger.info(
                            "Event loop lag elevated: p99=%.1fms (>=%dms, %d/%d)",
                            p99, self._warn_threshold_ms,
                            self._consecutive_warn, self._warn_consecutive,
                        )
                else:
                    if self._consecutive_warn > 0:
                        self._alert_sent = False  # 恢复后重置告警去重标志
                        self.logger.info(
                            "Event loop lag recovered: p99=%.1fms (<%dms)",
                            p99, self._warn_threshold_ms,
                        )
                    self._consecutive_warn = 0
                    self.logger.debug(
                        "Event loop lag: p50=%.1fms p95=%.1fms p99=%.1fms (n=%d)",
                        p50 if p50 is not None else 0.0,
                        p95 if p95 is not None else 0.0,
                        p99, len(self._lag_samples),
                    )
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.debug(f"eventloop lag publish loop error: {e}")
