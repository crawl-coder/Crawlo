# -*- coding: utf-8 -*-
"""
Book Item definition
"""
from crawlo.items import Item, Field


class BookItem(Item):
    title = Field()
    price = Field()
    rating = Field()
    availability = Field()
    upc = Field()
    tax = Field()
    stock = Field()
    category = Field()
    url = Field()