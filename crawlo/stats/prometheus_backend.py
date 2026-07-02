#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Prometheus 统计后端
===================
将 Crawlo 框架内部统计 key 自动映射为 Prometheus 指标，
并在指定端口暴露 /metrics 端点供 Prometheus Server 拉取。

使用方式：
    # settings.py
    STATS_BACKEND = 'prometheus'
    PROMETHEUS_METRICS_PORT = 9100      # 设为 0 则自动分配可用端口

依赖：
    pip install crawlo[monitoring]
    # 或 pip install prometheus-client>=0.19.0

映射规则（简单且可预测）：
    - inc_value(key, count) -> Counter（累计型，首次出现时创建）
    - set_value(key, value) -> Gauge（仅数值；字符串值自动跳过）
"""
import atexit
import logging
import os
import re
import socket
from typing import Any, Dict, Optional

from crawlo.stats.backends import StatsBackend

try:
    from prometheus_client import Counter, Gauge, CollectorRegistry
    from prometheus_client.exposition import start_http_server
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

logger = logging.getLogger(__name__)

# 任何非 [a-zA-Z0-9_] 字符统一替换为下划线。
# 覆盖：斜杠、连字符、点（hostname）、括号、中文 reason 等。
_INVALID_CHARS = re.compile(r'[^a-zA-Z0-9_]')


def _sanitize_metric_name(key: str, prefix: str = "crawlo") -> str:
    """将框架 key 转换为合法 Prometheus 指标名。

    示例：
        'response_received_count'              -> 'crawlo_response_received_count'
        'downloader/exception_count'           -> 'crawlo_downloader_exception_count'
        'offsite_request_count/www.example.com'-> 'crawlo_offsite_request_count_www_example_com'
        'request_ignore_count/reason/状态码 403'-> 'crawlo_request_ignore_count_reason_403'
    """
    name = _INVALID_CHARS.sub('_', key.lower())
    while '__' in name:
        name = name.replace('__', '_')
    name = name.strip('_')
    return f"{prefix}_{name}"


class PrometheusStatsBackend(StatsBackend):
    """Prometheus 统计后端

    映射规则（简单且可预测，不做后缀猜测）：
        - inc_value(key, count)  -> Counter（累计型，key 首次出现时创建）
        - set_value(key, value)  -> Gauge（仅当 value 可转为 float；字符串值自动跳过）

    为什么不做后缀自动判型：
        框架 key 命名并不统一（如 'response_total_bytes' 用 inc_value，
        'avg_response_time_ms' 用 set_value），靠后缀猜类型既不可靠也无必要——
        调用方已通过选择 inc_value / set_value 表达了语义。
    """

    def __init__(
        self,
        prefix: str = "crawlo",
        port: int = 9100,
        labels: Optional[Dict[str, str]] = None,
        registry: Optional[CollectorRegistry] = None,
    ):
        if not PROMETHEUS_AVAILABLE:
            raise ImportError(
                "prometheus-client is required for PrometheusStatsBackend.\n"
                "Install: pip install crawlo[monitoring]"
            )

        self._prefix = prefix
        self._labels = labels or {'spider': 'default', 'worker_id': 'default'}
        self._registry = registry or CollectorRegistry()

        # 指标对象缓存；值为 None 表示该 key 因指标名非法被跳过
        self._counters: Dict[str, Optional[Counter]] = {}
        self._gauges: Dict[str, Optional[Gauge]] = {}
        # 并行值缓存：用于 get_value / max_value / min_value，避免私有 API
        self._counter_values: Dict[str, float] = {}
        self._gauge_values: Dict[str, float] = {}

        # 启动 HTTP server（port=0 时由系统分配可用端口）
        self._httpd = None
        self._port = port
        try:
            # 版本兼容：部分 prometheus_client 版本中 start_http_server 返回 None，
            # 此时无法通过返回值获取实际端口。若 port=0，先找一个空闲端口再启动。
            if port == 0:
                port = self._find_free_port()
                self._port = port

            self._httpd = start_http_server(port, registry=self._registry)
            # 若有返回值且含 server_address，则解析实际端口
            if self._httpd is not None:
                srv = getattr(self._httpd, 'server', self._httpd)
                if hasattr(srv, 'server_address'):
                    self._port = srv.server_address[1]

            logger.info(
                f"Prometheus metrics endpoint started on "
                f"http://0.0.0.0:{self._port}/metrics "
                f"(labels={self._labels})"
            )
        except OSError as e:
            logger.error(f"Failed to start Prometheus HTTP server on port {port}: {e}")
            raise

        atexit.register(self.close)

    @staticmethod
    def _find_free_port() -> int:
        """查找一个空闲端口（用于 port=0 自动分配场景）"""
        import socket as _socket
        with _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            return s.getsockname()[1]

    def _label_names(self):
        """返回当前标签键列表（用于创建 Counter/Gauge 时注册 labelnames）"""
        return list(self._labels.keys())

    def _get_or_create_counter(self, name: str, key: str) -> Optional[Counter]:
        if name not in self._counters:
            try:
                self._counters[name] = Counter(
                    name, f'Auto-generated from "{key}"',
                    self._label_names(), registry=self._registry,
                )
            except ValueError:
                # 指标名仍不合法（_sanitize_metric_name 已处理，此处兜底）
                logger.debug(f"Skip non-prometheus metric key (invalid name): {key}")
                self._counters[name] = None
        return self._counters[name]

    def _get_or_create_gauge(self, name: str, key: str) -> Optional[Gauge]:
        if name not in self._gauges:
            try:
                self._gauges[name] = Gauge(
                    name, f'Auto-generated from "{key}"',
                    self._label_names(), registry=self._registry,
                )
            except ValueError:
                logger.debug(f"Skip non-prometheus metric key (invalid name): {key}")
                self._gauges[name] = None
        return self._gauges[name]

    # ── StatsBackend 接口实现 ──────────────────────────

    def inc_value(self, key: str, count: int = 1) -> None:
        try:
            amount = float(count)
        except (TypeError, ValueError):
            return
        name = _sanitize_metric_name(key, self._prefix)
        metric = self._get_or_create_counter(name, key)
        if metric is not None:
            metric.labels(**self._labels).inc(amount)
        self._counter_values[name] = self._counter_values.get(name, 0.0) + amount

    def set_value(self, key: str, value: Any) -> None:
        # 仅数值映射为 Gauge；字符串值（reason / spider_name / end_time
        # / start_time / elapsed_time 等）跳过，Prometheus 不表达文本
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return
        name = _sanitize_metric_name(key, self._prefix)
        metric = self._get_or_create_gauge(name, key)
        if metric is not None:
            metric.labels(**self._labels).set(numeric)
        self._gauge_values[name] = numeric

    def get_value(self, key: str, default: Any = None) -> Any:
        name = _sanitize_metric_name(key, self._prefix)
        if name in self._gauge_values:
            return self._gauge_values[name]
        if name in self._counter_values:
            return self._counter_values[name]
        return default

    def get_stats(self) -> Dict[str, Any]:
        return {
            'metrics_endpoint': f'http://0.0.0.0:{self._port}/metrics',
            'port': self._port,
            'labels': self._labels,
            'counter_count': sum(1 for v in self._counters.values() if v is not None),
            'gauge_count': sum(1 for v in self._gauges.values() if v is not None),
        }

    def clear(self) -> None:
        """从注册表注销所有指标，避免清空后再次 inc/set 时报
        'Duplicated timeseries'。"""
        for metric in list(self._counters.values()):
            if metric is not None:
                try:
                    self._registry.unregister(metric)
                except Exception:
                    pass
        for metric in list(self._gauges.values()):
            if metric is not None:
                try:
                    self._registry.unregister(metric)
                except Exception:
                    pass
        self._counters.clear()
        self._gauges.clear()
        self._counter_values.clear()
        self._gauge_values.clear()

    def max_value(self, key: str, value: Any) -> None:
        try:
            v = float(value)
        except (TypeError, ValueError):
            return
        name = _sanitize_metric_name(key, self._prefix)
        current = self._gauge_values.get(name)
        if current is None or v > current:
            self.set_value(key, v)

    def min_value(self, key: str, value: Any) -> None:
        try:
            v = float(value)
        except (TypeError, ValueError):
            return
        name = _sanitize_metric_name(key, self._prefix)
        current = self._gauge_values.get(name)
        if current is None or v < current:
            self.set_value(key, v)

    def append_value(self, key: str, value: Any) -> None:
        """Prometheus 指标模型不表达列表；忽略以避免对非数值转 float 报错。"""
        logger.debug(
            f"append_value ignored for '{key}' (Prometheus models scalars only)"
        )

    def close(self) -> None:
        """停止内嵌 HTTP server 线程并释放端口。"""
        httpd = getattr(self, '_httpd', None)
        if httpd is not None:
            shutdown = getattr(httpd, 'shutdown', None)
            if callable(shutdown):
                try:
                    shutdown()
                except Exception:
                    pass
            self._httpd = None
        logger.debug("PrometheusStatsBackend closed (port=%s).", self._port)
