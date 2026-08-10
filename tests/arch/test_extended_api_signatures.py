#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
架构守护测试 — 扩展公共 API 签名快照（P0-A3）
=============================================

在 test_public_api_signatures.py（5 个核心类）基础上，把签名守护扩展到
api-surface.md 中标记 frozen 的核心类（25 类 / 227 个方法签名）。

守护范围
--------
http / items / spider / downloader / middleware / crawler 门面 /
engine / context / processor / scheduler / queue / stats / filters /
checkpoint / logging / backpressure / pipeline / event / utils。

规则（与 5 类基线一致）
------------------------
- 仅允许加新方法；不允许删除或修改已有公共方法 / property / classmethod 签名；
- 加新方法不会影响基线（逐方法比较，新增方法不在基线中自然不被检查）。

基线更新
--------
当且仅当签名变更经过评审且确认向后兼容时：

    python tests/arch/test_extended_api_signatures.py > /tmp/new.json
    cp /tmp/new.json tests/arch/api_signatures_baseline.json

基线文件：tests/arch/api_signatures_baseline.json（2026-08-10，P0-A3 首次建立）。
"""

import hashlib
import importlib
import inspect
import json
import re
from pathlib import Path

import pytest

BASELINE_FILE = Path(__file__).resolve().parent / "api_signatures_baseline.json"

# 扩展守护类清单（与 api-surface.md 的 frozen 状态一致）
GUARDED_CLASSES = [
    ("crawlo.http.request", "Request"),
    ("crawlo.http.response", "Response"),
    ("crawlo.items.item", "Item"),
    ("crawlo.items.fields", "Field"),
    ("crawlo.spider.spider", "Spider"),
    ("crawlo.downloader", "DownloaderBase"),
    ("crawlo.middleware", "BaseMiddleware"),
    ("crawlo.crawler._crawler", "Crawler"),
    ("crawlo.crawler._process", "CrawlerProcess"),
    ("crawlo.crawler._framework", "CrawloFramework"),
    ("crawlo.core.engine", "Engine"),
    ("crawlo.core.application", "ApplicationContext"),
    ("crawlo.core.processor", "Processor"),
    ("crawlo.core.scheduling.task_scheduler", "Scheduler"),
    ("crawlo.core.scheduling.task_manager", "TaskManager"),
    ("crawlo.queue.queue_manager", "QueueManager"),
    ("crawlo.stats.collector", "StatsCollector"),
    ("crawlo.filters", "BaseFilter"),
    ("crawlo.checkpoint.manager", "CheckpointManager"),
    ("crawlo.logging", "LogManager"),
    ("crawlo.queue.backpressure", "BackpressureController"),
    ("crawlo.middleware.middleware_manager", "MiddlewareManager"),
    ("crawlo.pipelines.base_pipeline", "BasePipeline"),
    ("crawlo.event", "Subscriber"),
    ("crawlo.utils.request.fingerprint", "FingerprintGenerator"),
    # ── 具体实现类（api-surface 中 frozen / optional）──
    ("crawlo.downloader.aiohttp_downloader", "AioHttpDownloader"),
    ("crawlo.downloader.httpx_downloader", "HttpXDownloader"),
    ("crawlo.downloader.hybrid_downloader", "HybridDownloader"),
    ("crawlo.middleware.retry", "RetryMiddleware"),
    ("crawlo.middleware.proxy", "ProxyMiddleware"),
    ("crawlo.middleware.cloudflare_bypass", "CloudflareBypassMiddleware"),
    ("crawlo.middleware.dynamic_render_middleware", "DynamicRenderMiddleware"),
    ("crawlo.middleware.download_delay", "DownloadDelayMiddleware"),
    ("crawlo.middleware.default_header", "DefaultHeaderMiddleware"),
    ("crawlo.middleware.request_ignore", "RequestIgnoreMiddleware"),
    ("crawlo.middleware.offsite", "OffsiteMiddleware"),
    ("crawlo.middleware.response_code", "ResponseCodeMiddleware"),
    ("crawlo.middleware.response_filter", "ResponseFilterMiddleware"),
    ("crawlo.queue.backends.memory", "SpiderPriorityQueue"),
    ("crawlo.queue.backends.disk", "DiskQueue"),
    ("crawlo.queue.backends.redis_priority", "RedisPriorityQueue"),
    ("crawlo.queue.backends.redis_stream", "RedisStreamQueue"),
    ("crawlo.stats.backends", "RedisStatsBackend"),
    ("crawlo.stats.backends", "FileStatsBackend"),
    ("crawlo.stats.backends", "StatsBackendFactory"),
    ("crawlo.pipelines.dedup.memory", "MemoryDedupPipeline"),
    ("crawlo.pipelines.dedup.redis", "RedisDedupPipeline"),
    ("crawlo.pipelines.console", "ConsolePipeline"),
    ("crawlo.extensions.log_interval", "LogIntervalExtension"),
    ("crawlo.extensions.health_check", "HealthCheckExtension"),
    ("crawlo.extensions.eventloop_lag", "EventloopLagProbe"),
    ("crawlo.cluster.heartbeat", "HeartbeatDaemon"),
    ("crawlo.cluster.failover", "FailoverManager"),
    ("crawlo.cluster.progress", "ProgressAggregator"),
    ("crawlo.cluster.rate_limiter", "DistributedRateLimiter"),
    ("crawlo.spider.loader", "SpiderLoader"),
    ("crawlo.spider.resolver", "SpiderResolver"),
]


def _signature_string(name, attr):
    """构造签名字符串：method_name(arg1, arg2, ...) -> ReturnType。"""
    if isinstance(attr, property):
        func = attr.fget
        if func is None:
            return None
    elif isinstance(attr, classmethod):
        func = attr.__func__
    elif isinstance(attr, staticmethod):
        func = attr.__func__
    elif callable(attr):
        func = attr
    else:
        return None
    try:
        sig = inspect.signature(func)
    except (ValueError, TypeError):
        return None
    sig_str = str(sig)
    # 归一化 object() 哨兵默认值（repr 含内存地址，跨进程不稳定）：
    # (self, key, default=<object object at 0x...>) → (self, key, default=<object>)
    sig_str = re.sub(r"<object object at 0x[0-9a-fA-F]+>", "<object>", sig_str)
    return f"{name}{sig_str}"


def _public_members(cls):
    """枚举类的公共成员（含继承，排除 object 继承与 dunder，保留 __init__）。"""
    members = {}
    for klass in cls.__mro__:
        if klass is object:
            continue
        for name, attr in vars(klass).items():
            if name in members:
                continue  # 子类已覆盖，跳过父类版本
            if name.startswith('_') and name != '__init__':
                continue
            if name.startswith('__') and name.endswith('__') and name != '__init__':
                continue
            if callable(attr) or isinstance(attr, (property, staticmethod, classmethod)):
                members[name] = attr
    return members


def _signature_hash(name, attr):
    sig_str = _signature_string(name, attr)
    if sig_str is None:
        return None
    return hashlib.sha256(sig_str.encode('utf-8')).hexdigest()


def _load_baseline():
    return json.loads(BASELINE_FILE.read_text(encoding="utf-8"))


def _current_hashes():
    """计算当前所有守护类的签名哈希。"""
    current = {}
    for mod_name, cls_name in GUARDED_CLASSES:
        cls = getattr(importlib.import_module(mod_name), cls_name)
        key = f"{mod_name}.{cls_name}"
        current[key] = {}
        for name, attr in sorted(_public_members(cls).items()):
            h = _signature_hash(name, attr)
            if h is not None:
                current[key][name] = h
    return current


@pytest.mark.parametrize("class_key", [f"{m}.{c}" for m, c in GUARDED_CLASSES])
def test_frozen_class_signatures(class_key):
    """api-surface.md frozen 类的公共方法签名与基线一致。"""
    baseline = _load_baseline()
    assert class_key in baseline, (
        f"{class_key} 不在签名基线中。若为新增守护类，请先建立基线。"
    )
    current = _current_hashes()[class_key]
    failures = []
    for method_name, expected in baseline[class_key].items():
        actual = current.get(method_name)
        if actual is None:
            failures.append(f"  {class_key}.{method_name}: 已被删除或改为私有")
        elif actual != expected:
            failures.append(
                f"  {class_key}.{method_name}: 签名变更\n"
                f"    基线: {expected}\n"
                f"    当前: {actual}"
            )
    assert not failures, (
        "frozen 公共 API 签名发生变更。必须走 Deprecation 周期，不能直接改签名。\n"
        + "\n".join(failures)
        + "\n如确需变更（经评审），运行脚本更新基线：\n"
        "  python tests/arch/test_extended_api_signatures.py > /tmp/new.json\n"
        "  cp /tmp/new.json tests/arch/api_signatures_baseline.json"
    )


def test_baseline_covers_all_guarded_classes():
    """基线文件必须覆盖全部守护类（防基线遗漏）。"""
    baseline = _load_baseline()
    keys = {f"{m}.{c}" for m, c in GUARDED_CLASSES}
    missing = sorted(keys - set(baseline))
    assert not missing, f"基线缺少守护类: {missing}"


if __name__ == "__main__":
    import sys

    print(json.dumps(_current_hashes(), indent=2, sort_keys=True))
    print(f"# {len(_current_hashes())} classes, "
          f"{sum(len(v) for v in _current_hashes().values())} signatures", file=sys.stderr)
