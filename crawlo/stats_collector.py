#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
# @Time    :    2025-05-17 09:57
# @Author  :   crawl-coder
# @Desc    :   统计信息收集器
"""
from pprint import pformat
from crawlo.utils.log import get_logger


class StatsCollector(object):

    def __init__(self, crawler):
        self.crawler = crawler
        self._dump = self.crawler.settings.get_bool('STATS_DUMP')
        self._stats = {}
        self.logger = get_logger(self.__class__.__name__, "INFO")

    def inc_value(self, key, count=1, start=0):
        self._stats[key] = self._stats.setdefault(key, start) + count

    def get_value(self, key, default=None):
        return self._stats.get(key, default)

    def get_stats(self):
        return self._stats

    def set_stats(self, stats):
        self._stats = stats

    def clear_stats(self):
        self._stats.clear()

    def close_spider(self, spider_name, reason):
        self._stats['reason'] = reason
        if self._dump:
            self.logger.info(f'{spider_name} stats: \n{pformat(self._stats)}')

    def __getitem__(self, item):
        return self._stats[item]

    def __setitem__(self, key, value):
        self._stats[key] = value

    def __delitem__(self, key):
        del self._stats[key]
