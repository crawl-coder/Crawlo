#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Crawler 数据模型

提取自 crawler.py，包含：
- CrawlerState: 爬虫状态枚举
- CrawlerMetrics: 爬虫性能指标数据类
"""
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class CrawlerState(Enum):
    """Crawler状态枚举"""
    CREATED = "created"
    INITIALIZING = "initializing"
    READY = "ready"
    RUNNING = "running"
    CLOSING = "closing"
    CLOSED = "closed"
    ERROR = "error"


@dataclass
class CrawlerMetrics:
    """Crawler性能指标"""
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    initialization_duration: float = 0.0
    crawl_duration: float = 0.0
    request_count: int = 0
    success_count: int = 0
    error_count: int = 0
    
    def get_total_duration(self) -> float:
        """
        获取总执行时间
        
        Returns:
            float: 总执行时间（秒）
        """
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0.0
    
    def get_success_rate(self) -> float:
        """
        获取成功率
        
        Returns:
            float: 成功率（百分比）
        """
        total = self.success_count + self.error_count
        return (self.success_count / total * 100) if total > 0 else 0.0
