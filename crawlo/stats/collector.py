#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
统计收集器
==========
框架主要入口，负责收集和管理统计信息。

核心组件：
- StatsCollector: 统计收集器
"""
import re
from typing import Any, Dict
from pprint import pformat

from crawlo.logging import get_logger
from crawlo.stats.backends import StatsBackendFactory


class StatsCollector:
    """
    统计信息收集器
    
    框架内部通过此类记录抓取指标、错误聚合等信息。
    支持可插拔的存储后端（Memory/Redis/File）。
    """

    def __init__(self, crawler):
        """
        初始化统计收集器
        
        Args:
            crawler: Crawler 实例
        """
        self.crawler = crawler
        from crawlo.utils.misc import safe_get_config
        self._dump = safe_get_config(self.crawler.settings, 'STATS_DUMP', True, bool)
        self._closed = False  # 防止 close 重复调用
        
        # 创建统计后端
        self.backend = StatsBackendFactory.from_settings(self.crawler.settings)
        self.logger = get_logger(self.__class__.__name__)

    def inc_value(self, key: str, count: int = 1, start: int = 0) -> None:
        """
        增加统计值
        
        Args:
            key: 统计键
            count: 增加数量
            start: 初始值（如果键不存在）
        """
        if start != 0 and not self.backend.has_key(key):
            self.backend.set_value(key, start + count)
        else:
            self.backend.inc_value(key, count)

    def get_value(self, key: str, default: Any = None) -> Any:
        """获取统计值"""
        return self.backend.get_value(key, default)

    def get_stats(self) -> Dict[str, Any]:
        """获取所有统计信息"""
        return self.backend.get_stats()

    def set_stats(self, stats: Dict[str, Any]) -> None:
        """批量设置统计信息"""
        for k, v in stats.items():
            self.backend.set_value(k, v)

    def clear_stats(self) -> None:
        """清空所有统计信息"""
        self.backend.clear()

    def close_spider(self, spider, reason: str) -> None:
        """
        爬虫关闭时记录信息
        
        Args:
            spider: Spider 实例
            reason: 关闭原因
        """
        from datetime import datetime
        
        self.backend.set_value('reason', reason)
        spider_name = getattr(spider, 'name', None) or spider.__class__.__name__ or '<Unknown>'
        self.backend.set_value('spider_name', spider_name)
        
        # 记录结束时间
        end_time = datetime.now()
        self.backend.set_value('end_time', end_time.strftime('%Y-%m-%d %H:%M:%S'))
        
        # 计算并记录性能指标
        start_time_str = self.backend.get_value('start_time')
        if start_time_str:
            try:
                start_time = datetime.strptime(start_time_str, '%Y-%m-%d %H:%M:%S')
                elapsed_seconds = (end_time - start_time).total_seconds()
                
                # 记录消耗时间
                self.backend.set_value('elapsed_time', f'{elapsed_seconds:.2f}s')
                
                # 计算每分钟速率
                if elapsed_seconds > 0:
                    item_count = self.backend.get_value('item_successful_count', 0)
                    response_count = self.backend.get_value('response_received_count', 0)
                    
                    items_per_min = (item_count / elapsed_seconds) * 60
                    pages_per_min = (response_count / elapsed_seconds) * 60
                    
                    self.backend.set_value('items_per_minute', round(items_per_min, 2))
                    self.backend.set_value('pages_per_minute', round(pages_per_min, 2))
            except (ValueError, TypeError):
                pass

    def __getitem__(self, item: str) -> Any:
        return self.backend.get_value(item)

    def __setitem__(self, key: str, value: Any) -> None:
        self.backend.set_value(key, value)

    def close(self) -> None:
        """关闭统计收集器并输出统计信息报告"""
        # 幂等保护：防止 close 被重复调用
        if self._closed:
            return
        self._closed = True
        
        if self._dump:
            stats = self.backend.get_stats()
            spider_name = stats.get('spider_name', 'unknown')
            
            # 尝试从 crawler 获取爬虫名称
            if spider_name == 'unknown' and hasattr(self, 'crawler') and self.crawler:
                spider = getattr(self.crawler, 'spider', None)
                if spider and hasattr(spider, 'name'):
                    spider_name = spider.name
                    self.backend.set_value('spider_name', spider_name)
            
            # 计算并添加性能指标
            self._calculate_performance_metrics(stats)
            
            # 格式化浮点数
            formatted_stats = {}
            for key, value in stats.items():
                formatted_stats[key] = round(value, 2) if isinstance(value, float) else value
            
            # 聚合相似统计项
            optimized_stats = self._aggregate_similar_stats(formatted_stats)
            self.logger.info(f'{spider_name} stats: \n{pformat(optimized_stats)}')
        
        self.backend.close()
    
    def _calculate_performance_metrics(self, stats: Dict[str, Any]) -> None:
        """
        计算并添加性能指标
        
        Args:
            stats: 当前统计信息
        """
        from datetime import datetime
        
        # 计算总耗时（秒）
        start_time_str = stats.get('start_time')
        end_time_str = stats.get('end_time')
        
        if start_time_str and end_time_str:
            try:
                start_time = datetime.strptime(start_time_str, '%Y-%m-%d %H:%M:%S')
                end_time = datetime.strptime(end_time_str, '%Y-%m-%d %H:%M:%S')
                elapsed_seconds = (end_time - start_time).total_seconds()
                
                if elapsed_seconds > 0:
                    # 计算每分钟速率
                    item_count = stats.get('item_successful_count', 0)
                    response_count = stats.get('response_received_count', 0)
                    
                    items_per_min = (item_count / elapsed_seconds) * 60
                    pages_per_min = (response_count / elapsed_seconds) * 60
                    
                    self.backend.set_value('items_per_minute', round(items_per_min, 2))
                    self.backend.set_value('pages_per_minute', round(pages_per_min, 2))
            except (ValueError, TypeError):
                pass
        
        # 计算响应状态码分类统计
        self._calculate_response_status_categories(stats)
    
    def _calculate_response_status_categories(self, stats: Dict[str, Any]) -> None:
        """
        计算响应状态码分类统计（3xx、4xx、5xx）
        
        Args:
            stats: 当前统计信息
        """
        status_3xx = 0
        status_4xx = 0
        status_5xx = 0
        
        # 遍历所有状态码统计项
        for key, value in stats.items():
            if key.startswith('response_status_code/'):
                status_code_str = key.split('/')[-1]
                try:
                    status_code = int(status_code_str)
                    if 300 <= status_code < 400:
                        status_3xx += value
                    elif 400 <= status_code < 500:
                        status_4xx += value
                    elif 500 <= status_code < 600:
                        status_5xx += value
                except (ValueError, TypeError):
                    pass
        
        # 设置分类统计
        if status_3xx > 0:
            self.backend.set_value('response_status_code/category/3xx', status_3xx)
        if status_4xx > 0:
            self.backend.set_value('response_status_code/category/4xx', status_4xx)
        if status_5xx > 0:
            self.backend.set_value('response_status_code/category/5xx', status_5xx)
    
    def _aggregate_similar_stats(self, stats: Dict[str, Any]) -> Dict[str, Any]:
        """
        聚合相似的统计项（如 403/404 错误），减少日志冗长度
        
        Args:
            stats: 原始统计信息
            
        Returns:
            聚合后的统计信息
        """
        aggregated_stats = {}
        for key, value in stats.items():
            if key.startswith('request_ignore_count/reason/'):
                reason_part = key[len('request_ignore_count/reason/'):]
                
                # 聚合 403 错误
                if '403' in reason_part and '不在允许列表中' in reason_part:
                    agg_key = 'request_ignore_count/reason/状态码 403 不在允许列表中 - 403'
                    aggregated_stats[agg_key] = aggregated_stats.get(agg_key, 0) + value
                
                # 聚合 404 错误
                elif '404' in reason_part and '不在允许列表中' in reason_part:
                    agg_key = 'request_ignore_count/reason/状态码 404 不在允许列表中 - 404'
                    aggregated_stats[agg_key] = aggregated_stats.get(agg_key, 0) + value
                
                # 聚合其他状态码错误
                else:
                    match = re.search(r'(response filtered: 状态码 \d+ 不在允许列表中) - \d+', reason_part)
                    if match:
                        agg_key = f'request_ignore_count/reason/{match.group(1)}'
                        aggregated_stats[agg_key] = aggregated_stats.get(agg_key, 0) + value
                    else:
                        aggregated_stats[key] = value
            else:
                aggregated_stats[key] = value
        
        return aggregated_stats
