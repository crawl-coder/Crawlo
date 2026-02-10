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
        for extension_path in extensions:
            try:
                extension_cls = load_object(extension_path)
                if not hasattr(extension_cls, 'create_instance'):
                    raise ExtensionInitError(
                        f"Extension '{extension_path}' init failed: Must have method 'create_instance()'"
                    )
                self.extensions.append(extension_cls.create_instance(self.crawler))
            except NotConfigured as e:
                # 对于未配置启用的扩展，仅输出提示信息，不记录为错误
                self.logger.info(f"Extension '{extension_path}' is disabled: {e}")
            except Exception as e:
                self.logger.error(f"Failed to load extension '{extension_path}': {e}")
                raise ExtensionInitError(f"Failed to load extension '{extension_path}': {e}")
        
        if extensions:
            # 恢复INFO级别日志，保留关键的启用信息
            self.logger.info(f"Enabled extensions: \n{pformat(extensions)}")

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