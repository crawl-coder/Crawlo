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
            
            # 优化：聚合相似的统计项，减少输出冗长度
            optimized_stats = self._aggregate_similar_stats(formatted_stats)
            
            # 输出统计信息（这是唯一输出统计信息的地方）
            self.logger.info(f'{spider_name} stats: \n{pformat(optimized_stats)}')
    
    def _aggregate_similar_stats(self, stats):
        """
        聚合相似的统计项，减少输出冗长度
        特别是对request_ignore_count/reason/*这样的统计项进行聚合
        """
        import re
        
        # 用于聚合相似统计项的容器
        aggregated_stats = {}
        
        for key, value in stats.items():
            # 聚合request_ignore_count/reason/*类型的统计项
            if key.startswith('request_ignore_count/reason/'):
                # 提取原因部分
                reason_part = key[len('request_ignore_count/reason/'):]
                
                # 检查是否是403错误相关的统计项
                if '403' in reason_part and '不在允许列表中' in reason_part:
                    # 将所有403错误聚合到一个统计项中
                    aggregate_key = 'request_ignore_count/reason/状态码 403 不在允许列表中 - 403'
                    if aggregate_key not in aggregated_stats:
                        aggregated_stats[aggregate_key] = 0
                    aggregated_stats[aggregate_key] += value
                elif '404' in reason_part and '不在允许列表中' in reason_part:
                    # 将所有404错误聚合到一个统计项中
                    aggregate_key = 'request_ignore_count/reason/状态码 404 不在允许列表中 - 404'
                    if aggregate_key not in aggregated_stats:
                        aggregated_stats[aggregate_key] = 0
                    aggregated_stats[aggregate_key] += value
                else:
                    # 对于其他原因，按模式聚合
                    # 例如：将 "response filtered: 状态码 404 不在允许列表中 - 404" 和 "response filtered: 状态码 403 不在允许列表中 - 403" 分别聚合
                    pattern = re.search(r'(response filtered: 状态码 \d+ 不在允许列表中) - \d+', reason_part)
                    if pattern:
                        base_reason = pattern.group(1)
                        aggregate_key = f'request_ignore_count/reason/{base_reason}'
                        if aggregate_key not in aggregated_stats:
                            aggregated_stats[aggregate_key] = 0
                        aggregated_stats[aggregate_key] += value
                    else:
                        # 如果无法聚合，保持原有统计项
                        aggregated_stats[key] = value
            elif key.startswith('request_ignore_count/domain/'):
                # 对域名统计进行聚合，保持原有逻辑
                aggregated_stats[key] = value
            else:
                # 非聚合统计项，直接复制
                aggregated_stats[key] = value
        
        return aggregated_stats