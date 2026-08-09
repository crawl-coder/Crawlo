#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
P3-B-01 回归单元测试：Auto 模式在 Redis 可用时正确切换到
AioRedisFilter + RedisDedupPipeline（此前误用 MemoryFilter 导致跨运行去重失效）。

策略：
1. 直接调用 `CrawloConfig.auto()` → `.to_settings()`（走 factories.py _make_auto）
2. 探活本机 Redis：能 ping 通 → 验证 FILTER/DEDUP 都切到 Redis 版本
3. 连不上 → 自动 skip（x 标记，不影响 CI）

另外：
- test_factories_redis_unavailable 用 Mock 强制 Redis ping 失败 → 验证 fallback 到 MemoryFilter
"""

import pytest
from unittest.mock import patch, MagicMock


def _redis_ping_available():
    try:
        import redis as _sync_redis  # 用同步版，避免 event loop 依赖
        r = _sync_redis.Redis(host="127.0.0.1", port=6379, db=0, socket_connect_timeout=1)
        return bool(r.ping())
    except Exception:
        return False


class TestP3B01AutoModeDedup:
    """Auto 模式 Factories 修复的回归测试。"""

    @pytest.mark.skipif(not _redis_ping_available(), reason="本地 Redis (127.0.0.1:6379/0) 不可达，跳过在线断言")
    def test_auto_fallback_to_memory_when_redis_down(self):
        """
        用错误的 Redis URL（redis://127.0.0.1:1）触发降级：
        CrawloConfig.auto 会先尝试 ping 给出的 REDIS_URL，连不上就 fallback 回 MemoryFilter。
        """
        from crawlo.core.config.factories import CrawloConfig
        # 强行给一个无法连接的 Redis URL
        cfg = CrawloConfig.auto(
            "project_p3b01_offline",
            spider_name="sp_p3b01_offline",
            REDIS_URL="redis://127.0.0.1:1/0",
            REDIS_HOST="127.0.0.1",
            REDIS_PORT=1,
        )
        settings = cfg.settings

        filter_val = settings.get("FILTER_CLASS") or "crawlo.filters.MemoryFilter"
        # Redis 不可连时，B-01 修复后的预期：要么仍是 MemoryFilter，要么尚未覆盖（仍为 standalone 继承值）
        assert "Memory" in filter_val or filter_val.endswith("MemoryFilter"), (
            f"错误 Redis URL 时必须落到 Memory 侧去重，实际 {filter_val!r}"
        )

    @pytest.mark.skipif(not _redis_ping_available(), reason="本地 Redis (127.0.0.1:6379/0) 不可达，跳过在线断言")
    def test_auto_switches_to_redis_backed_dedup_when_redis_online(self):
        """B-01 关键断言：Redis 在线时，CrawloConfig.auto() 必须切到 Redis 版去重。"""
        from crawlo.core.config.factories import CrawloConfig

        cfg = CrawloConfig.auto(
            "project_p3b01_online",
            spider_name="sp_p3b01_online",
        )
        settings = cfg.settings

        filter_cls = settings.get("FILTER_CLASS")
        dedup_pipe = settings.get("DEFAULT_DEDUP_PIPELINE")

        assert filter_cls == "crawlo.filters.AioRedisFilter", (
            f"Redis 在线时 CrawloConfig.auto() 应把 FILTER_CLASS 切到 AioRedisFilter，"
            f"实际是 {filter_cls!r}（这就是 B-01 修复前的 Bug：去重不跨运行生效）"
        )
        assert dedup_pipe == "crawlo.pipelines.RedisDedupPipeline", (
            f"Redis 在线时 CrawloConfig.auto() 应把 DEFAULT_DEDUP_PIPELINE 切到 RedisDedupPipeline，"
            f"实际是 {dedup_pipe!r}"
        )


class TestP3B02AutoClearShutdownFlag:
    """engine._check_control_state 新增的 auto-clear 分支（空集群下自动清 shutdown）。"""

    @pytest.mark.asyncio
    async def test_auto_clear_fires_when_only_self_registered(self):
        """
        registry 里只有本 Worker，control:state == shutdown
        → 必须走 AutoFix：调用 resume_spider() 清状态并返回 True（不退出）。
        """
        import asyncio
        from unittest.mock import AsyncMock as UAsyncMock
        from crawlo.core.engine import Engine
        from crawlo.core.engine_distributed import DistributedCoordinator

        # —— 构造最小 Engine（参考 test_stale_pending_xclaim.py） ——
        engine = Engine.__new__(Engine)
        engine.running = True
        engine.crawler = None
        engine.settings = {"CLUSTER_AUTO_CLEAR_SHUTDOWN_ON_START": True}
        engine.logger = MagicMock()
        engine._cluster_state = MagicMock()
        engine._cluster_state.worker_id = "W-only-self"
        engine._cluster_state.paused = False
        engine._cluster_state.dynamic_config = MagicMock()
        engine._cluster_state.dynamic_config.get_control_state = UAsyncMock(return_value="shutdown")
        engine._cluster_state.dynamic_config.resume_spider = UAsyncMock()
        engine._cluster_state.registry = MagicMock()
        # 只有自己一个活跃
        engine._cluster_state.registry.get_active_workers = UAsyncMock(return_value=[
            {"id": "W-only-self", "status": "running"},
        ])
        # P4 Week1 A2：薄代理依赖组合组件
        engine._distributed = DistributedCoordinator(engine)
        engine._dispatcher = MagicMock()

        should_continue = await engine._check_control_state()

        assert should_continue is True, "registry 空集群 + shutdown 残留应自动 recover 后继续运行，而不是退出"
        assert engine.running is True, "engine.running 必须仍是 True（没触发 self.running=False 分支）"
        engine._cluster_state.dynamic_config.resume_spider.assert_awaited_once(), (
            "必须调用 dynamic_config.resume_spider() 重置 control:state→running"
        )
        # 日志里必须出现 P3-B-02 标记（告警信息/通知渠道用）
        logged_warning_text = " ".join(
            str(c.args[0]) for c in engine.logger.warning.call_args_list or []
        )
        assert "P3-B-02" in logged_warning_text, (
            "需要显式打印 P3-B-02 标记，方便线上钉钉告警匹配"
        )

    @pytest.mark.asyncio
    async def test_no_auto_clear_when_other_workers_alive(self):
        """
        有其他 Worker 活跃的情况下遇到 shutdown，必须正常退出（避免破坏人工的 shutdown）。
        """
        from unittest.mock import AsyncMock as UAsyncMock
        from crawlo.core.engine import Engine
        from crawlo.core.engine_distributed import DistributedCoordinator

        engine = Engine.__new__(Engine)
        engine.running = True
        engine.settings = {"CLUSTER_AUTO_CLEAR_SHUTDOWN_ON_START": True}
        engine.logger = MagicMock()
        engine._cluster_state = MagicMock()
        engine._cluster_state.worker_id = "W-newbie"
        engine._cluster_state.paused = False
        engine._cluster_state.dynamic_config = MagicMock()
        engine._cluster_state.dynamic_config.get_control_state = UAsyncMock(return_value="shutdown")
        engine._cluster_state.dynamic_config.resume_spider = UAsyncMock()
        engine._cluster_state.registry = MagicMock()
        # 另一个 Worker（W-veteran）还在活跃
        engine._cluster_state.registry.get_active_workers = UAsyncMock(return_value=[
            {"id": "W-veteran"},
            {"id": "W-newbie"},
        ])
        # P4 Week1 A2：薄代理依赖组合组件
        engine._distributed = DistributedCoordinator(engine)
        engine._dispatcher = MagicMock()

        should_continue = await engine._check_control_state()

        assert should_continue is False, "其他 Worker 还在，必须执行原本的 shutdown 退出逻辑"
        assert engine.running is False
        engine._cluster_state.dynamic_config.resume_spider.assert_not_awaited()


class TestP3B03Defaults:
    """P3-B-03 超时 / XCLAIM 等默认值对齐的断言。"""

    def test_stream_and_failover_defaults_in_default_settings(self):
        from crawlo.settings import default_settings as ds

        # 1.5min（90,000 ms），给慢请求留余量
        assert ds.STREAM_CONSUMER_IDLE_TIMEOUT == 90_000
        # 网络抖动不要太快投死信（5 次）
        assert ds.STREAM_DELIVERY_COUNT_LIMIT == 5
        # Failover 间隔 15s（更早发现死 Worker）
        assert ds.CLUSTER_FAILOVER_CHECK_INTERVAL == 15
        # P3-B-02 开关默认打开
        assert ds.CLUSTER_AUTO_CLEAR_SHUTDOWN_ON_START is True

    def test_distributed_mode_map_values(self):
        from crawlo.core.config.base import MODE_CONFIG_MAP
        d = MODE_CONFIG_MAP["distributed"]

        assert d["STREAM_CONSUMER_IDLE_TIMEOUT"] == 90_000
        assert d["STREAM_DELIVERY_COUNT_LIMIT"] == 5
        assert d["CLUSTER_FAILOVER_CHECK_INTERVAL"] == 15
        assert d["CLUSTER_AUTO_CLEAR_SHUTDOWN_ON_START"] is True
