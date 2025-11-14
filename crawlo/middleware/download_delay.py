#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
DownloadDelayMiddleware 中间件
用于控制请求之间的延迟时间，支持固定延迟和随机延迟
"""

import asyncio
from asyncio import sleep
from random import uniform
from crawlo.logging import get_logger
from crawlo.exceptions import NotConfiguredError


class DownloadDelayMiddleware(object):
    """
    DownloadDelayMiddleware 中间件
    用于控制请求之间的延迟时间，支持固定延迟和随机延迟
    
    功能特性:
    - 支持固定延迟时间
    - 支持随机延迟时间
    - 提供详细的日志信息
    - 记录延迟统计信息
    """

    def __init__(self, settings, stats=None):
        """
        初始化中间件
        
        Args:
            settings: 设置管理器
            stats: 统计信息收集器（可选）
        """
        self.delay = settings.get_float("DOWNLOAD_DELAY")
        if not self.delay:
            raise NotConfiguredError("DOWNLOAD_DELAY not set or is zero")
            
        self.randomness = settings.get_bool("RANDOMNESS", False)
        
        # 安全地获取随机范围配置
        random_range = settings.get_list("RANDOM_RANGE")
        if len(random_range) >= 2:
            try:
                self.floor = float(random_range[0])
                self.upper = float(random_range[1])
            except (ValueError, TypeError):
                # 如果配置无效，使用默认值
                self.floor, self.upper = 0.5, 1.5
        else:
            # 如果配置不完整，使用默认值
            self.floor, self.upper = 0.5, 1.5
            
        self.logger = get_logger(self.__class__.__name__)
        self.stats = stats

    @classmethod
    def create_instance(cls, crawler):
        """
        创建中间件实例
        
        Args:
            crawler: 爬虫实例
            
        Returns:
            DownloadDelayMiddleware: 中间件实例
        """
        o = cls(
            settings=crawler.settings,
            stats=getattr(crawler, 'stats', None)
        )
        return o

    async def process_request(self, _request, _spider):
        """
        处理请求，添加延迟
        
        Args:
            _request: 请求对象
            _spider: 爬虫实例
        """
        try:
            if self.randomness:
                # 计算随机延迟时间
                delay_time = uniform(self.delay * self.floor, self.delay * self.upper)
                await sleep(delay_time)
                
                # 记录统计信息
                if self.stats:
                    self.stats.inc_value('download_delay/random_count')
                    self.stats.inc_value('download_delay/random_total_time', delay_time)
                    
                # 记录日志
                self.logger.debug(f"应用随机延迟: {delay_time:.2f}秒 (范围: {self.delay * self.floor:.2f} - {self.delay * self.upper:.2f})")
            else:
                # 应用固定延迟
                await sleep(self.delay)
                
                # 记录统计信息
                if self.stats:
                    self.stats.inc_value('download_delay/fixed_count')
                    self.stats.inc_value('download_delay/fixed_total_time', self.delay)
                    
                # 记录日志
                self.logger.debug(f"应用固定延迟: {self.delay:.2f}秒")
        except asyncio.CancelledError:
            # 正确处理取消异常
            self.logger.info("下载延迟被取消")
            raise
