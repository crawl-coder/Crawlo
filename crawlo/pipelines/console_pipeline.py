#!/usr/bin/python
# -*- coding:UTF-8 -*-
from crawlo import Item
from crawlo.spider import Spider
from crawlo.utils.log import get_logger


class DebugPipeline:

    def __init__(self, logger):
        self.logger = logger

    @classmethod
    def create_instance(cls, crawler):
        logger = get_logger(cls.__name__, crawler.settings.get('LOG_LEVEL'))
        return cls(logger)

    async def process_item(self, item: Item, spider: Spider) -> Item:
        self.logger.debug(item.to_dict())
        return item
