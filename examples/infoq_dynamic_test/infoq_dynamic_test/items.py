# -*- coding: UTF-8 -*-
"""
数据项定义
"""
from crawlo.items import Item, Field


class InfoqArticle(Item):
    """InfoQ 文章数据项"""
    url = Field()
    title = Field()
    author = Field()
    date = Field()
    publish_time = Field()
    summary = Field()
    content = Field()
    content_html = Field()
    source = Field()
    type = Field()
    note = Field()
    status = Field()
    text_length = Field()


