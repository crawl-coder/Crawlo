#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
RequestIgnoreMiddleware 中间件
用于处理和记录被忽略的请求
"""
from crawlo.logging import get_logger
from crawlo.exceptions import IgnoreRequestError
from crawlo.event import CrawlerEvent


class RequestIgnoreMiddleware(object):
    """
    RequestIgnoreMiddleware 中间件
    用于处理和记录被忽略的请求，提供详细的统计信息
    """

    def __init__(self, stats):
        """
        初始化中间件
        
        Args:
            stats: 统计信息收集器
        """
        self.logger = get_logger(self.__class__.__name__)
        self.stats = stats

    @classmethod
    def create_instance(cls, crawler):
        """
        创建中间件实例
        
        Args:
            crawler: 爬虫实例
            
        Returns:
            RequestIgnoreMiddleware: 中间件实例
        """
        o = cls(stats=crawler.stats)
        crawler.subscriber.subscribe(o.request_ignore, event=CrawlerEvent.IGNORE_REQUEST)
        return o

    async def request_ignore(self, exc, request, _spider):
        """
        处理被忽略的请求事件
        
        Args:
            exc: 异常对象
            request: 被忽略的请求
            _spider: 爬虫实例
        """
        # 记录被忽略的请求
        self.logger.info(f'请求被忽略: {request.url}')
        self.stats.inc_value('request_ignore_count')
        
        # 记录忽略原因
        reason = getattr(exc, 'msg', 'unknown')
        if reason:
            self.stats.inc_value(f'request_ignore_count/reason/{reason}')
            
        # 记录请求的域名分布
        try:
            from urllib.parse import urlparse
            parsed_url = urlparse(request.url)
            domain = parsed_url.netloc
            if domain:
                self.stats.inc_value(f'request_ignore_count/domain/{domain}')
        except Exception:
            self.stats.inc_value('request_ignore_count/domain/invalid_url')

    @staticmethod
    def process_exception(_request, exc, _spider):
        """
        处理异常，识别IgnoreRequestError
        
        Args:
            _request: 请求对象
            exc: 异常对象
            _spider: 爬虫实例
            
        Returns:
            bool: 如果是IgnoreRequestError则返回True，否则返回None
        """
        if isinstance(exc, IgnoreRequestError):
            return True
        return None