#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
逻辑修复验证测试

1. Prometheus 标签名校验
2. metrics_endpoint 使用 localhost
3. checkpoint 提取顺序（指纹先于请求）
4. engine close_spider 异常时触发 SPIDER_CLOSED
"""
import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import logging

# ---------- 1. 标签名校验 ----------

class TestLabelValidation(unittest.TestCase):
    """标签名非法应报明确错误"""

    def test_valid_labels_pass(self):
        from crawlo.stats.prometheus_backend import PrometheusStatsBackend
        b = PrometheusStatsBackend(port=0, labels={'spider': 'a', 'env_prod': 'b', '_x': 'c'})
        b.close()

    def test_space_in_label_raises(self):
        from crawlo.stats.prometheus_backend import PrometheusStatsBackend
        with self.assertRaises(ValueError) as ctx:
            PrometheusStatsBackend(port=0, labels={'my label': 'x'})
        self.assertIn('my label', str(ctx.exception))
        self.assertIn('PROMETHEUS_LABELS', str(ctx.exception))

    def test_leading_digit_raises(self):
        from crawlo.stats.prometheus_backend import PrometheusStatsBackend
        with self.assertRaises(ValueError):
            PrometheusStatsBackend(port=0, labels={'1bad': 'x'})

    def test_unicode_raises(self):
        from crawlo.stats.prometheus_backend import PrometheusStatsBackend
        with self.assertRaises(ValueError):
            PrometheusStatsBackend(port=0, labels={'env中文': 'x'})


# ---------- 2. metrics_endpoint ----------

class TestMetricsEndpointLocalhost(unittest.TestCase):
    """get_stats 应返回 localhost URL"""

    def setUp(self):
        from crawlo.stats.prometheus_backend import PrometheusStatsBackend
        self.backend = PrometheusStatsBackend(port=0)

    def tearDown(self):
        try:
            self.backend.close()
        except Exception:
            pass

    def test_endpoint_uses_localhost(self):
        stats = self.backend.get_stats()
        url = stats['metrics_endpoint']
        self.assertIn('localhost', url)
        self.assertNotIn('0.0.0.0', url)

    def test_endpoint_format(self):
        stats = self.backend.get_stats()
        url = stats['metrics_endpoint']
        port = stats['port']
        self.assertEqual(url, f'http://localhost:{port}/metrics')


# ---------- 3. checkpoint 提取顺序 ----------

class TestCheckpointExtractionOrder(unittest.TestCase):
    """指纹应先于请求提取"""

    def test_save_order(self):
        """验证 save() 内先调 _extract_fingerprints 再调 _extract_pending_requests"""
        from crawlo.checkpoint.manager import CheckpointManager

        # 模拟 manager 使 save() 不依赖完整初始化
        cm = CheckpointManager.__new__(CheckpointManager)
        cm._storage = MagicMock()  # _storage 是@property的后备字段
        cm._storage.save.return_value = True
        cm.settings = MagicMock()
        cm.spider_name = 'test'
        cm.logger = MagicMock()

        # 记录调用顺序
        call_order = []

        async def mock_extract_pending(scheduler):
            call_order.append('extract_pending')
            return []

        def mock_extract_fingerprints(scheduler):
            call_order.append('extract_fingerprints')
            return set()

        cm._extract_pending_requests = mock_extract_pending
        cm._extract_fingerprints = mock_extract_fingerprints

        import asyncio
        asyncio.run(cm.save(MagicMock(), MagicMock()))

        self.assertEqual(len(call_order), 2)
        self.assertEqual(call_order[0], 'extract_fingerprints',
                         "指纹应先于请求提取")
        self.assertEqual(call_order[1], 'extract_pending')


# ---------- 4. engine close_spider SPIDER_CLOSED ----------

class TestEngineSpiderClosed(unittest.TestCase):
    """close_spider 异常时应触发 SPIDER_CLOSED 事件"""

    def test_spider_closed_fired_on_exception(self):
        from crawlo.core.engine import Engine
        import asyncio

        # 构造 engine 实例，mock 掉所有前置方法
        engine = Engine.__new__(Engine)
        engine._spider_closed = False
        engine._close_reason = 'finished'
        engine.task_manager = None
        engine.processor = None
        engine.scheduler = None
        engine._cluster_registry = None
        engine._cluster_failover = None
        engine._cluster_heartbeat = None
        engine._coordinated_shutdown_enabled = False
        engine.days = 1

        engine.downloader = None  # 跳过 downloader.close (有独立 try-except)

        # 关闭集群时抛出未预期异常（无独立 try-except，触发外层 except）
        engine._shutdown_cluster = AsyncMock(side_effect=RuntimeError("集群关闭失败"))

        # 跳过其他清理方法
        engine._cleanup_old_logs = AsyncMock(return_value=None)
        engine._save_checkpoint = AsyncMock(return_value=None)
        engine._clear_checkpoint = AsyncMock(return_value=None)
        engine._setup_failover = MagicMock(return_value=None)
        engine._setup_heartbeat = MagicMock(return_value=None)

        # 模拟 logger 和 crawler
        engine.logger = MagicMock()
        mock_subscriber = AsyncMock()
        engine.crawler = MagicMock()
        engine.crawler.subscriber = mock_subscriber

        try:
            asyncio.run(engine.close_spider('finished'))
        except RuntimeError:
            pass

        # 验证 SPIDER_CLOSED 事件被触发
        mock_subscriber.notify.assert_called_once()
        args, kwargs = mock_subscriber.notify.call_args
        # 确保回调参数含 reason='error'
        if 'reason' in kwargs:
            self.assertEqual(kwargs['reason'], 'error')
        elif len(args) > 1:
            self.assertEqual(args[1], 'error')


if __name__ == '__main__':
    unittest.main(verbosity=2)
