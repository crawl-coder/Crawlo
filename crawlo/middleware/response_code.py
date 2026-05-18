#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
ResponseCodeMiddleware 中间件
用于处理HTTP响应状态码，记录统计信息并支持特殊状态码处理
"""
from crawlo.logging import get_logger


class ResponseCodeMiddleware:
    """
    ResponseCodeMiddleware 中间件
    用于处理HTTP响应状态码，记录统计信息并支持特殊状态码处理
    
    功能特性:
    - 记录各种HTTP状态码的出现次数
    - 支持特殊状态码的详细处理
    - 提供详细的日志信息
    - 支持状态码分类统计(2xx, 3xx, 4xx, 5xx)
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
            ResponseCodeMiddleware: 中间件实例
        """
        o = cls(stats=crawler.stats)
        return o

    def _get_status_category(self, status_code):
        """
        获取状态码分类
        
        Args:
            status_code (int): HTTP状态码
            
        Returns:
            str: 状态码分类 (2xx, 3xx, 4xx, 5xx, other)
        """
        if 200 <= status_code < 300:
            return "2xx"
        elif 300 <= status_code < 400:
            return "3xx"
        elif 400 <= status_code < 500:
            return "4xx"
        elif 500 <= status_code < 600:
            return "5xx"
        else:
            return "other"

    def _is_success_response(self, status_code):
        """
        判断是否为成功响应
        
        Args:
            status_code (int): HTTP状态码
            
        Returns:
            bool: 是否为成功响应
        """
        return 200 <= status_code < 300

    def _is_redirect_response(self, status_code):
        """
        判断是否为重定向响应
        
        Args:
            status_code (int): HTTP状态码
            
        Returns:
            bool: 是否为重定向响应
        """
        return 300 <= status_code < 400

    def _is_client_error(self, status_code):
        """
        判断是否为客户端错误
        
        Args:
            status_code (int): HTTP状态码
            
        Returns:
            bool: 是否为客户端错误
        """
        return 400 <= status_code < 500

    def _is_server_error(self, status_code):
        """
        判断是否为服务器错误
        
        Args:
            status_code (int): HTTP状态码
            
        Returns:
            bool: 是否为服务器错误
        """
        return 500 <= status_code < 600

    def process_response(self, request, response, spider):
        """记录成功/失败统计和响应大小（状态码分类统计由 MiddlewareManager 统一处理）"""
        status = response.status

        if self._is_success_response(status):
            self.stats.inc_value('response_status_code/success_count')
        elif self._is_client_error(status) or self._is_server_error(status):
            self.stats.inc_value('response_status_code/error_count')

        if hasattr(response, 'content_length') and response.content_length:
            self.stats.inc_value('response_total_bytes', response.content_length)

        return response
