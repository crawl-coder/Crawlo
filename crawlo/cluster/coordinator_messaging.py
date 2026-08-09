#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""ClusterMixin 消息/故障子 Mixin（P2-6 从 coordinator.py 拆分）"""
from __future__ import annotations

import asyncio


try:
    from crawlo.extensions.notifications import async_send_crawler_alert, ChannelType
    _NOTIFY_AVAILABLE = True
except ImportError:
    async_send_crawler_alert = None
    ChannelType = None
    _NOTIFY_AVAILABLE = False


class ClusterMessagingMixin:
    """控制/配置消息处理与故障检测循环。"""

    async def _on_control_message(self, message: dict):
        """处理控制消息（暂停/恢复/停止）"""
        action = message.get("action", "")
        if action == "pause":
            self._cluster_state.paused = True
            self.logger.info("Cluster control: PAUSED")
        elif action == "resume":
            self._cluster_state.paused = False
            self.logger.info("Cluster control: RESUMED")
        elif action == "shutdown":
            self.logger.warning("Cluster control: SHUTDOWN received")
            self.running = False

    async def _on_config_message(self, message: dict):
        """处理配置变更消息"""
        action = message.get("action", "")
        if action == "rate_limit" and self._cluster_state.rate_limiter:
            domain = message.get("domain", "")
            rate = message.get("rate", 0)
            await self._cluster_state.rate_limiter.set_rate(domain, rate)
        elif action == "seed_urls" and self._cluster_state.dynamic_config:
            urls = await self._cluster_state.dynamic_config.pop_seed_urls(count=100)
            for url in urls:
                from crawlo.http.request import Request
                await self.scheduler.enqueue_request(Request(url=url))

    # ========================================================================
    # 后台循环
    # ========================================================================

    async def _failover_loop(self):
        """故障检测后台循环"""
        while self.running:
            try:
                stats = await self._cluster_state.failover.check_and_recover()
                # cluster/worker/heartbeat_lost Counter
                dead_n = int(stats.get("dead_workers", 0)) if isinstance(stats, dict) else 0
                if dead_n > 0:
                    self._inc_stats_counter("cluster/worker/heartbeat_lost", dead_n)
                    # P4 钉钉告警规则 #3：HeartbeatLost — Worker 心跳丢失触发故障转移
                    if _NOTIFY_AVAILABLE:
                        try:
                            await async_send_crawler_alert(
                                title="Worker 心跳丢失告警",
                                content=(
                                    f"检测到 {dead_n} 个 Worker 心跳丢失，已触发故障转移。"
                                    f"请检查 Worker 是否崩溃或网络分区。"
                                ),
                                channel=ChannelType.DINGTALK,
                            )
                        except Exception as e:
                            self._logger.debug(f"Failed to send heartbeat lost alert: {e}")
                await asyncio.sleep(self._cluster_state.failover.failover_interval)
            except asyncio.CancelledError:
                break
            except Exception:
                await asyncio.sleep(5)

    def _inc_stats_counter(self, key: str, count: int = 1) -> None:
        """向 StatsCollector 写入 Counter（fail-safe：scheduler 不可用时静默跳过）。"""
        try:
            if count <= 0:
                return
            scheduler = getattr(self, 'scheduler', None)
            if scheduler is None:
                return
            crawler = getattr(scheduler, '_crawler', None)
            if crawler is None:
                # Engine 继承 ClusterMixin 时 scheduler 持 crawler 引用
                crawler = getattr(self, 'crawler', None)
            if crawler is None:
                return
            stats = getattr(crawler, 'stats', None)
            if stats is None:
                return
            stats.inc_value(key, count=count)
        except Exception:
            pass

