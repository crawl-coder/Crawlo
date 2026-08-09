#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Spider 统计模块（P2-6 拆分）
============================
从 spider.py 拆分：爬虫运行期统计追踪（请求/响应/数据项/错误）。
"""
from __future__ import annotations

import time
from typing import Any, Dict, Optional
from urllib.parse import urlparse

class SpiderStatsTracker:
    """
    爬虫统计跟踪器
    提供详细的性能监控功能
    """
    
    def __init__(self, spider_name: str) -> None:
        """
        初始化统计跟踪器
        
        Args:
            spider_name: 爬虫名称
        """
        self.spider_name: str = spider_name
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.request_count: int = 0
        self.response_count: int = 0
        self.item_count: int = 0
        self.error_count: int = 0
        self.domain_stats: Dict[str, int] = {}
        
    def start_tracking(self) -> None:
        """开始统计"""
        self.start_time = time.time()
        
    def stop_tracking(self) -> None:
        """停止统计"""
        self.end_time = time.time()
        
    def record_request(self, url: str) -> None:
        """
        记录请求
        
        Args:
            url: 请求URL
        """
        self.request_count += 1
        # urlparse 已在顶部导入
        domain = urlparse(url).netloc
        self.domain_stats[domain] = self.domain_stats.get(domain, 0) + 1
        
    def record_response(self) -> None:
        """记录响应"""
        self.response_count += 1
        
    def record_item(self) -> None:
        """记录Item"""
        self.item_count += 1
        
    def record_error(self) -> None:
        """记录错误"""
        self.error_count += 1
        
    def get_summary(self) -> Dict[str, Any]:
        """
        获取统计摘要
        
        Returns:
            Dict[str, Any]: 统计摘要字典
        """
        duration = (self.end_time - self.start_time) if (self.start_time and self.end_time) else 0
        
        return {
            'spider_name': self.spider_name,
            'duration_seconds': round(duration, 2),
            'requests': self.request_count,
            'responses': self.response_count,
            'items': self.item_count,
            'errors': self.error_count,
            'success_rate': round((self.response_count / max(1, self.request_count)) * 100, 2),
            'requests_per_second': round(self.request_count / max(1, duration), 2),
            'top_domains': sorted(
                self.domain_stats.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:5]
        }

