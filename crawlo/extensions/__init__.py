#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Extensions 模块 — 框架扩展组件

合并原 extension/（单数）和 bot/ 到统一 extensions/ 包。

Subpackages:
- extensions.monitor: 监控扩展（MemoryMonitorExtension / MySQLMonitorExtension / RedisMonitorExtension 等）
- extensions.notifications: 通知系统（原 bot/，FeishuChannel / EmailChannel 等）

Public API:
- ExtensionManager: 扩展管理器（原定义于 extension/__init__.py）
- MemoryMonitorExtension, MySQLMonitorExtension, RedisMonitorExtension
- HealthCheckExtension, LogStats, LogIntervalExtension
- CustomLoggerExtension, RequestRecorderExtension
"""
from typing import List, Any
from pprint import pformat

from crawlo.logging import get_logger
from crawlo.utils.misc import load_object
from crawlo.core.errors import ExtensionInitError
from crawlo.plugin import (
    register_extension,
    unregister_extension,
)


class ExtensionManager:

    def __init__(self, crawler: Any):
        self.crawler = crawler
        self.extensions: List = []
        extensions = self.crawler.settings.get_list('EXTENSIONS')
        self.logger = get_logger(self.__class__.__name__)
        self._add_extensions(extensions)
        self._subscribe_extensions()

    @classmethod
    def create_instance(cls, *args: Any, **kwargs: Any) -> 'ExtensionManager':
        return cls(*args, **kwargs)

    def _add_extensions(self, extensions: List[str]) -> None:
        from crawlo.core.errors import NotConfigured
        enabled_extensions = []

        for extension_path in extensions:
            try:
                extension_cls = load_object(extension_path)
                if not hasattr(extension_cls, 'create_instance'):
                    raise ExtensionInitError(
                        f"Extension '{extension_path}' init failed: Must have method 'create_instance()'"
                    )
                self.extensions.append(extension_cls.create_instance(self.crawler))
                enabled_extensions.append(extension_path)
            except NotConfigured as e:
                # 对于未配置启用的扩展，输出 DEBUG 级别日志（配置禁用是正常行为）
                self.logger.debug(f"Extension '{extension_path}' disabled: {e}")
            except Exception as e:
                self.logger.error(f"Failed to load extension '{extension_path}': {e}")
                raise ExtensionInitError(f"Failed to load extension '{extension_path}': {e}")

        # 只在有启用扩展时打印汇总信息
        if enabled_extensions:
            self.logger.info(f"Enabled extensions: \n{pformat(enabled_extensions)}")

    def _subscribe_extensions(self) -> None:
        """订阅扩展方法到相应的事件"""
        from crawlo.event import CrawlerEvent

        for extension in self.extensions:
            # 订阅 spider_closed 方法
            if hasattr(extension, 'spider_closed'):
                self.crawler.subscriber.subscribe(extension.spider_closed, event=CrawlerEvent.SPIDER_CLOSED)

            # 订阅 item_successful 方法
            if hasattr(extension, 'item_successful'):
                self.crawler.subscriber.subscribe(extension.item_successful, event=CrawlerEvent.ITEM_SUCCESSFUL)

            # 订阅 item_discard 方法
            if hasattr(extension, 'item_discard'):
                self.crawler.subscriber.subscribe(extension.item_discard, event=CrawlerEvent.ITEM_DISCARD)

            # 订阅 response_received 方法
            if hasattr(extension, 'response_received'):
                self.crawler.subscriber.subscribe(extension.response_received, event=CrawlerEvent.RESPONSE_RECEIVED)

            # 订阅 request_scheduled 方法
            if hasattr(extension, 'request_scheduled'):
                self.crawler.subscriber.subscribe(extension.request_scheduled, event=CrawlerEvent.REQUEST_SCHEDULED)


# ── 延迟导出扩展类（支持短路径：crawlo.extensions.LogIntervalExtension）──
def __getattr__(name):
    _MAPPING = {
        'LogIntervalExtension':      'crawlo.extensions.log_interval',
        'LogStats':                  'crawlo.extensions.log_stats',
        'CustomLoggerExtension':     'crawlo.extensions.logging',
        'MemoryMonitorExtension':    'crawlo.extensions.monitor.memory',
        'MySQLMonitorExtension':     'crawlo.extensions.monitor.mysql',
        'RedisMonitorExtension':     'crawlo.extensions.monitor.redis',
        'HealthCheckExtension':      'crawlo.extensions.health_check',
        'RequestRecorderExtension':  'crawlo.extensions.request_recorder',
        'EventloopLagProbe':         'crawlo.extensions.eventloop_lag',
    }
    if name in _MAPPING:
        import importlib
        mod = importlib.import_module(_MAPPING[name])
        cls = getattr(mod, name)
        return cls
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__all__ = [
    'ExtensionManager',
    'register_extension',
    'unregister_extension',
    'LogIntervalExtension',
    'LogStats',
    'CustomLoggerExtension',
    'MemoryMonitorExtension',
    'MySQLMonitorExtension',
    'RedisMonitorExtension',
    'HealthCheckExtension',
    'RequestRecorderExtension',
    'EventloopLagProbe',
]
