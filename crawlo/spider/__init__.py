#!/usr/bin/python
# -*- coding:UTF-8 -*-
from __future__ import annotations
from typing import Type, Any, Optional, List, Dict
from ..network.request import Request
from ..utils.log import get_logger


# 全局注册表
_DEFAULT_SPIDER_REGISTRY: dict[str, Type[Spider]] = {}


class SpiderMeta(type):
    def __new__(mcs, name: str, bases: tuple[type], namespace: dict[str, Any], **kwargs):
        cls = super().__new__(mcs, name, bases, namespace)

        is_spider_subclass = any(
            base is Spider or (isinstance(base, type) and issubclass(base, Spider))
            for base in bases
        )
        if not is_spider_subclass:
            return cls

        spider_name = namespace.get('name')
        if not isinstance(spider_name, str):
            raise AttributeError(f"爬虫类 '{cls.__name__}' 必须定义字符串类型的 'name' 属性。")

        if spider_name in _DEFAULT_SPIDER_REGISTRY:
            raise ValueError(
                f"爬虫名称 '{spider_name}' 已被 {_DEFAULT_SPIDER_REGISTRY[spider_name].__name__} 占用。"
                f"请确保每个爬虫的 name 属性全局唯一。"
            )

        _DEFAULT_SPIDER_REGISTRY[spider_name] = cls
        get_logger(__name__).debug(f"自动注册爬虫: {spider_name} -> {cls.__name__}")

        return cls


class Spider(metaclass=SpiderMeta):
    name: str = None

    def __init__(self, name=None, **kwargs):
        if not hasattr(self, 'start_urls'):
            self.start_urls = []
        self.crawler = None
        self.name = name or self.name
        self.logger = get_logger(self.name or self.__class__.__name__)

    @classmethod
    def create_instance(cls, crawler) -> Spider:
        o = cls()
        o.crawler = crawler
        return o

    def start_requests(self):
        if self.start_urls:
            for url in self.start_urls:
                yield Request(url=url, dont_filter=True)
        else:
            if hasattr(self, 'start_url') and isinstance(getattr(self, 'start_url'), str):
                yield Request(getattr(self, 'start_url'), dont_filter=True)

    def parse(self, response):
        raise NotImplementedError

    async def spider_opened(self):
        pass

    async def spider_closed(self):
        pass

    def __str__(self):
        return self.__class__.__name__


# === 公共只读接口 ===
def get_global_spider_registry() -> dict[str, Type[Spider]]:
    return _DEFAULT_SPIDER_REGISTRY.copy()


def get_spider_by_name(name: str) -> Optional[Type[Spider]]:
    return _DEFAULT_SPIDER_REGISTRY.get(name)


def get_all_spider_classes() -> list[Type[Spider]]:
    return list(set(_DEFAULT_SPIDER_REGISTRY.values()))

# #!/usr/bin/python
# # -*- coding:UTF-8 -*-
# from ..network.request import Request
# from ..utils.log import get_logger
#
#
# class Spider(object):
#     name = None
#
#     def __init__(self, name=None, **kwargs):
#         if not hasattr(self, 'start_urls'):
#             self.start_urls = []
#         self.crawler = None
#         self.name = name or self.name
#         self.logger = get_logger(self.name or self.__class__.__name__)
#
#     @classmethod
#     def create_instance(cls, crawler):
#         o = cls()
#         o.crawler = crawler
#         return o
#
#     def start_requests(self):
#         if self.start_urls:
#             for url in self.start_urls:
#                 yield Request(url=url, dont_filter=True)
#         else:
#             if hasattr(self, 'start_url') and isinstance(getattr(self, 'start_url'), str):
#                 yield Request(getattr(self, 'start_url'), dont_filter=True)
#
#     def parse(self, response):
#         raise NotImplementedError
#
#     async def spider_opened(self):
#         pass
#
#     async def spider_closed(self):
#         pass
#
#     def __str__(self):
#         return self.__class__.__name__
