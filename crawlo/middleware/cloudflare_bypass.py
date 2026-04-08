#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Cloudflare 绕过中间件
======================
自动检测并绕过 Cloudflare 挑战页面。

功能特性:
- 检测 Cloudflare 挑战页面（403/503 + 特征）
- 自动降级到隐身浏览器重新请求
- 支持多种隐身浏览器（camoufox、playwright、drissionpage）
- 智能重试机制

使用方法:
# settings.py
# 中间件默认已在框架中注册，无需手动配置
# 只需配置绕过时使用的下载器类型
CLOUDFLARE_BYPASS_DOWNLOADER = \'camoufox\'  # 或 \'playwright\', \'drissionpage\'
"""

import re
from typing import Optional, Union
from urllib.parse import urlparse

from crawlo.network.request import Request
from crawlo.network.response import Response
from crawlo.logging import get_logger


class CloudflareBypassMiddleware:
    """
    Cloudflare 绕过中间件
    
    自动检测 Cloudflare 挑战页面并使用隐身浏览器重新请求。
    
    检测逻辑（参考 Scrapling）：
    1. HTTP 状态码为 403、503、520、521、522、523、524
    2. 响应内容包含 Cloudflare 特征
    3. 支持 Turnstile 挑战类型检测
    
    绕过策略：
    1. 使用隐身浏览器（camoufox 推荐）重新请求
    2. 支持请求级别配置不同的浏览器
    """
    
    # Cloudflare 挑战状态码
    CHALLENGE_STATUS_CODES = {403, 503, 520, 521, 522, 523, 524}
    
    # Cloudflare Turnstile 挑战类型（参考 Scrapling）
    CHALLENGE_TYPES = (
        "non-interactive",
        "managed",
        "interactive",
    )
    
    # Cloudflare 响应特征
    CLOUDFLARE_SIGNATURES = [
        rb'cloudflare',
        rb'cf-ray',
        rb'cf-browser-verify',
        rb'cf_chl_opt',
        rb'challenge-platform',
        rb'ray id:',
        rb'Checking your browser',
        rb'Just a moment',
        rb'DDoS protection by Cloudflare',
        rb'Please Wait\.\.\. \| Cloudflare',
        rb'<title>Access denied</title>',
        rb'<title>Attention Required!</title>',
        rb'enable JavaScript',
        rb'cf_clearance',
        rb'__cf_bm',
        rb'cf-mitigated',
        rb'cType:',  # Turnstile 挑战类型标识
    ]
    
    # Cloudflare 挑战平台 URL 模式
    CF_CHALLENGE_PATTERN = re.compile(r"^https?://challenges\.cloudflare\.com/cdn-cgi/challenge-platform/.*")
    
    def __init__(self, crawler):
        self.crawler = crawler
        self.logger = get_logger(self.__class__.__name__)
        
        # 配置
        self.max_retries = crawler.settings.get_int("CLOUDFLARE_BYPASS_MAX_RETRIES", 2)
        self.default_downloader = crawler.settings.get("CLOUDFLARE_BYPASS_DOWNLOADER", "camoufox")
        
        # 用于缓存已知的 Cloudflare 域名
        self._cloudflare_domains = set()
        
        # 下载器实例缓存（延迟初始化）
        self._bypass_downloader = None
        
        self.logger.debug(f"CloudflareBypassMiddleware initialized (downloader={self.default_downloader})")

    @classmethod
    def create_instance(cls, crawler):
        """创建中间件实例"""
        return cls(crawler)

    async def process_request(self, request: Request, spider) -> Optional[Request]:
        """请求预处理"""
        # 如果请求已经标记为使用隐身浏览器，跳过
        if request.meta.get('cloudflare_bypass_attempted'):
            return None
        
        # 如果域名已知需要 Cloudflare 绕过，直接使用隐身浏览器
        if self._is_known_cloudflare_domain(request.url):
            self.logger.debug(f"Known Cloudflare domain, using stealth browser for {request.url}")
            request.meta['use_dynamic_loader'] = True
            request.meta['dynamic_downloader_type'] = request.meta.get(
                'cloudflare_bypass_downloader', 
                self.default_downloader
            )
        
        return None

    async def process_response(self, request: Request, response: Response, spider) -> Union[Request, Response]:
        """响应后处理"""
        # 检查是否为 Cloudflare 挑战页面
        if not self._is_cloudflare_challenge(response):
            return response
        
        # 检查是否已达到最大重试次数
        bypass_count = request.meta.get('cloudflare_bypass_count', 0)
        if bypass_count >= self.max_retries:
            self.logger.warning(f"Max Cloudflare bypass retries reached for {request.url}")
            return response
        
        # 标记为 Cloudflare 域名
        self._mark_cloudflare_domain(request.url)
        
        # 创建新的请求，使用隐身浏览器
        self.logger.info(f"Cloudflare challenge detected for {request.url}, attempting bypass with {self.default_downloader}")
        
        # 创建重试请求
        retry_request = self._create_bypass_request(request, bypass_count)
        
        return retry_request

    async def process_exception(self, request: Request, exception: Exception, spider) -> Optional[Request]:
        """异常处理"""
        # 某些异常也可能是由 Cloudflare 引起的
        exception_str = str(exception).lower()
        cloudflare_error_indicators = [
            'cloudflare',
            'cf-ray',
            '403',
            'forbidden',
            'access denied',
        ]
        
        if any(indicator in exception_str for indicator in cloudflare_error_indicators):
            bypass_count = request.meta.get('cloudflare_bypass_count', 0)
            if bypass_count < self.max_retries:
                self.logger.info(f"Cloudflare-related exception for {request.url}, attempting bypass")
                return self._create_bypass_request(request, bypass_count)
        
        return None

    def _is_cloudflare_challenge(self, response: Response) -> bool:
        """检测是否为 Cloudflare 挑战页面"""
        # 检查状态码
        if response.status_code not in self.CHALLENGE_STATUS_CODES:
            return False
        
        # 检查响应头
        headers_lower = {k.lower(): v for k, v in response.headers.items()}
        if 'cf-ray' in headers_lower or 'cf-cache-status' in headers_lower:
            return True
        
        # 检查响应内容
        body = response.body
        if not body:
            return False
        
        # 检查 Cloudflare 特征
        for signature in self.CLOUDFLARE_SIGNATURES:
            if re.search(signature, body, re.IGNORECASE):
                return True
        
        return False
    
    def _detect_cloudflare_type(self, page_content: str) -> Optional[str]:
        """
        检测 Cloudflare Turnstile 挑战类型（参考 Scrapling）
        
        Args:
            page_content: 页面内容
            
        Returns:
            挑战类型: 'non-interactive', 'managed', 'interactive', 'embedded' 或 None
        """
        try:
            content = page_content if isinstance(page_content, str) else page_content.decode('utf-8', errors='ignore')
            
            # 检查 Turnstile 类型
            for ctype in self.CHALLENGE_TYPES:
                if f"cType: '{ctype}'" in content:
                    return ctype
            
            # 检查是否为嵌入式 Turnstile
            if 'challenges.cloudflare.com/turnstile' in content:
                return "embedded"
            
            return None
        except Exception:
            return None

    def _create_bypass_request(self, original_request: Request, bypass_count: int) -> Request:
        """创建绕过请求"""
        # 复制原始请求
        retry_request = original_request.copy()
            
        # 更新 meta
        retry_request.meta['cloudflare_bypass_count'] = bypass_count + 1
        retry_request.meta['cloudflare_bypass_attempted'] = True
        retry_request.meta['use_dynamic_loader'] = True
        retry_request.meta['dynamic_downloader_type'] = retry_request.meta.get(
            'cloudflare_bypass_downloader', 
            self.default_downloader
        )
            
        self.logger.debug(
            f"Created bypass request (attempt {bypass_count + 1}/{self.max_retries}) "
            f"using {retry_request.meta['dynamic_downloader_type']}"
        )
            
        return retry_request

    def _is_known_cloudflare_domain(self, url: str) -> bool:
        """检查是否为已知的 Cloudflare 域名"""
        try:
            domain = urlparse(url).netloc.lower()
            return domain in self._cloudflare_domains
        except Exception:
            return False

    def _mark_cloudflare_domain(self, url: str):
        """标记域名需要 Cloudflare 绕过"""
        try:
            domain = urlparse(url).netloc.lower()
            self._cloudflare_domains.add(domain)
            self.logger.debug(f"Marked {domain} as Cloudflare-protected domain")
        except Exception:
            pass
