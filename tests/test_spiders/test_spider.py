# -*- coding: utf-8 -*-

from crawlo.spider import Spider


class TestSpider(Spider):
    name = 'test_spider'
    
    def parse(self, response):
        pass