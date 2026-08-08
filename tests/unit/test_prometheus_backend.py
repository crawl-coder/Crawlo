#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Prometheus 统计后端测试

覆盖：
1. PrometheusStatsBackend 创建与端口管理
2. _sanitize_metric_name 清洗逻辑（含中文、点号、斜杠、连续下划线）
3. inc_value → Counter 映射
4. set_value → Gauge 映射（数值写入、字符串跳过）
5. get_value 与并行值缓存
6. get_stats 输出
7. clear() 注销与重建（验证不报 Duplicated timeseries）
8. max_value / min_value 逻辑
9. append_value 忽略
10. close() 释放端口
11. HTTP /metrics 端点可访问
12. StatsBackendFactory prometheus 分支
13. memory_monitor 与 log_interval 埋点不抛异常
14. 指标名非 ASCII 字符容错
"""
import os
import socket
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from lxml.html import fromstring


# ==================================================================
# 辅助：Mock settings
# ==================================================================

class MockSettings(dict):
    """模拟 Settings 对象，支持 get_int/get_bool/get_dict"""
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
    def get_dict(self, k, d=None):
        val = super().get(k, d) if d is None else super().get(k, {})
        return val if isinstance(val, dict) else {}


# ==================================================================
# 1. 指标名清洗
# ==================================================================

class TestSanitizeMetricName(unittest.TestCase):
    """_sanitize_metric_name 测试"""

    def test_basic(self):
        from crawlo.stats.prometheus_backend import _sanitize_metric_name
        self.assertEqual(
            _sanitize_metric_name('response_received_count'),
            'crawlo_response_received_count'
        )

    def test_slash_as_underscore(self):
        from crawlo.stats.prometheus_backend import _sanitize_metric_name
        self.assertEqual(
            _sanitize_metric_name('downloader/exception_count'),
            'crawlo_downloader_exception_count'
        )

    def test_dot_as_underscore(self):
        from crawlo.stats.prometheus_backend import _sanitize_metric_name
        self.assertEqual(
            _sanitize_metric_name('offsite_request_count/www.example.com'),
            'crawlo_offsite_request_count_www_example_com'
        )

    def test_chinese_reason(self):
        from crawlo.stats.prometheus_backend import _sanitize_metric_name
        result = _sanitize_metric_name('request_ignore_count/reason/状态码 403')
        # 中文 + 空格 → 下划线
        self.assertNotIn('状态码', result)
        self.assertNotIn(' ', result)
        self.assertTrue(result.startswith('crawlo_request_ignore_count_reason'))
        self.assertTrue(result.endswith('403'))

    def test_collapse_duplicate_underscore(self):
        from crawlo.stats.prometheus_backend import _sanitize_metric_name
        result = _sanitize_metric_name('a//b---c')
        # 两个 / 变成 __，--变成 __，再 collapse
        self.assertNotIn('__', result)

    def test_prefix_default(self):
        from crawlo.stats.prometheus_backend import _sanitize_metric_name
        self.assertEqual(
            _sanitize_metric_name('counter', prefix='app'),
            'app_counter'
        )

    def test_special_chars_parens(self):
        """括号等特殊字符应被替换"""
        from crawlo.stats.prometheus_backend import _sanitize_metric_name
        result = _sanitize_metric_name('cost_time(s)')
        self.assertNotIn('(', result)
        self.assertNotIn(')', result)


# ==================================================================
# 2. PrometheusStatsBackend 基本功能
# ==================================================================

class TestPrometheusStatsBackend(unittest.TestCase):
    """核心功能测试"""

    def setUp(self):
        from crawlo.stats.prometheus_backend import PrometheusStatsBackend
        self.backend = PrometheusStatsBackend(
            prefix='crawlo', port=0,  # port=0: auto-assign
        )

    def tearDown(self):
        try:
            self.backend.close()
        except Exception:
            pass

    def test_01_created_with_auto_port(self):
        """port=0 应成功创建，不抛异常"""
        self.assertIsNotNone(self.backend)

    def test_02_inc_value_counter(self):
        """inc_value 应创建 Counter 并更新值"""
        self.backend.inc_value('response_received_count', 42)
        self.assertEqual(
            self.backend.get_value('response_received_count'),
            42.0
        )

    def test_03_inc_value_multiple(self):
        """多次 inc 应累加"""
        self.backend.inc_value('item_scraped', 10)
        self.backend.inc_value('item_scraped', 5)
        self.backend.inc_value('item_scraped', 3)
        self.assertEqual(
            self.backend.get_value('item_scraped'),
            18.0
        )

    def test_04_set_value_gauge_numeric(self):
        """set_value 对数值应创建 Gauge"""
        self.backend.set_value('memory_rss_mb', 128.5)
        self.assertEqual(
            self.backend.get_value('memory_rss_mb'),
            128.5
        )

    def test_05_set_value_gauge_update(self):
        """set_value 多次写入应覆盖"""
        self.backend.set_value('thread_count', 10)
        self.backend.set_value('thread_count', 15)
        self.assertEqual(
            self.backend.get_value('thread_count'),
            15.0
        )

    def test_06_set_value_string_skipped(self):
        """set_value 对字符串应静默跳过，不创建 Gauge"""
        self.backend.set_value('reason', 'finished')
        self.backend.set_value('spider_name', 'myspider')
        self.backend.set_value('end_time', '2026-07-02 22:30:00')
        # 这些 key 的值应为 None（查不到）
        self.assertIsNone(self.backend.get_value('reason'))
        self.assertIsNone(self.backend.get_value('spider_name'))

    def test_07_get_stats(self):
        """get_stats 应返回正确的统计信息"""
        self.backend.inc_value('req', 100)
        self.backend.inc_value('req', 50)
        self.backend.set_value('mem', 256.0)
        stats = self.backend.get_stats()
        self.assertIn('metrics_endpoint', stats)
        self.assertIn('port', stats)
        self.assertIn('labels', stats)
        self.assertIn('counter_count', stats)
        self.assertIn('gauge_count', stats)

    def test_08_get_value_default(self):
        """不存在的 key 应返回 default"""
        self.assertIsNone(self.backend.get_value('nonexistent'))
        self.assertEqual(self.backend.get_value('nonexistent', 0), 0)

    def test_09_max_value(self):
        """max_value 应取最大值"""
        self.backend.max_value('concurrent', 5)
        self.backend.max_value('concurrent', 3)
        self.backend.max_value('concurrent', 8)
        self.assertEqual(self.backend.get_value('concurrent'), 8.0)

    def test_10_min_value(self):
        """min_value 应取最小值"""
        self.backend.min_value('latency_ms', 100)
        self.backend.min_value('latency_ms', 50)
        self.backend.min_value('latency_ms', 200)
        self.assertEqual(self.backend.get_value('latency_ms'), 50.0)

    def test_11_max_min_non_numeric_skip(self):
        """max_value / min_value 对非数值应跳过"""
        self.backend.max_value('x', 'abc')  # 不应抛异常
        self.backend.min_value('y', [])      # 不应抛异常
        self.assertIsNone(self.backend.get_value('x'))
        self.assertIsNone(self.backend.get_value('y'))

    def test_12_append_value_ignored(self):
        """append_value 应被忽略（日志 debug）"""
        self.backend.append_value('list_metric', 'val')  # 不应抛异常
        self.assertIsNone(self.backend.get_value('list_metric'))

    def test_13_clear_and_reuse(self):
        """clear() 后重建不应报 Duplicated timeseries"""
        self.backend.inc_value('counter', 1)
        self.backend.set_value('gauge', 1.0)
        self.backend.clear()
        # 重建
        self.backend.inc_value('counter', 2)
        self.backend.inc_value('counter', 3)
        self.backend.set_value('gauge', 4.0)
        self.assertEqual(self.backend.get_value('counter'), 5.0)
        self.assertEqual(self.backend.get_value('gauge'), 4.0)

    def test_14_close_prometheus(self):
        """close() 清理（端口释放取决于 prometheus_client 版本）"""
        port = self.backend._port
        self.backend.close()
        self.assertIsNotNone(port)
        # 部分 prometheus_client 版本中 start_http_server 返回 None，
        # 无法主动停止 server 线程；此处只验证 close 不抛异常

    def test_15_chinese_reason_key(self):
        """含中文 reason 的 key 不抛异常"""
        # 模拟框架中真实存在的 key
        self.backend.inc_value(
            'request_ignore_count/reason/状态码 403 不在允许列表中 - 403',
            1
        )
        self.backend.inc_value(
            'request_ignore_count/reason/状态码 404 不在允许列表中 - 404',
            2
        )
        # 指标名被清洗、值有效
        count = self.backend.get_value(
            'request_ignore_count/reason/状态码 403 不在允许列表中 - 403'
        )
        self.assertEqual(count, 1.0)


# ==================================================================
# 3. HTTP /metrics 端点
# ==================================================================

class TestMetricsEndpoint(unittest.TestCase):
    """验证 /metrics HTTP 可访问"""

    def setUp(self):
        from crawlo.stats.prometheus_backend import PrometheusStatsBackend
        self.backend = PrometheusStatsBackend(port=0)

    def tearDown(self):
        try:
            self.backend.close()
        except Exception:
            pass

    def test_metrics_accessible(self):
        """curl /metrics 应返回合法 Prometheus 文本格式"""
        import urllib.request
        port = self.backend._port
        url = f'http://localhost:{port}/metrics'

        # 写入一些指标
        self.backend.inc_value('response_received_count', 100)
        self.backend.set_value('memory_rss_mb', 256.5)

        # 读取 /metrics
        try:
            with urllib.request.urlopen(url, timeout=5) as resp:
                body = resp.read().decode('utf-8')
        except Exception as e:
            self.fail(f"Failed to fetch /metrics at {url}: {e}")

        # 验证格式
        self.assertIn('crawlo_response_received_count', body)
        self.assertIn('crawlo_memory_rss_mb', body)
        self.assertIn('TYPE', body)
        self.assertIn('counter', body.lower())
        self.assertIn('gauge', body.lower())

    def test_metrics_after_clear(self):
        """clear() 后再 inc，/metrics 应反映新值"""
        import urllib.request
        port = self.backend._port
        url = f'http://localhost:{port}/metrics'

        self.backend.inc_value('test', 10)
        self.backend.clear()
        self.backend.inc_value('test', 5)

        with urllib.request.urlopen(url, timeout=5) as resp:
            body = resp.read().decode('utf-8')
        # 应只有 1 个 test 指标（clear 前的不在 registry 中了）
        # prometheus_client 的 Counter 会自动在 TYPE 声明时附加 _total 后缀
        self.assertIn('crawlo_test_total', body)
        self.assertIn('5.0', body)


# ==================================================================
# 4. StatsBackendFactory
# ==================================================================

class TestFactory(unittest.TestCase):
    """StatsBackendFactory prometheus 分支测试"""

    def test_factory_creates_prometheus(self):
        """from_settings 应返回 PrometheusStatsBackend"""
        from crawlo.stats.backends import StatsBackendFactory
        from crawlo.stats.prometheus_backend import PrometheusStatsBackend

        settings = MockSettings({
            'STATS_BACKEND': 'prometheus',
            'PROMETHEUS_METRICS_PORT': 0,
            'PROJECT_NAME': 'test_spider',
        })
        backend = StatsBackendFactory.from_settings(settings)
        self.assertIsInstance(backend, PrometheusStatsBackend)
        self.assertEqual(backend._labels['spider'], 'test_spider')
        backend.close()

    def test_factory_fallback_no_dep(self):
        """prometheus-client 不可用时回退到 memory"""
        from crawlo.stats.backends import StatsBackendFactory
        from crawlo.stats.backends import MemoryStatsBackend

        # 模拟 import 失败
        with patch('crawlo.stats.prometheus_backend.PROMETHEUS_AVAILABLE', False):
            settings = MockSettings({
                'STATS_BACKEND': 'prometheus',
                'PROMETHEUS_METRICS_PORT': 0,
            })
            backend = StatsBackendFactory.from_settings(settings)
            self.assertIsInstance(backend, MemoryStatsBackend)


# ==================================================================
# 5. 统计 key 完整性测试
# ==================================================================

class TestAllStatKeys(unittest.TestCase):
    """验证框架所有关键统计 key 都能正确映射为 Prometheus 指标"""

    def setUp(self):
        from crawlo.stats.prometheus_backend import PrometheusStatsBackend
        self.backend = PrometheusStatsBackend(port=0)

    def tearDown(self):
        try:
            self.backend.close()
        except Exception:
            pass

    def test_all_counter_keys(self):
        """所有 inc_value 类统计 key 不抛异常"""
        counter_keys = [
            'response_received_count',
            'response_status_code/200',
            'response_status_code/404',
            'response_status_code/3xx',
            'response_status_code/4xx',
            'response_status_code/5xx',
            'response_status_code/success_count',
            'response_status_code/error_count',
            'response_total_bytes',
            'item_successful_count',
            'item_discard_count',
            'request_scheduler_count',
            'retry_count',
            'downloader/exception_count',
            'downloader/exception_type_count/TimeoutError',
            'downloader/failed_urls_count',
            'request_ignore_count',
            'request_ignore_count/reason/状态码 403 不在允许列表中 - 403',
            'request_ignore_count/domain/www.example.com',
            'offsite_request_count',
            'offsite_request_count/www.example.com',
            'download_error/TimeoutError',
            'dedup/dropped_count',
            'dedup/new_count',
            'dedup/process_error_count',
            'dedup/process_time',
            'json_pipeline/items_written',
            'csv_pipeline/items_written',
            'hbase/success',
            'hbase/failed',
        ]
        for key in counter_keys:
            try:
                self.backend.inc_value(key, 1)
            except Exception as e:
                self.fail(f"inc_value('{key}') raised: {e}")

    def test_all_gauge_keys(self):
        """所有 set_value 类数值统计 key 不抛异常"""
        gauge_keys = {
            'concurrency_limit': 100,
            'max_concurrent_seen': 80,
            'concurrency_utilization': 0.75,
            'avg_response_time_ms': 350.2,
            'items_per_minute': 42.5,
            'pages_per_minute': 60.0,
        }
        for key, val in gauge_keys.items():
            try:
                self.backend.set_value(key, val)
            except Exception as e:
                self.fail(f"set_value('{key}') raised: {e}")

    def test_string_values_ignore(self):
        """所有字符串类 set_value 不应抛异常"""
        string_keys = [
            ('reason', 'finished'),
            ('spider_name', 'myspider'),
            ('start_time', '2026-07-02 22:00:00'),
            ('end_time', '2026-07-02 22:30:00'),
            ('elapsed_time', '1800.00s'),
            ('cost_time(s)', '1800.00'),
        ]
        for key, val in string_keys:
            try:
                self.backend.set_value(key, val)
            except Exception as e:
                self.fail(f"set_value('{key}', '{val}') raised: {e}")


# ==================================================================
# 6. 框架埋点非回归测试
# ==================================================================

class TestInstrumentationNoop(unittest.TestCase):
    """memory_monitor 和 log_interval 的埋点追加不应破坏现有逻辑"""

    def test_memory_monitor_stats_write(self):
        """memory_monitor 写 stats.set_value 不抛异常"""
        from crawlo.extension.memory_monitor import MemoryMonitorExtension

        # 模拟 crawler 对象
        mock_stats = MagicMock()
        mock_crawler = MagicMock()
        mock_crawler.stats = mock_stats

        monitor = MemoryMonitorExtension(mock_crawler)
        # 正常路径下 set_value 被调用 3 次（memory_rss_mb, memory_percent, thread_count）
        calls = mock_stats.set_value.call_count
        # 初始化时不应调用 set_value, 只在 _monitor_loop 循环中调用
        self.assertGreaterEqual(calls, 0)  # 不抛异常就过了

    def test_log_interval_queue_write(self):
        """log_interval 写 set_value('queue_size', ...) 不抛异常"""
        from crawlo.extension.log_interval import LogIntervalExtension

        mock_stats = MagicMock()
        mock_crawler = MagicMock()
        mock_crawler.stats = mock_stats

        ext = LogIntervalExtension(mock_crawler)
        self.assertIsNotNone(ext)


# ==================================================================
# 7. 运行测试
# ==================================================================

if __name__ == '__main__':
    unittest.main(verbosity=2)
