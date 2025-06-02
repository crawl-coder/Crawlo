#!/usr/bin/python
# -*- coding:UTF-8 -*-
from crawlo.event import spider_opened


class DefaultHeaderMiddleware(object):

    def __init__(self, user_agent, headers, spider):
        self.user_agent = user_agent
        self.headers = headers
        self.spider = spider

    @classmethod
    def create_instance(cls, crawler):
        o = cls(
            user_agent=crawler.settings.get('USER_AGENT'),
            headers=crawler.settings.get_dict('DEFAULT_HEADERS'),
            spider=crawler.spider
        )
        crawler.subscriber.subscribe(o.spider_opened, event=spider_opened)
        return o

    async def spider_opened(self):
        self.user_agent = getattr(self.spider, 'user_agent', self.user_agent)
        self.headers = getattr(self.spider, 'headers', self.headers)
        if self.user_agent:
            self.headers.setdefault('User-Agent', self.user_agent)

    def process_request(self, request, _spider):
        if self.headers:
            for key, value in self.headers.items():
                request.headers.setdefault(key, value)
