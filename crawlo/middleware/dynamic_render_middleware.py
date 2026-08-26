#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Dynamic Render Middleware
==========================
Sets request markers based on configuration for HybridDownloader to select appropriate downloader.

Workflow:
1. Check if user has explicitly set request markers
2. Check URL pattern configuration (user configured)
3. Check domain configuration (user configured)
4. Set request markers for downloader layer

Usage:
    # Configure domains or URL patterns requiring dynamic rendering in settings.py
    DYNAMIC_RENDER_DOMAINS = ['www.example.com']
    DYNAMIC_RENDER_URL_PATTERNS = [r'/spa/', r'/dynamic/']

    # Or explicitly specify in request
    yield Request(url, meta={'use_dynamic_loader': True})
"""
import re
from typing import Optional, Set, Dict, Any
from urllib.parse import urlparse

from crawlo.logging import get_logger
from crawlo.middleware import BaseMiddleware


class DynamicRenderMiddleware(BaseMiddleware):
    """
    Dynamic Render Middleware - Sets request markers based on configuration

    Works with HybridDownloader in layered collaboration:
    - Middleware layer: Sets request markers based on configuration
    - Downloader layer: Reads markers, selects appropriate downloader

    与 HybridDownloader 的分工（重要）：

    - 本中间件的 meta 标记在 HybridDownloader 路由中**优先级最高**，
      因此只在拥有**显式配置知识**时才打标：
      DYNAMIC_RENDER_URL_PATTERNS / STATIC_PATTERNS / DOMAINS /
      STATIC_DOMAINS 命中，或缓存了此类命中结果。
    - 无任何显式配置命中时不打标，交由 HybridDownloader 按
      HYBRID_DYNAMIC_URL_PATTERNS / HYBRID_DYNAMIC_DOMAINS / 默认协议
      自行路由——避免"未配置的中间件默认打 protocol 标记"短路掉
      HybridDownloader 自己的规则。
    - DYNAMIC_RENDER_DEFAULT_DYNAMIC=True 时默认回退仍视为动态
      （保持该配置项原有语义）。

    Usage:
        # Configure domains or URL patterns requiring dynamic rendering in settings.py
        DYNAMIC_RENDER_DOMAINS = ['www.example.com']
        DYNAMIC_RENDER_URL_PATTERNS = [r'/spa/', r'/dynamic/']

        # Or explicitly specify in request (highest priority)
        yield Request(url, meta={'use_dynamic_loader': True})
    """

    # Class-level flag to ensure init log is printed only once
    _logged_init = False

    def __init__(self):
        super().__init__()
        self.logger = get_logger(self.__class__.__name__)

        # 配置项（将在 create_instance 中初始化）
        self.enabled: bool = True
        self.cache_enabled: bool = True
        self.default_dynamic: bool = False

        # URL 模式配置
        self.dynamic_url_patterns: list = []
        self.static_url_patterns: list = []
        self.dynamic_domains: Set[str] = set()
        self.static_domains: Set[str] = set()

        # 缓存
        self._domain_cache: Dict[str, bool] = {}
        self._cache_max_size: int = 1000

        # 编译后的正则模式
        self._dynamic_pattern_regex: list = []
        self._static_pattern_regex: list = []

    @classmethod
    def create_instance(cls, crawler) -> 'DynamicRenderMiddleware':
        """创建中间件实例"""
        instance = cls()

        # 从配置加载设置
        instance.enabled = crawler.settings.get_bool("DYNAMIC_RENDER_ENABLED", True)
        instance.cache_enabled = crawler.settings.get_bool("DYNAMIC_RENDER_CACHE_ENABLED", True)
        instance.default_dynamic = crawler.settings.get_bool("DYNAMIC_RENDER_DEFAULT_DYNAMIC", False)

        # 加载 URL 模式（用户显式配置）
        instance.dynamic_url_patterns = crawler.settings.get_list(
            "DYNAMIC_RENDER_URL_PATTERNS", []
        )

        instance.static_url_patterns = crawler.settings.get_list(
            "DYNAMIC_RENDER_STATIC_PATTERNS", []
        )

        # 加载域名配置
        instance.dynamic_domains = set(crawler.settings.get_list("DYNAMIC_RENDER_DOMAINS", []))
        instance.static_domains = set(crawler.settings.get_list("DYNAMIC_RENDER_STATIC_DOMAINS", []))

        # 编译正则模式
        instance._compile_patterns()

        # 只打印一次初始化日志
        if not DynamicRenderMiddleware._logged_init:
            DynamicRenderMiddleware._logged_init = True
            instance.logger.debug(
                f"DynamicRenderMiddleware initialized: enabled={instance.enabled}, "
                f"default_dynamic={instance.default_dynamic}, "
                f"dynamic_domains={list(instance.dynamic_domains)}, "
                f"dynamic_patterns={instance.dynamic_url_patterns}"
            )

        return instance

    def _compile_patterns(self):
        """编译正则模式"""
        self._dynamic_pattern_regex = [
            re.compile(pattern) for pattern in self.dynamic_url_patterns
        ]
        self._static_pattern_regex = [
            re.compile(pattern) for pattern in self.static_url_patterns
        ]

    async def process_request(self, request, spider) -> Optional[Any]:
        """
        处理请求：仅在拥有显式配置知识时设置下载器标记

        Returns:
            None: 继续处理流程
        """
        if not self.enabled:
            return None

        # 检查用户是否已显式指定（用户显式标记优先级最高，不覆盖）
        if 'use_dynamic_loader' in request.meta or 'use_protocol_loader' in request.meta:
            return None

        channel = self._resolve_channel(request)

        # 显式命中才打标；None（无显式知识）不打标，
        # 交由 HybridDownloader 按 HYBRID_* 规则/默认协议自行路由
        if channel == "dynamic":
            request.meta['use_dynamic_loader'] = True
        elif channel == "protocol":
            request.meta['use_protocol_loader'] = True

        return None

    def _resolve_channel(self, request) -> Optional[str]:
        """
        判定请求应使用的下载通道

        Detection strategy (by priority):
        1. URL pattern matching (user configured) -> "dynamic" / "protocol"
        2. Domain configuration (user configured) -> "dynamic" / "protocol"
        3. Cache query（缓存值均来自显式命中） -> "dynamic" / "protocol"
        4. Default value: default_dynamic=True -> "dynamic"；
           False -> None（不打标，交由 HybridDownloader 自身路由）

        Returns:
            "dynamic" / "protocol" / None
        """
        url = request.url
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower()

        # 1. Check URL pattern (user configured)
        for pattern in self._dynamic_pattern_regex:
            if pattern.search(url):
                self.logger.debug(f"URL pattern matched, using dynamic: {url}")
                self._cache_domain(url, True)  # Cache result
                return "dynamic"

        for pattern in self._static_pattern_regex:
            if pattern.search(url):
                self.logger.debug(f"Static URL pattern matched, using protocol: {url}")
                self._cache_domain(url, False)  # Cache result
                return "protocol"

        # 2. Check domain configuration (user configured)
        if domain in self.dynamic_domains:
            self.logger.debug(f"Domain in dynamic list: {domain}")
            self._cache_domain(url, True)  # Cache result
            return "dynamic"
        if domain in self.static_domains:
            self.logger.debug(f"Domain in static list: {domain}")
            self._cache_domain(url, False)  # Cache result
            return "protocol"

        # 3. Check cache (缓存内容均来自上面的显式命中)
        if self.cache_enabled and domain in self._domain_cache:
            return "dynamic" if self._domain_cache[domain] else "protocol"

        # 4. 默认回退：仅当用户显式要求默认动态时打 dynamic 标；
        #    默认静态时不打标——HybridDownloader 的默认通道同样是协议下载，
        #    行为等价，且不会短路 HYBRID_DYNAMIC_URL_PATTERNS 等规则。
        if self.default_dynamic:
            return "dynamic"
        return None

    def _cache_domain(self, url: str, needs_dynamic: bool):
        """缓存域名检测结果"""
        if not self.cache_enabled:
            return

        domain = urlparse(url).netloc.lower()

        # 限制缓存大小
        if len(self._domain_cache) >= self._cache_max_size:
            oldest_key = next(iter(self._domain_cache))
            del self._domain_cache[oldest_key]

        self._domain_cache[domain] = needs_dynamic

    def get_stats(self) -> Dict[str, Any]:
        """获取中间件统计信息"""
        return {
            'enabled': self.enabled,
            'cache_enabled': self.cache_enabled,
            'cache_size': len(self._domain_cache),
            'dynamic_domains_configured': len(self.dynamic_domains),
            'static_domains_configured': len(self.static_domains),
        }
