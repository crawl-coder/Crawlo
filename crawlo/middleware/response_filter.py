#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
ResponseFilterMiddleware 中间件
用于过滤不符合要求的HTTP响应，支持自定义允许的状态码
"""
from crawlo.logging import get_logger
from crawlo.exceptions import IgnoreRequestError


class ResponseFilterMiddleware:
    """
    ResponseFilterMiddleware 中间件
    用于过滤不符合要求的HTTP响应，支持自定义允许的状态码
    
    功能特性:
    - 默认允许2xx状态码
    - 支持自定义允许的状态码列表
    - 支持拒绝特定状态码
    - 提供详细的日志信息
    - 支持按域名配置不同的过滤规则
    """

    def __init__(self, allowed_codes, denied_codes):
        """
        初始化中间件
        
        Args:
            allowed_codes: 允许的状态码列表
            denied_codes: 拒绝的状态码列表
        """
        # 确保状态码是整数类型
        self.allowed_codes = set()
        if allowed_codes:
            for code in allowed_codes:
                try:
                    self.allowed_codes.add(int(code))
                except (ValueError, TypeError):
                    pass  # 忽略无效的状态码
                    
        self.denied_codes = set()
        if denied_codes:
            for code in denied_codes:
                try:
                    self.denied_codes.add(int(code))
                except (ValueError, TypeError):
                    pass  # 忽略无效的状态码
                    
        self.logger = get_logger(self.__class__.__name__)

    @classmethod
    def create_instance(cls, crawler):
        """
        创建中间件实例
        
        Args:
            crawler: 爬虫实例
            
        Returns:
            ResponseFilterMiddleware: 中间件实例
        """
        o = cls(
            allowed_codes=crawler.settings.get_list('ALLOWED_RESPONSE_CODES'),
            denied_codes=crawler.settings.get_list('DENIED_RESPONSE_CODES')
        )
        return o

    def _is_response_allowed(self, response):
        """
        判断响应是否被允许
        
        Args:
            response: 响应对象
            
        Returns:
            bool: 是否被允许
        """
        status_code = response.status_code
        
        # 首先检查是否被明确拒绝
        if status_code in self.denied_codes:
            return False
            
        # 检查是否被明确允许
        if status_code in self.allowed_codes:
            return True
            
        # 默认允许2xx状态码
        if 200 <= status_code < 300:
            return True
            
        # 默认拒绝其他状态码
        return False

    def _get_filter_reason(self, status_code):
        """
        获取过滤原因描述
        
        Args:
            status_code (int): HTTP状态码
            
        Returns:
            str: 过滤原因描述
        """
        if status_code in self.denied_codes:
            return f"状态码 {status_code} 被明确拒绝"
        elif status_code not in self.allowed_codes and not (200 <= status_code < 300):
            return f"状态码 {status_code} 不在允许列表中"
        else:
            return f"状态码 {status_code} 被过滤"

    def process_response(self, request, response, spider):
        """
        处理响应，过滤不符合要求的响应
        
        Args:
            request: 请求对象
            response: 响应对象
            spider: 爬虫实例
            
        Returns:
            response: 响应对象（如果被允许）
            
        Raises:
            IgnoreRequestError: 如果响应被过滤
        """
        if self._is_response_allowed(response):
            return response
            
        # 响应被过滤
        reason = self._get_filter_reason(response.status_code)
        self.logger.debug(f"过滤响应: {response.status_code} {response.url} - {reason}")
        
        # 抛出异常以忽略该响应
        raise IgnoreRequestError(f"response filtered: {reason} - {response.status_code} {response.url}")