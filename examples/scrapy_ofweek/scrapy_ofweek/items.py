# -*- coding: UTF-8 -*-
"""
scrapy_ofweek.items
===================
定义抓取的数据结构。
"""

import scrapy


class NewsItem(scrapy.Item):
    """新闻数据项"""
    title = scrapy.Field()
    publish_time = scrapy.Field()
    url = scrapy.Field()
    source = scrapy.Field()
    content = scrapy.Field()
