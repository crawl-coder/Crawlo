#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
混合下载器
=========
智能选择合适的下载器处理不同类型的请求，支持协议请求和动态加载内容。

支持的场景:
1. 列表页、详情页都要动态加载
2. 列表页使用协议请求、详情页使用动态加载
3. 列表页使用动态加载，详情页使用协议请求

功能特性:
1. 智能检测内容类型并选择合适的下载器
2. 支持基于URL模式的下载器选择
3. 支持基于请求标记的下载器选择
4. 统一的接口和响应格式
5. 自动资源管理和优化
6. 与 DynamicRenderMiddleware 分层协作

协作模式:
- DynamicRenderMiddleware（中间件层）：检测页面类型，设置请求标记
- HybridDownloader（下载器层）：读取标记，选择合适的下载器执行
"""
from typing import Optional, Dict, Type
from urllib.parse import urlparse

from crawlo.downloader import DownloaderBase
from crawlo.network.request import Request
from crawlo.network.response import Response
from crawlo.logging import get_logger

# 动态导入下载器（避免循环导入）
try:
    from .aiohttp_downloader import AioHttpDownloader
except ImportError:
    AioHttpDownloader = None

try:
    from .httpx_downloader import HttpXDownloader
except ImportError:
    HttpXDownloader = None

try:
    from .cffi_downloader import CurlCffiDownloader
except ImportError:
    CurlCffiDownloader = None

try:
    from .drissionpage_downloader import DrissionPageDownloader
except ImportError:
    DrissionPageDownloader = None

try:
    from .playwright_downloader import PlaywrightDownloader
except ImportError:
    PlaywrightDownloader = None


class HybridDownloader(DownloaderBase):
    """
    混合下载器 - 根据请求特征智能选择合适的下载器

    与 DynamicRenderMiddleware 分层协作：
    - 中间件层检测页面类型，设置 use_dynamic_loader / use_protocol_loader 标记
    - 下载器层读取标记，选择合适的下载器

    检测优先级：
    1. 请求标记（中间件设置或用户显式指定）
    2. URL 模式配置
    3. 域名配置
    4. 文件扩展名判断
    5. 请求方法判断
    6. URL 动态标识判断
    7. 默认策略
    """

    def __init__(self, crawler):
        super().__init__(crawler)
        self.logger = get_logger(self.__class__.__name__)

        # 下载器实例缓存
        self._downloaders: Dict[str, DownloaderBase] = {}

        # 配置选项
        self.default_protocol_downloader = crawler.settings.get("HYBRID_DEFAULT_PROTOCOL_DOWNLOADER", "aiohttp")
        self.default_dynamic_downloader = crawler.settings.get("HYBRID_DEFAULT_DYNAMIC_DOWNLOADER", "playwright")

        # URL模式配置
        self.dynamic_url_patterns = set(crawler.settings.get_list("HYBRID_DYNAMIC_URL_PATTERNS", []))
        self.protocol_url_patterns = set(crawler.settings.get_list("HYBRID_PROTOCOL_URL_PATTERNS", []))

        # 域名配置
        self.dynamic_domains = set(crawler.settings.get_list("HYBRID_DYNAMIC_DOMAINS", []))
        self.protocol_domains = set(crawler.settings.get_list("HYBRID_PROTOCOL_DOMAINS", []))

        # 是否启用智能检测日志
        self.verbose_logging = crawler.settings.get_bool("HYBRID_VERBOSE_LOGGING", False)

    def open(self):
        super().open()
        
        # 初始化默认下载器
        self._initialize_default_downloaders()

    def _initialize_default_downloaders(self):
        """初始化默认下载器
        
        默认只初始化协议下载器，动态下载器按需懒加载。
        这样可以避免不必要的 Playwright 初始化开销。
        """
        # 初始化协议下载器
        protocol_downloader_cls = self._get_downloader_class(self.default_protocol_downloader)
        if protocol_downloader_cls:
            self._downloaders["protocol"] = protocol_downloader_cls(self.crawler)
            self._downloaders["protocol"].open()
        
        # 动态下载器不预先初始化，按需懒加载
        # 只有当检测到需要动态渲染时，才在 _get_or_create_downloader 中初始化
        
        # 打印汇总日志
        protocol_downloader_name = self._downloaders["protocol"].__class__.__name__ if "protocol" in self._downloaders else "None"
        self.logger.info(
            f"enabled downloader: HybridDownloader (protocol: {protocol_downloader_name}, "
            f"dynamic: lazy-loaded)"
        )

    def _get_downloader_class(self, downloader_type: str) -> Optional[Type[DownloaderBase]]:
        """根据类型获取下载器类"""
        downloader_map = {
            "aiohttp": AioHttpDownloader,
            "httpx": HttpXDownloader,
            "curl_cffi": CurlCffiDownloader,
            "drissionpage": DrissionPageDownloader,
            "playwright": PlaywrightDownloader
        }
        return downloader_map.get(downloader_type.lower())

    async def download(self, request: Request) -> Optional[Response]:
        """根据请求特征选择合适的下载器并下载"""
        try:
            # 确定应该使用的下载器类型
            downloader_type = self._determine_downloader_type(request)
            
            # 获取对应的下载器
            downloader = self._get_or_create_downloader(downloader_type)
            if downloader is None:
                self.logger.error(f"No downloader available for type: {downloader_type}")
                return None
            
            self.logger.debug(f"Using {downloader_type} downloader for {request.url}")
            
            # 执行下载
            return await downloader.download(request)
        except Exception as e:
            self.logger.error(f"Error in hybrid downloader for {request.url}: {e}", exc_info=True)
            return None

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

        # 2. 检查URL模式配置
        for pattern in self.dynamic_url_patterns:
            if pattern in url:
                detection_reason = f"url_pattern:dynamic:{pattern}"
                if self.verbose_logging:
                    self.logger.debug(f"[Hybrid] {url} -> dynamic (reason: {detection_reason})")
                return "dynamic"

        for pattern in self.protocol_url_patterns:
            if pattern in url:
                detection_reason = f"url_pattern:protocol:{pattern}"
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
                if hasattr(downloader, 'close_async'):
                    await downloader.close_async()
                else:
                    await downloader.close()
            except Exception as e:
                self.logger.warning(f"Error closing {name} downloader: {e}")
                
        self._downloaders.clear()