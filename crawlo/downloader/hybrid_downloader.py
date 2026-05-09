#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Hybrid Downloader
=================
Intelligently selects appropriate downloader for different request types, supporting protocol requests and dynamic content.

Supported scenarios:
1. Both list and detail pages require dynamic loading
2. List page uses protocol requests, detail page uses dynamic loading
3. List page uses dynamic loading, detail page uses protocol requests

Features:
1. Intelligent content type detection and downloader selection
2. URL pattern-based downloader selection
3. Request marker-based downloader selection
4. Unified interface and response format
5. Automatic resource management and optimization
6. Layered collaboration with DynamicRenderMiddleware

Collaboration model:
- DynamicRenderMiddleware (middleware layer): Detects page type, sets request markers
- HybridDownloader (downloader layer): Reads markers, selects appropriate downloader
"""
import importlib
from typing import Optional, Dict, Type, List
import re
from urllib.parse import urlparse

from crawlo.downloader import DownloaderBase
from crawlo.network.request import Request
from crawlo.network.response import Response
from crawlo.logging import get_logger


class HybridDownloader(DownloaderBase):
    """
    Hybrid Downloader - Intelligently selects appropriate downloader based on request characteristics

    Layered collaboration with DynamicRenderMiddleware:
    - Middleware layer detects page type, sets use_dynamic_loader / use_protocol_loader markers
    - Downloader layer reads markers, selects appropriate downloader

    Detection priority:
    1. Request markers (set by middleware or user-specified)
    2. URL pattern configuration
    3. Domain configuration
    4. File extension detection
    5. Request method detection
    6. URL dynamic identifier detection
    7. Default strategy
    """

    def __init__(self, crawler):
        super().__init__(crawler)
        self.logger = get_logger(self.__class__.__name__)

        # 下载器实例缓存
        self._downloaders: Dict[str, DownloaderBase] = {}

        # 配置选项
        self.default_protocol_downloader = crawler.settings.get("HYBRID_DEFAULT_PROTOCOL_DOWNLOADER", "aiohttp")
        self.default_dynamic_downloader = crawler.settings.get("HYBRID_DEFAULT_DYNAMIC_DOWNLOADER", "playwright")

        # URL模式配置（支持正则表达式）
        self.dynamic_url_patterns: List[re.Pattern] = [
            re.compile(p) for p in crawler.settings.get_list("HYBRID_DYNAMIC_URL_PATTERNS", [])
        ]
        self.protocol_url_patterns: List[re.Pattern] = [
            re.compile(p) for p in crawler.settings.get_list("HYBRID_PROTOCOL_URL_PATTERNS", [])
        ]

        # Domain configuration
        self.dynamic_domains = set(crawler.settings.get_list("HYBRID_DYNAMIC_DOMAINS", []))
        self.protocol_domains = set(crawler.settings.get_list("HYBRID_PROTOCOL_DOMAINS", []))

        # Enable smart detection logging
        self.verbose_logging = crawler.settings.get_bool("HYBRID_VERBOSE_LOGGING", False)

    def open(self):
        super().open()
        
        # 初始化默认下载器
        self._initialize_default_downloaders()

    def _initialize_default_downloaders(self):
        """Initialize default downloaders
        
        By default, only protocol downloader is initialized, dynamic downloader is lazy-loaded.
        This avoids unnecessary Playwright initialization overhead.
        """
        # Initialize protocol downloader
        protocol_downloader_cls = self._get_downloader_class(self.default_protocol_downloader)
        if protocol_downloader_cls:
            self._downloaders["protocol"] = protocol_downloader_cls(self.crawler)
            self._downloaders["protocol"].open()
        
        # Dynamic downloader is not pre-initialized, lazy-loaded on demand
        # Only initialized in _get_or_create_downloader when dynamic rendering is detected
        
        # Print summary log
        protocol_downloader_name = self._downloaders["protocol"].__class__.__name__ if "protocol" in self._downloaders else "None"
        self.logger.info(
            f"enabled downloader: HybridDownloader (protocol: {protocol_downloader_name}, "
            f"dynamic: lazy-loaded)"
        )

    def _get_downloader_class(self, downloader_type: str) -> Optional[Type[DownloaderBase]]:
        """Get downloader class by type (lazy loading to avoid circular imports and unnecessary startup overhead)"""
        # Downloader mapping configuration: (module relative path, class name)
        downloader_map = {
            "aiohttp": (".aiohttp_downloader", "AioHttpDownloader"),
            "httpx": (".httpx_downloader", "HttpXDownloader"),
            "curl_cffi": (".cffi_downloader", "CurlCffiDownloader"),
            "drissionpage": (".drissionpage_downloader", "DrissionPageDownloader"),
            "playwright": (".playwright_downloader", "PlaywrightDownloader"),
            "camoufox": (".camoufox_downloader", "CamoufoxDownloader"),
        }
        
        target = downloader_type.lower()
        if target not in downloader_map:
            return None
            
        module_path, class_name = downloader_map[target]
        
        try:
            # Dynamic import module, package parameter ensures relative imports work correctly
            module = importlib.import_module(module_path, package=__package__)
            return getattr(module, class_name)
        except (ImportError, AttributeError) as e:
            self.logger.error(f"Failed to load downloader '{downloader_type}': {e}")
            return None

    async def download(self, request: Request) -> Optional[Response]:
        """根据请求特征选择合适的下载器并下载"""
        # 确定应该使用的下载器类型
        downloader_type = self._determine_downloader_type(request)
        
        # 获取对应的下载器
        downloader = self._get_or_create_downloader(downloader_type)
        if downloader is None:
            self.logger.error(f"No downloader available for type: {downloader_type}")
            return None
        
        self.logger.debug(f"Using {downloader_type} downloader for {request.url}")
        
        # 执行下载（异常应该传播到 MiddlewareManager，由重试中间件处理）
        return await downloader.download(request)

    def _determine_downloader_type(self, request: Request) -> str:
        """
        根据请求特征确定下载器类型

        检测优先级：
        1. 请求标记（中间件设置或用户显式指定）- 最高优先级
        2. URL 模式配置
        3. 域名配置
        4. 文件扩展名判断
        5. 默认策略：使用协议下载器

        注意：不再自动检测 POST 请求或 URL 关键词，
              只有在明确配置时才使用动态下载器。

        Returns:
            "dynamic" - 使用动态下载器
            "protocol" - 使用协议下载器
        """
        url = request.url
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower()

        # 1. 检查请求标记（最高优先级，由 DynamicRenderMiddleware 或用户设置）
        if request.meta.get("use_dynamic_loader"):
            detection_reason = "request_meta:use_dynamic_loader"
            if self.verbose_logging:
                self.logger.debug(f"[Hybrid] {url} -> dynamic (reason: {detection_reason})")
            return "dynamic"
        elif request.meta.get("use_protocol_loader"):
            detection_reason = "request_meta:use_protocol_loader"
            if self.verbose_logging:
                self.logger.debug(f"[Hybrid] {url} -> protocol (reason: {detection_reason})")
            return "protocol"

        # 2. 检查URL模式配置（使用正则表达式匹配）
        for pattern in self.dynamic_url_patterns:
            if pattern.search(url):
                detection_reason = f"url_pattern:dynamic:{pattern.pattern}"
                if self.verbose_logging:
                    self.logger.debug(f"[Hybrid] {url} -> dynamic (reason: {detection_reason})")
                return "dynamic"

        for pattern in self.protocol_url_patterns:
            if pattern.search(url):
                detection_reason = f"url_pattern:protocol:{pattern.pattern}"
                if self.verbose_logging:
                    self.logger.debug(f"[Hybrid] {url} -> protocol (reason: {detection_reason})")
                return "protocol"

        # 3. 检查域名配置
        if domain in self.dynamic_domains:
            detection_reason = f"domain_config:dynamic:{domain}"
            if self.verbose_logging:
                self.logger.debug(f"[Hybrid] {url} -> dynamic (reason: {detection_reason})")
            return "dynamic"

        if domain in self.protocol_domains:
            detection_reason = f"domain_config:protocol:{domain}"
            if self.verbose_logging:
                self.logger.debug(f"[Hybrid] {url} -> protocol (reason: {detection_reason})")
            return "protocol"

        # 4. 检查文件扩展名（静态资源通常有特定扩展名）
        path = parsed_url.path.lower()
        static_extensions = {'.js', '.css', '.jpg', '.jpeg', '.png', '.gif', '.ico', '.pdf', '.zip', '.doc', '.docx'}
        if any(path.endswith(ext) for ext in static_extensions):
            detection_reason = "file_extension:static"
            if self.verbose_logging:
                self.logger.debug(f"[Hybrid] {url} -> protocol (reason: {detection_reason})")
            return "protocol"

        # 5. 默认使用协议下载器
        # 不再自动检测 POST 请求或 URL 关键词
        detection_reason = "default:protocol"
        if self.verbose_logging:
            self.logger.debug(f"[Hybrid] {url} -> protocol (reason: {detection_reason})")
        return "protocol"

    def _get_or_create_downloader(self, downloader_type: str) -> Optional[DownloaderBase]:
        """获取或创建下载器实例"""
        # 如果已经存在，直接返回
        if downloader_type in self._downloaders:
            return self._downloaders[downloader_type]
        
        # 创建新的下载器实例
        if downloader_type == "protocol":
            downloader_cls = self._get_downloader_class(self.default_protocol_downloader)
        elif downloader_type == "dynamic":
            downloader_cls = self._get_downloader_class(self.default_dynamic_downloader)
        else:
            self.logger.warning(f"Unknown downloader type: {downloader_type}")
            return None
            
        if downloader_cls is None:
            self.logger.warning(f"Failed to get downloader class for: {downloader_type}")
            return None
            
        downloader = downloader_cls(self.crawler)
        downloader.open()
            
        self._downloaders[downloader_type] = downloader
        return downloader

    async def close(self) -> None:
        """关闭所有下载器"""
        for name, downloader in self._downloaders.items():
            try:
                await downloader.close()
            except Exception as e:
                self.logger.warning(f"Error closing {name} downloader: {e}")
                
        self._downloaders.clear()