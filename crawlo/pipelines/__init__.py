#!/usr/bin/python
# -*- coding:UTF-8 -*-
from crawlo.items.items import Item


class BasePipeline:

    def process_item(self, item: Item, spider):
        raise NotImplementedError

    @classmethod
    def create_instance(cls, crawler):
        return cls()
