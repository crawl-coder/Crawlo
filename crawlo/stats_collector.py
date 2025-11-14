#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
# @Time    :    2025-05-17 09:57
# @Author  :   crawl-coder
# @Desc    :   统计信息收集器
"""
from pprint import pformat
from crawlo.logging import get_logger


class StatsCollector(object):

    def __init__(self, crawler):
        self.crawler = crawler
        # 安全获取STATS_DUMP设置
        from crawlo.utils.misc import safe_get_config
        self._dump = safe_get_config(self.crawler.settings, 'STATS_DUMP', True, bool)
            
        self._stats = {}
        self.logger = get_logger(self.__class__.__name__)

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

    def close_spider(self, spider, reason):
        self._stats['reason'] = reason

        # 首选：使用 spider.name
        # 次选：使用实例的类名
        # 最后：使用一个完全未知的占位符
        spider_name = (
                getattr(spider, 'name', None) or
                spider.__class__.__name__ or
                '<Unknown>'
        )

        self._stats['spider_name'] = spider_name

    def __getitem__(self, item):
        return self._stats[item]

    def __setitem__(self, key, value):
        self._stats[key] = value

    def __delitem__(self, key):
        del self._stats[key]

    def close(self):
        """关闭统计收集器并输出统计信息"""
        if self._dump:
            # 获取爬虫名称
            spider_name = self._stats.get('spider_name', 'unknown')
            
            # 如果还没有设置爬虫名称，尝试从crawler中获取
            if spider_name == 'unknown' and hasattr(self, 'crawler') and self.crawler:
                spider = getattr(self.crawler, 'spider', None)
                if spider and hasattr(spider, 'name'):
                    spider_name = spider.name
                    # 同时更新_stats中的spider_name
                    self._stats['spider_name'] = spider_name
            
            # 对统计信息中的浮点数进行四舍五入处理
            formatted_stats = {}
            for key, value in self._stats.items():
                if isinstance(value, float):
                    # 对浮点数进行四舍五入，保留2位小数
                    formatted_stats[key] = round(value, 2)
                else:
                    formatted_stats[key] = value
            
            # 输出统计信息（这是唯一输出统计信息的地方）
            self.logger.info(f'{spider_name} stats: \n{pformat(formatted_stats)}')