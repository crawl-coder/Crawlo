#!/usr/bin/python
# -*- coding:UTF-8 -*-
from typing import List, Any
from pprint import pformat

from crawlo.utils.log import get_logger
from crawlo.utils.class_loader import load_class
from crawlo.exceptions import ExtensionInitError


class ExtensionManager(object):

    def __init__(self, crawler: Any):
        self.crawler = crawler
        self.extensions: List = []
        extensions = self.crawler.settings.get_list('EXTENSIONS')
        self.logger = get_logger(self.__class__.__name__, crawler.settings.get('LOG_LEVEL'))
        self._add_extensions(extensions)
        self._subscribe_extensions()

    @classmethod
    def create_instance(cls, *args: Any, **kwargs: Any) -> 'ExtensionManager':
        return cls(*args, **kwargs)

    def _add_extensions(self, extensions: List[str]) -> None:
        for extension_path in extensions:
            try:
                extension_cls = load_class(extension_path)
                if not hasattr(extension_cls, 'create_instance'):
                    raise ExtensionInitError(
                        f"Extension '{extension_path}' init failed: Must have method 'create_instance()'"
                    )
                self.extensions.append(extension_cls.create_instance(self.crawler))
            except Exception as e:
                self.logger.error(f"Failed to load extension '{extension_path}': {e}")
                raise ExtensionInitError(f"Failed to load extension '{extension_path}': {e}")
        
        if extensions:
            # 恢复INFO级别日志，保留关键的启用信息
            self.logger.info(f"Enabled extensions: \n{pformat(extensions)}")

    def _subscribe_extensions(self) -> None:
        """订阅扩展方法到相应的事件"""
        for extension in self.extensions:
            # 订阅 spider_closed 方法
            if hasattr(extension, 'spider_closed'):
                self.crawler.subscriber.subscribe(extension.spider_closed, event="spider_closed")
            
            # 订阅 item_successful 方法
            if hasattr(extension, 'item_successful'):
                self.crawler.subscriber.subscribe(extension.item_successful, event="item_successful")
            
            # 订阅 item_discard 方法
            if hasattr(extension, 'item_discard'):
                self.crawler.subscriber.subscribe(extension.item_discard, event="item_discard")
            
            # 订阅 response_received 方法
            if hasattr(extension, 'response_received'):
                # 修复：将事件名称从 "request_received" 更正为 "response_received"
                self.crawler.subscriber.subscribe(extension.response_received, event="response_received")
            
            # 订阅 request_scheduled 方法
            if hasattr(extension, 'request_scheduled'):
                self.crawler.subscriber.subscribe(extension.request_scheduled, event="request_scheduled")