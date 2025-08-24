#!/usr/bin/python
# -*- coding:UTF-8 -*-
from ..network.request import Request
from ..utils.log import get_logger


class Spider(object):
    name = None

    def __init__(self, name=None, **kwargs):
        if not hasattr(self, 'start_urls'):
            self.start_urls = []
        self.crawler = None
        self.name = name or self.name
        self.logger = get_logger(self.name or self.__class__.__name__)

    @classmethod
    def create_instance(cls, crawler):
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
