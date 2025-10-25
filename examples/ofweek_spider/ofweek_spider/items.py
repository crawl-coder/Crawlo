# -*- coding: UTF-8 -*-
"""
ofweek_spider.items
======================
定义你抓取的数据结构。
"""

from crawlo.items import Item, Field


class NewsItem(Item):
    """新闻数据项"""
    title = Field()
    publish_time = Field()
    url = Field()
    source = Field()
    content = Field()