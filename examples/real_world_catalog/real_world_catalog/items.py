# -*- coding: UTF-8 -*-
"""Catalog 数据模型。"""

from crawlo.items import Field, Item


class CatalogItem(Item):
    """商品条目：列表页与详情页合并后的最终数据。"""

    url = Field()
    title = Field()
    price = Field()
    category = Field()
    description = Field(nullable=True, default="")
    sku = Field(nullable=True, default="")
    in_stock = Field(nullable=True, default=True)
