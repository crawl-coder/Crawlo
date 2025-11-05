#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
# -*- coding: utf-8 -*-

from crawlo.spider import Spider


class TestSpider(Spider):
    name = 'test_spider'
    
    def parse(self, response):
        pass