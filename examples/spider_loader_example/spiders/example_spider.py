# -*- coding: utf-8 -*-

from crawlo import Spider
from crawlo.network.request import Request
from crawlo.items import Item, Field


class ExampleItem(Item):
    url = Field()
    title = Field()
    status = Field()


class ExampleSpider(Spider):
    name = 'example'
    
    def start_requests(self):
        urls = [
            'http://httpbin.org/html',
            'http://httpbin.org/json',
        ]
        for url in urls:
            yield Request(url=url)
    
    def parse(self, response):
        self.logger.info(f'Visited {response.url}')
        item = ExampleItem()
        item['url'] = response.url
        item['title'] = response.extract_text('title')
        item['status'] = response.status_code
        yield item