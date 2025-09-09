# -*- coding: UTF-8 -*-
"""
api_data_collection.items
========================
定义API数据采集项目的数据结构。
"""

from crawlo.items import Item, Field


class ApiDataItem(Item):
    """
    API数据项
    """
    # 基本信息字段
    id = Field(description="数据ID")
    name = Field(description="名称")
    description = Field(description="描述")
    category = Field(description="分类")
    price = Field(description="价格")
    status = Field(description="状态")
    created_at = Field(description="创建时间")
    updated_at = Field(description="更新时间")
    
    # 分布式特有字段
    crawl_time = Field(description="抓取时间")
    crawl_node = Field(description="爬取节点")
    data_version = Field(description="数据版本")