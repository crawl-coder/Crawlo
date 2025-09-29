# -*- coding: UTF-8 -*-
"""
测试爬虫
"""
from crawlo.spider import Spider


class TestSpider(Spider):
    name = 'test_spider'
    
    def parse(self, response):
        pass