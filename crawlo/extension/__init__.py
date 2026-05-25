#!/usr/bin/python
# -*- coding:UTF-8 -*-
from typing import List, Any
from pprint import pformat

from crawlo.logging import get_logger
from crawlo.utils.misc import load_object
from crawlo.exceptions import ExtensionInitError


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
        from crawlo.exceptions import NotConfigured
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


# ── 延迟导出扩展类（支持短路径：crawlo.extension.LogIntervalExtension）──
def __getattr__(name):
    _MAPPING = {
        'LogIntervalExtension':      'crawlo.extension.log_interval',
        'LogStats':                  'crawlo.extension.log_stats',
        'CustomLoggerExtension':     'crawlo.extension.logging_extension',
        'MemoryMonitorExtension':    'crawlo.extension.memory_monitor',
        'MySQLMonitorExtension':     'crawlo.extension.mysql_monitor',
        'RedisMonitorExtension':     'crawlo.extension.redis_monitor',
        'HealthCheckExtension':      'crawlo.extension.health_check',
        'RequestRecorderExtension':  'crawlo.extension.request_recorder',
    }
    if name in _MAPPING:
        import importlib
        mod = importlib.import_module(_MAPPING[name])
        cls = getattr(mod, name)
        return cls
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__all__ = [
    'ExtensionManager',
    'LogIntervalExtension',
    'LogStats',
    'CustomLoggerExtension',
    'MemoryMonitorExtension',
    'MySQLMonitorExtension',
    'RedisMonitorExtension',
    'HealthCheckExtension',
    'RequestRecorderExtension',
]