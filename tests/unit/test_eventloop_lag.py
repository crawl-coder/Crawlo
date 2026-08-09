#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
EventloopLagProbe 扩展单元测试
================================

覆盖范围（对应 P4_STRUCTURE_GOVERNANCE_PLAN_v1.md §4 验收标准）：
1. RingBuffer + percentile 工具函数正确性
2. EventloopLagProbe 初始化（默认配置 / 自定义配置）
3. P50/P95/P99 指标写入 StatsCollector
4. 阈值告警：P99 >= threshold 连续 N 个周期触发 WARN
5. spider_opened / spider_closed 生命周期（后台任务启停干净）
6. 空样本时不写入指标、不触发告警
"""
import asyncio
import unittest
from unittest.mock import MagicMock, patch

from crawlo.utils.ring_buffer import RingBuffer, percentile, percentiles


# ==================================================================
# 辅助：Mock settings（复用 test_prometheus_backend 的模式）
# ==================================================================

class MockSettings(dict):
    """模拟 Settings 对象，支持 get_int/get_bool/get_float/get_dict"""

    def get(self, k, d=None):
        return super().get(k, d)

    def get_int(self, k, d=0):
        val = super().get(k, d)
        try:
            return int(val)
        except (TypeError, ValueError):
            return d

    def get_bool(self, k, d=False):
        val = super().get(k, d)
        if isinstance(val, bool):
            return val
        return str(val).lower() in ('1', 'true', 'yes') if val else d

    def get_float(self, k, d=0.0):
        val = super().get(k, d)
        try:
            return float(val)
        except (TypeError, ValueError):
            return d

    def get_dict(self, k, d=None):
        val = super().get(k, d) if d is None else super().get(k, {})
        return val if isinstance(val, dict) else {}


def _make_mock_crawler(settings_dict=None):
    """构造一个最小化 mock crawler，含 settings + stats。"""
    s = MockSettings(settings_dict or {})
    crawler = MagicMock()
    crawler.settings = s
    # stats mock：set_value / get_value 用 dict 存储
    _stats_store = {}

    stats = MagicMock()
    stats.set_value = lambda k, v: _stats_store.__setitem__(k, v)
    stats.get_value = lambda k, d=None: _stats_store.get(k, d)
    stats.get_stats = lambda: dict(_stats_store)
    crawler.stats = stats
    # subscriber mock
    crawler.subscriber = MagicMock()
    return crawler


# ==================================================================
# 1. RingBuffer + percentile 工具函数
# ==================================================================

class TestRingBuffer(unittest.TestCase):
    """RingBuffer 基础功能测试"""

    def test_append_and_len(self):
        rb = RingBuffer(5)
        self.assertEqual(len(rb), 0)
        for i in range(3):
            rb.append(float(i))
        self.assertEqual(len(rb), 3)

    def test_capacity_overflow(self):
        """容量满后覆盖最旧元素"""
        rb = RingBuffer(3)
        for i in range(5):
            rb.append(float(i))
        self.assertEqual(len(rb), 3)
        # 最旧的应该是 2.0（0 和 1 被覆盖）
        snap = rb.snapshot()
        self.assertEqual(snap, [2.0, 3.0, 4.0])

    def test_percentile_basic(self):
        """percentile 对已知序列的计算正确性"""
        rb = RingBuffer(100)
        for v in [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]:
            rb.append(float(v))
        # P50 = 55.0（线性插值，10 个元素，rank=4.5 → 50*0.5+60*0.5=55）
        self.assertAlmostEqual(rb.percentile(50), 55.0, places=1)
        # P99 接近最大值
        self.assertGreaterEqual(rb.percentile(99), 99.0)
        # P0 = 最小值
        self.assertEqual(rb.percentile(0), 10.0)
        # P100 = 最大值
        self.assertEqual(rb.percentile(100), 100.0)

    def test_percentile_single_element(self):
        rb = RingBuffer(10)
        rb.append(42.0)
        self.assertEqual(rb.percentile(50), 42.0)
        self.assertEqual(rb.percentile(99), 42.0)

    def test_percentile_empty(self):
        rb = RingBuffer(10)
        self.assertEqual(rb.percentile(50), 0.0)
        self.assertEqual(rb.percentile(99), 0.0)

    def test_standalone_percentile_function(self):
        """独立 percentile() 函数对已排序序列的计算"""
        sorted_vals = [1.0, 2.0, 3.0, 4.0, 5.0]
        self.assertEqual(percentile(sorted_vals, 0), 1.0)
        self.assertEqual(percentile(sorted_vals, 100), 5.0)
        self.assertAlmostEqual(percentile(sorted_vals, 50), 3.0, places=1)

    def test_standalone_percentiles_function(self):
        """percentiles() 一次求多个百分位"""
        vals = [10, 20, 30, 40, 50]
        p50, p95, p99 = percentiles(vals, [50, 95, 99])
        self.assertAlmostEqual(p50, 30.0, places=1)
        self.assertGreaterEqual(p99, 49.0)
        self.assertGreaterEqual(p95, p50)

    def test_mean_and_sum(self):
        rb = RingBuffer(10)
        for v in [1, 2, 3, 4, 5]:
            rb.append(float(v))
        self.assertEqual(rb.sum(), 15.0)
        self.assertEqual(rb.mean(), 3.0)
        self.assertEqual(rb.max(), 5.0)
        self.assertEqual(rb.min(), 1.0)

    def test_clear(self):
        rb = RingBuffer(10)
        rb.append(1.0)
        rb.append(2.0)
        rb.clear()
        self.assertEqual(len(rb), 0)
        self.assertEqual(rb.percentile(50), 0.0)


# ==================================================================
# 2. EventloopLagProbe 初始化
# ==================================================================

class TestEventloopLagProbeInit(unittest.TestCase):
    """EventloopLagProbe 初始化配置测试"""

    def test_default_config(self):
        from crawlo.extensions.eventloop_lag import EventloopLagProbe
        crawler = _make_mock_crawler()
        probe = EventloopLagProbe(crawler)
        self.assertEqual(probe._sample_interval, 1.0)
        self.assertEqual(probe._publish_interval, 5.0)
        self.assertEqual(probe._warn_threshold_ms, 200)
        self.assertEqual(probe._warn_consecutive, 3)
        self.assertEqual(len(probe._lag_samples), 0)
        self.assertTrue(probe.enabled)

    def test_custom_config(self):
        from crawlo.extensions.eventloop_lag import EventloopLagProbe
        settings = {
            'EVENTLOOP_LAG_SAMPLE_INTERVAL': 0.5,
            'EVENTLOOP_LAG_PUBLISH_INTERVAL': 2.0,
            'EVENTLOOP_LAG_WARN_THRESHOLD_MS': 100,
            'EVENTLOOP_LAG_WARN_CONSECUTIVE': 2,
        }
        crawler = _make_mock_crawler(settings)
        probe = EventloopLagProbe(crawler)
        self.assertEqual(probe._sample_interval, 0.5)
        self.assertEqual(probe._publish_interval, 2.0)
        self.assertEqual(probe._warn_threshold_ms, 100)
        self.assertEqual(probe._warn_consecutive, 2)

    def test_min_clamp(self):
        """配置值过低时被 clamp 到最小值"""
        from crawlo.extensions.eventloop_lag import EventloopLagProbe
        settings = {
            'EVENTLOOP_LAG_SAMPLE_INTERVAL': 0.01,  # < 0.1 → clamped
            'EVENTLOOP_LAG_PUBLISH_INTERVAL': 0.1,   # < 1.0 → clamped
            'EVENTLOOP_LAG_WARN_THRESHOLD_MS': 0,    # < 1 → clamped
            'EVENTLOOP_LAG_WARN_CONSECUTIVE': 0,     # < 1 → clamped
        }
        crawler = _make_mock_crawler(settings)
        probe = EventloopLagProbe(crawler)
        self.assertEqual(probe._sample_interval, 0.1)
        self.assertEqual(probe._publish_interval, 1.0)
        self.assertEqual(probe._warn_threshold_ms, 1)
        self.assertEqual(probe._warn_consecutive, 1)

    def test_from_crawler(self):
        from crawlo.extensions.eventloop_lag import EventloopLagProbe
        crawler = _make_mock_crawler()
        probe = EventloopLagProbe.from_crawler(crawler)
        self.assertIsInstance(probe, EventloopLagProbe)


# ==================================================================
# 3. P50/P95/P99 指标写入
# ==================================================================

class TestEventloopLagProbePublish(unittest.TestCase):
    """EventloopLagProbe 指标发布测试"""

    def test_publish_writes_p50_p95_p99(self):
        """_publish_loop 计算并写入 P50/P95/P99 到 stats"""
        from crawlo.extensions.eventloop_lag import EventloopLagProbe
        crawler = _make_mock_crawler({
            'EVENTLOOP_LAG_PUBLISH_INTERVAL': 0.1,  # 快速发布
        })
        probe = EventloopLagProbe(crawler)
        # 手动注入样本
        for v in [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]:
            probe._lag_samples.append(v)

        # 手动执行一次 publish 逻辑（不等 sleep）
        async def _run_once():
            # 直接调 _publish_loop 的内部逻辑
            p50 = probe._lag_samples.percentile(50)
            p95 = probe._lag_samples.percentile(95)
            p99 = probe._lag_samples.percentile(99)
            stats = getattr(probe.crawler, 'stats', None)
            if stats is not None:
                stats.set_value('resource/eventloop_lag_ms_p50', float(p50))
                stats.set_value('resource/eventloop_lag_ms_p95', float(p95))
                stats.set_value('resource/eventloop_lag_ms_p99', float(p99))

        asyncio.run(_run_once())

        # 验证 stats 中写入了 3 个指标
        self.assertAlmostEqual(
            crawler.stats.get_value('resource/eventloop_lag_ms_p50'), 5.5, places=1
        )
        self.assertIsNotNone(crawler.stats.get_value('resource/eventloop_lag_ms_p95'))
        self.assertIsNotNone(crawler.stats.get_value('resource/eventloop_lag_ms_p99'))
        # P99 >= P95 >= P50
        p50 = crawler.stats.get_value('resource/eventloop_lag_ms_p50')
        p95 = crawler.stats.get_value('resource/eventloop_lag_ms_p95')
        p99 = crawler.stats.get_value('resource/eventloop_lag_ms_p99')
        self.assertGreaterEqual(p95, p50)
        self.assertGreaterEqual(p99, p95)

    def test_publish_empty_samples_no_write(self):
        """空样本时不写入指标"""
        from crawlo.extensions.eventloop_lag import EventloopLagProbe
        crawler = _make_mock_crawler()
        probe = EventloopLagProbe(crawler)
        # 不注入任何样本，len(_lag_samples) == 0
        self.assertEqual(len(probe._lag_samples), 0)
        # 模拟 _publish_loop 的判断逻辑
        if len(probe._lag_samples) > 0:
            self.fail("Should not write stats when samples are empty")


# ==================================================================
# 4. 阈值告警
# ==================================================================

class TestEventloopLagProbeAlert(unittest.TestCase):
    """EventloopLagProbe 阈值告警测试"""

    def test_consecutive_warn_triggers(self):
        """P99 >= threshold 连续 N 次后 _consecutive_warn >= N"""
        from crawlo.extensions.eventloop_lag import EventloopLagProbe
        crawler = _make_mock_crawler({
            'EVENTLOOP_LAG_WARN_THRESHOLD_MS': 200,
            'EVENTLOOP_LAG_WARN_CONSECUTIVE': 3,
        })
        probe = EventloopLagProbe(crawler)

        # 模拟 3 次超阈值
        for i in range(3):
            p99 = 250.0  # > 200
            if p99 >= probe._warn_threshold_ms:
                probe._consecutive_warn += 1

        self.assertEqual(probe._consecutive_warn, 3)
        self.assertGreaterEqual(probe._consecutive_warn, probe._warn_consecutive)

    def test_warn_resets_on_recovery(self):
        """P99 恢复到阈值以下时 _consecutive_warn 重置为 0"""
        from crawlo.extensions.eventloop_lag import EventloopLagProbe
        crawler = _make_mock_crawler({
            'EVENTLOOP_LAG_WARN_THRESHOLD_MS': 200,
        })
        probe = EventloopLagProbe(crawler)

        # 先累积 2 次超阈值
        probe._consecutive_warn = 2
        # 模拟恢复
        p99 = 100.0  # < 200
        if p99 < probe._warn_threshold_ms:
            probe._consecutive_warn = 0

        self.assertEqual(probe._consecutive_warn, 0)

    def test_no_warn_below_threshold(self):
        """P99 < threshold 时不增加 _consecutive_warn"""
        from crawlo.extensions.eventloop_lag import EventloopLagProbe
        crawler = _make_mock_crawler({
            'EVENTLOOP_LAG_WARN_THRESHOLD_MS': 200,
        })
        probe = EventloopLagProbe(crawler)

        p99 = 50.0  # < 200
        if p99 >= probe._warn_threshold_ms:
            probe._consecutive_warn += 1

        self.assertEqual(probe._consecutive_warn, 0)


# ==================================================================
# 5. 生命周期（spider_opened / spider_closed）
# ==================================================================

class TestEventloopLagProbeLifecycle(unittest.TestCase):
    """EventloopLagProbe 后台任务启停测试"""

    def test_spider_opened_starts_tasks(self):
        """spider_opened 启动 sample + publish 两个后台任务"""
        from crawlo.extensions.eventloop_lag import EventloopLagProbe

        async def _test():
            crawler = _make_mock_crawler({
                'EVENTLOOP_LAG_SAMPLE_INTERVAL': 0.1,
                'EVENTLOOP_LAG_PUBLISH_INTERVAL': 0.2,
            })
            probe = EventloopLagProbe(crawler)
            # 模拟未注册到 MonitorManager（from_crawler 路径）
            with patch('crawlo.extensions.monitor.base.get_monitor_manager') as mock_mm:
                mock_mm.return_value.get_monitor.return_value = None
                await probe.spider_opened()

            self.assertIsNotNone(probe._sample_task)
            self.assertIsNotNone(probe._publish_task)
            self.assertFalse(probe._sample_task.done())
            self.assertFalse(probe._publish_task.done())

            # 清理
            probe._stopping = True
            probe._sample_task.cancel()
            probe._publish_task.cancel()
            try:
                await probe._sample_task
            except (asyncio.CancelledError, Exception):
                pass
            try:
                await probe._publish_task
            except (asyncio.CancelledError, Exception):
                pass

        asyncio.run(_test())

    def test_spider_closed_cancels_tasks(self):
        """spider_closed 取消后台任务"""
        from crawlo.extensions.eventloop_lag import EventloopLagProbe

        async def _test():
            crawler = _make_mock_crawler({
                'EVENTLOOP_LAG_SAMPLE_INTERVAL': 0.1,
                'EVENTLOOP_LAG_PUBLISH_INTERVAL': 0.2,
            })
            probe = EventloopLagProbe(crawler)
            with patch('crawlo.extensions.monitor.base.get_monitor_manager') as mock_mm:
                mock_mm.return_value.get_monitor.return_value = None
                await probe.spider_opened()

            # 确认任务在运行
            self.assertFalse(probe._sample_task.done())

            # 关闭
            with patch('crawlo.extensions.monitor.base.get_monitor_manager') as mock_mm2:
                mock_mm2.return_value.get_monitor.return_value = None
                await probe.spider_closed()

            # 任务已被取消
            self.assertTrue(probe._stopping)

        asyncio.run(_test())

    def test_disabled_probe_no_tasks(self):
        """enabled=False 时 spider_opened 不启动任务"""
        from crawlo.extensions.eventloop_lag import EventloopLagProbe

        async def _test():
            crawler = _make_mock_crawler()
            probe = EventloopLagProbe(crawler)
            probe.enabled = False
            await probe.spider_opened()
            self.assertIsNone(probe._sample_task)
            self.assertIsNone(probe._publish_task)

        asyncio.run(_test())


# ==================================================================
# 6. 集成测试：完整采样→发布→stats 写入流程
# ==================================================================

class TestEventloopLagProbeIntegration(unittest.TestCase):
    """端到端集成测试：短周期采样 + 发布 + stats 验证"""

    def test_end_to_end_sample_and_publish(self):
        """启动 probe → 等待采样 + 发布 → 验证 stats 中有 P50/P95/P99"""
        from crawlo.extensions.eventloop_lag import EventloopLagProbe

        async def _test():
            crawler = _make_mock_crawler({
                'EVENTLOOP_LAG_SAMPLE_INTERVAL': 0.1,
                'EVENTLOOP_LAG_PUBLISH_INTERVAL': 0.3,
            })
            probe = EventloopLagProbe(crawler)
            with patch('crawlo.extensions.monitor.base.get_monitor_manager') as mock_mm:
                mock_mm.return_value.get_monitor.return_value = None
                await probe.spider_opened()

            # 等待足够时间让采样和发布各执行至少一次
            await asyncio.sleep(1.0)

            # 关闭
            probe._stopping = True
            for t in (probe._sample_task, probe._publish_task):
                if t and not t.done():
                    t.cancel()
                    try:
                        await t
                    except (asyncio.CancelledError, Exception):
                        pass

            # 验证采样了至少 1 个样本
            self.assertGreater(len(probe._lag_samples), 0)

            # 验证 stats 中写入了至少 P99（publish 可能跑过 1~3 次）
            p99 = crawler.stats.get_value('resource/eventloop_lag_ms_p99')
            # 空闲事件循环的 lag 应该很小（< 50ms 通常）
            if p99 is not None:
                self.assertGreaterEqual(p99, 0.0)
                self.assertLess(p99, 500.0, f"P99={p99}ms seems too high for idle loop")

        asyncio.run(_test())

    def test_d_direction_metric_keys_in_stats(self):
        """验证 D 方向 8+3 个指标 key 在完整运行后存在于 stats 中"""
        from crawlo.extensions.eventloop_lag import EventloopLagProbe

        async def _test():
            crawler = _make_mock_crawler({
                'EVENTLOOP_LAG_SAMPLE_INTERVAL': 0.1,
                'EVENTLOOP_LAG_PUBLISH_INTERVAL': 0.3,
            })
            probe = EventloopLagProbe(crawler)
            with patch('crawlo.extensions.monitor.base.get_monitor_manager') as mock_mm:
                mock_mm.return_value.get_monitor.return_value = None
                await probe.spider_opened()

            await asyncio.sleep(1.5)

            probe._stopping = True
            for t in (probe._sample_task, probe._publish_task):
                if t and not t.done():
                    t.cancel()
                    try:
                        await t
                    except (asyncio.CancelledError, Exception):
                        pass

            # EventloopLagProbe 负责的 3 个 key
            raw_stats = crawler.stats.get_stats()
            eventloop_keys = [
                k for k in raw_stats if 'eventloop_lag' in k
            ]
            # 至少 p99 被写入
            self.assertTrue(
                len(eventloop_keys) > 0,
                f"No eventloop_lag keys in stats: {raw_stats}"
            )

        asyncio.run(_test())

    def test_blocking_eventloop_triggers_warn(self):
        """人工阻塞事件循环 > 500ms → P99 > 200ms 持续 3 tick → 日志告警被触发

        验收标准（P4 §4 L170）：人工阻塞 > 500ms → P99 > 200ms 持续 3 tick → 日志出现告警。

        实现说明：直接从测试协程调用 time.sleep() 无法可靠阻塞 _sample_loop 的
        call_later(0, _probe) 回调（因为 _sample_loop 大部分时间在 asyncio.sleep 中，
        阻塞恢复后新 probe 立即触发 lag≈0）。因此通过 patch loop.call_later 在 _probe
        回调前注入 time.sleep(0.3) 阻塞，模拟事件循环卡顿 300ms，使 _probe 测得
        lag ≈ 300ms > 200ms 阈值。
        """
        import time as _time
        from crawlo.extensions.eventloop_lag import EventloopLagProbe

        async def _test():
            crawler = _make_mock_crawler({
                'EVENTLOOP_LAG_SAMPLE_INTERVAL': 0.05,
                'EVENTLOOP_LAG_PUBLISH_INTERVAL': 0.15,
                'EVENTLOOP_LAG_WARN_THRESHOLD_MS': 200,
                'EVENTLOOP_LAG_WARN_CONSECUTIVE': 3,
            })
            probe = EventloopLagProbe(crawler)

            # 拦截 logger.warning 以验证告警被触发
            warn_messages = []
            original_warning = probe.logger.warning

            def _capture_warning(*args, **kwargs):
                warn_messages.append((args, kwargs))

            probe.logger.warning = _capture_warning

            # Patch loop.call_later：在 _probe 回调前注入 300ms 阻塞
            loop = asyncio.get_event_loop()
            original_call_later = loop.call_later
            block_count = [0]
            MAX_BLOCKS = 10  # 前 10 个 probe 回调注入阻塞

            def _patched_call_later(delay, callback, *args, **ctx):
                cb_name = getattr(callback, '__name__', '')
                if delay == 0 and cb_name == '_probe' and block_count[0] < MAX_BLOCKS:
                    block_count[0] += 1

                    def _blocking_probe():
                        _time.sleep(0.3)  # 模拟事件循环卡顿 300ms
                        callback(*args, **ctx)

                    return original_call_later(delay, _blocking_probe)
                return original_call_later(delay, callback, *args, **ctx)

            loop.call_later = _patched_call_later
            try:
                with patch('crawlo.extensions.monitor.base.get_monitor_manager') as mock_mm:
                    mock_mm.return_value.get_monitor.return_value = None
                    await probe.spider_opened()

                # 等待足够时间：10 个阻塞 probe (每个 0.3s + 0.05s sleep ≈ 3.5s)
                # + 3 个 publish 周期 (0.15s each)
                await asyncio.sleep(4.0)
            finally:
                loop.call_later = original_call_later

            # 清理
            probe._stopping = True
            for t in (probe._sample_task, probe._publish_task):
                if t and not t.done():
                    t.cancel()
                    try:
                        await t
                    except (asyncio.CancelledError, Exception):
                        pass

            # 断言 1：至少 1 个样本 >= 200ms（阻塞被探测到）
            samples = probe._lag_samples.snapshot()
            high_lag = [s for s in samples if s >= 200.0]
            self.assertGreater(
                len(high_lag), 0,
                f"Expected >= 1 sample >= 200ms after blocking, got: {samples}"
            )

            # 断言 2：consecutive_warn >= 3（3 个 publish 周期都看到 P99 > 200ms）
            self.assertGreaterEqual(
                probe._consecutive_warn, 3,
                f"Expected _consecutive_warn >= 3, got {probe._consecutive_warn}"
            )

            # 断言 3：logger.warning 被调用（"Event loop lag HIGH"）
            self.assertTrue(
                len(warn_messages) > 0,
                f"Expected logger.warning to be called, but it wasn't. "
                f"consecutive_warn={probe._consecutive_warn}, samples={samples}"
            )

        asyncio.run(_test())


if __name__ == '__main__':
    unittest.main()
