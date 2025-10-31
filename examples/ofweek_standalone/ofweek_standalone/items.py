# -*- coding: UTF-8 -*-
"""
数据项定义
"""

from crawlo.items import Item, Field


class OfWeekStandaloneItem(Item):
    """
    ofweek_standalone 项目的数据项。
    """
    title = Field()
    publish_time = Field()
    url = Field()
    source = Field()
    content = Field()