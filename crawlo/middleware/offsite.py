#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
OffsiteMiddleware 中间件
用于过滤掉不在指定域名范围内的请求
"""
import re
from urllib.parse import urlparse

from crawlo.logging import get_logger
from crawlo.exceptions import IgnoreRequestError


class OffsiteMiddleware:
    """
    OffsiteMiddleware 中间件
    用于过滤掉不在指定域名范围内的请求，防止爬虫爬取到不相关的网站
    """

    def __init__(self, stats, allowed_domains=None):
        self.logger = get_logger(self.__class__.__name__)
        self.stats = stats
        self.allowed_domains = allowed_domains or []

    @classmethod
    def create_instance(cls, crawler):
        """
        创建中间件实例
        从爬虫设置中获取允许的域名列表
        """
        # 优先使用 Spider 实例的 allowed_domains，回退到全局设置中的 ALLOWED_DOMAINS
        allowed_domains = []
        
        # 检查当前爬虫实例是否有 allowed_domains 属性
        if hasattr(crawler, 'spider') and crawler.spider and hasattr(crawler.spider, 'allowed_domains'):
            allowed_domains = getattr(crawler.spider, 'allowed_domains', [])
        
        # 如果 Spider 实例没有设置 allowed_domains，则从全局设置中获取
        if not allowed_domains:
            allowed_domains = crawler.settings.get_list('ALLOWED_DOMAINS')
        
        # 如果没有配置允许的域名，则禁用此中间件
        if not allowed_domains:
            from crawlo.exceptions import NotConfiguredError
            raise NotConfiguredError("未配置ALLOWED_DOMAINS，OffsiteMiddleware已禁用")
            
        o = cls(
            stats=crawler.stats,
            allowed_domains=allowed_domains
        )
        
        # 编译域名正则表达式以提高性能
        o._compile_domains()
        
        # 使用中间件自己的logger而不是crawler.logger
        o.logger.debug(f"OffsiteMiddleware 已启用，允许的域名: {allowed_domains}")
        return o

    def _compile_domains(self):
        """
        编译域名正则表达式
        """
        self._domain_regexes = []
        for domain in self.allowed_domains:
            # 转义域名中的特殊字符
            escaped_domain = re.escape(domain)
            # 创建匹配域名的正则表达式（支持子域名）
            regex = re.compile(r'(^|.*\.)' + escaped_domain + '$', re.IGNORECASE)
            self._domain_regexes.append(regex)

    def _is_offsite_request(self, request):
        """
        判断请求是否为站外请求
        """
        try:
            parsed_url = urlparse(request.url)
            hostname = parsed_url.hostname
            
            if not hostname:
                return True  # 无效URL
                
            # 检查是否匹配允许的域名
            for regex in self._domain_regexes:
                if regex.match(hostname):
                    return False  # 匹配允许的域名
                    
            return True  # 不匹配任何允许的域名
        except Exception:
            # URL解析失败，视为站外请求
            return True

    async def process_request(self, request, spider):
        """
        处理请求，过滤站外请求
        """
        if self._is_offsite_request(request):
            # 记录被过滤的请求
            self.stats.inc_value('offsite_request_count')
            
            # 记录被过滤的域名
            try:
                parsed_url = urlparse(request.url)
                hostname = parsed_url.hostname or "unknown"
                self.stats.inc_value(f'offsite_request_count/{hostname}')
            except:
                self.stats.inc_value('offsite_request_count/invalid_url')
            
            self.logger.debug(f"过滤站外请求: {request.url}")
            
            # 抛出异常以忽略该请求
            raise IgnoreRequestError(f"站外请求被过滤: {request.url}")
            
        return None

    def process_exception(self, request, exception, spider):
        """
        处理异常
        """
        # 如果是IgnoreRequestError且是我们产生的，则处理它
        if isinstance(exception, IgnoreRequestError) and "站外请求被过滤" in str(exception):
            self.logger.debug(f"已过滤站外请求: {request.url}")
            return True  # 表示异常已被处理
        return None