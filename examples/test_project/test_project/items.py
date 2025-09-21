# -*- coding: UTF-8 -*-
"""
test_project.items
======================
定义你抓取的数据结构。
"""

from crawlo.items import Item, Field


class ExampleItem(Item):
    """
    一个示例数据项。
    """
    id = Field()
    # price = Field()
    # description = Field()
    pass


class NewsItem(Item):
    """
    新闻数据项。
    """
    title = Field()
    publish_time = Field()
    url = Field()
    source = Field()
    content = Field()