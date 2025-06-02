#!/usr/bin/python
# -*- coding:UTF-8 -*-
from asyncio import sleep
from random import uniform
from crawlo.utils.log import get_logger
from crawlo.exceptions import NotConfiguredError


class DownloadDelayMiddleware(object):

    def __init__(self, settings, log_level):
        self.delay = settings.get_float("DOWNLOAD_DELAY")
        if not self.delay:
            raise NotConfiguredError
        self.randomness = settings.get_bool("RANDOMNESS")
        self.floor, self.upper = settings.get_list("RANDOM_RANGE")
        self.logger = get_logger(self.__class__.__name__, log_level)

    @classmethod
    def create_instance(cls, crawler):
        o = cls(settings=crawler.settings, log_level=crawler.settings.get('LOG_LEVEL'))
        return o

    async def process_request(self, _request, _spider):
        if self.randomness:
            await sleep(uniform(self.delay * self.floor, self.delay * self.upper))
        else:
            await sleep(self.delay)
