#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
Crawlo Downloader Module
========================
提供多种高性能异步下载器实现。

下载器类型:
- AioHttpDownloader: 基于aiohttp的高性能下载器
- CurlCffiDownloader: 支持浏览器指纹模拟的curl-cffi下载器  
- HttpXDownloader: 支持HTTP/2的httpx下载器

核心类:
- DownloaderBase: 下载器基类
- ActivateRequestManager: 活跃请求管理器
"""
from abc import abstractmethod, ABCMeta
from typing import Final, Set, Optional, TYPE_CHECKING, Dict, Any
from contextlib import asynccontextmanager

from crawlo.logging import get_logger
from crawlo.middleware.middleware_manager import MiddlewareManager
from crawlo.utils.misc import safe_get_config

if TYPE_CHECKING:
    from crawlo import Response


class ActivateRequestManager:
    """活跃请求管理器 - 跟踪和管理正在处理的请求"""

    def __init__(self):
        self._active: Final[Set[Any]] = set()
        self._total_requests: int = 0
        self._completed_requests: int = 0
        self._failed_requests: int = 0

    def add(self, request):
        """Add active request"""
        self._active.add(request)
        self._total_requests += 1
        return request

    def remove(self, request, success: bool = True):
        """Remove active request and update statistics"""
        self._active.discard(request)  # Use discard to avoid KeyError
        if success:
            self._completed_requests += 1
        else:
            self._failed_requests += 1

    @asynccontextmanager
    async def __call__(self, request):
        """Context manager usage"""
        self.add(request)
        success = False
        try:
            yield request
            success = True
        except Exception:
            success = False
            raise
        finally:
            self.remove(request, success)

    def __len__(self):
        """Return current active request count"""
        return len(self._active)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get request statistics"""
        completed = self._completed_requests + self._failed_requests
        return {
            'active_requests': len(self._active),
            'total_requests': self._total_requests,
            'completed_requests': self._completed_requests,
            'failed_requests': self._failed_requests,
            'success_rate': (
                self._completed_requests / completed * 100 
                if completed > 0 else 100.0
            )
        }
    
    def reset_stats(self):
        """Reset statistics"""
        self._total_requests = 0
        self._completed_requests = 0
        self._failed_requests = 0
        # Note: Does not clear _active, as there may be ongoing requests


class DownloaderMeta(ABCMeta):
    """Downloader metaclass - validates required methods"""
    def __subclasscheck__(self, subclass):
        # Dynamically check required abstract methods from DownloaderBase
        required_methods = ('download', 'close')
        is_subclass = all(
            hasattr(subclass, method) and callable(getattr(subclass, method, None)) 
            for method in required_methods
        )
        return is_subclass


class DownloaderBase(metaclass=DownloaderMeta):
    """
    下载器基类 - 提供通用的下载器功能和接口
    
    所有下载器实现都应该继承此基类。
    """
    
    def __init__(self, crawler):
        self.crawler = crawler
        self._active = ActivateRequestManager()
        self.middleware: Optional[MiddlewareManager] = None
        self.logger = get_logger(self.__class__.__name__)
        self._closed = False
        
        # 安全获取DOWNLOADER_STATS配置
        self._stats_enabled = safe_get_config(crawler.settings, "DOWNLOADER_STATS", True, bool)

    @classmethod
    def create_instance(cls, *args, **kwargs):
        """创建下载器实例"""
        return cls(*args, **kwargs)

    def open(self) -> None:
        """Initialize downloader"""
        if self._closed:
            raise RuntimeError(f"{self.__class__.__name__} is closed, cannot be reopened")
            
        # Get downloader class full path
        downloader_class = f"{type(self).__module__}.{type(self).__name__}"
            
        # Sub-downloaders (managed by HybridDownloader) do not print enable logs separately
        # Judgment logic: Check if DOWNLOADER config is HybridDownloader
        # Dynamically determine if this is a sub-downloader by checking if it's not the main configured downloader
        is_sub_downloader = False
        if self.crawler and self.crawler.settings:
            if hasattr(self.crawler.settings, 'get'):
                main_downloader = self.crawler.settings.get('DOWNLOADER', '')
                # If main downloader is HybridDownloader and this is not HybridDownloader itself, it's a sub-downloader
                if main_downloader and 'HybridDownloader' in str(main_downloader):
                    is_sub_downloader = downloader_class != 'crawlo.downloader.hybrid_downloader.HybridDownloader'
                    
        # HybridDownloader itself does not print, subclasses handle it themselves
        is_hybrid = 'HybridDownloader' in downloader_class
                    
        if not is_sub_downloader and not is_hybrid:
            self.logger.info(f"enabled downloader: {downloader_class}")
    
        # Get concurrency configuration using safe_get_config
        concurrency = safe_get_config(self.crawler.settings, "CONCURRENCY", 8, int)
        
        # Output downloader configuration summary
        self.logger.debug(
            f"{self.crawler.spider} <Downloader class: {downloader_class}> "
            f"<Concurrency: {concurrency}>"
        )
        
        try:
            self.middleware = MiddlewareManager.create_instance(self.crawler)
            self.logger.debug(f"{self.__class__.__name__} middleware initialized")
        except Exception as e:
            self.logger.error(f"Middleware initialization failed: {e}")
            raise

    async def fetch(self, request) -> 'Optional[Response]':
        """Fetch request response (with middleware processing)"""
        if self._closed:
            raise RuntimeError(f"{self.__class__.__name__} is closed")
            
        if not self.middleware:
            raise RuntimeError("Middleware not initialized")
            
        async with self._active(request):
            try:
                response = await self.middleware.download(request)
                return response
            except Exception as e:
                # Use DEBUG level, no stack trace, exception will propagate to Engine
                self.logger.debug(f"Download failed for {request.url}: {type(e).__name__}: {e}")
                raise

    @abstractmethod
    async def download(self, request) -> 'Response':
        """Download method that subclasses must implement"""
        pass

    async def close(self) -> None:
        """Close downloader and cleanup resources"""
        if not self._closed:
            self._closed = True
            self.logger.debug(f"{self.__class__.__name__} closed")

    def idle(self) -> bool:
        """Check if idle (no active requests)"""
        return len(self._active) == 0

    def __len__(self) -> int:
        """Return active request count"""
        return len(self._active)
    
    def __bool__(self) -> bool:
        """Always return True, avoid being judged as False when active requests are empty"""
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """Get downloader statistics"""
        base_stats = {
            'downloader_class': self.__class__.__name__,
            'is_idle': self.idle(),
            'is_closed': self._closed
        }
        
        if self._stats_enabled:
            base_stats.update(self._active.get_stats())
            
        return base_stats
    
    def reset_stats(self):
        """Reset statistics"""
        if self._stats_enabled:
            self._active.reset_stats()
    
    def health_check(self) -> Dict[str, Any]:
        """Health check"""
        return {
            'status': 'healthy' if not self._closed and self.middleware else 'unhealthy',
            'active_requests': len(self._active),
            'middleware_ready': self.middleware is not None,
            'closed': self._closed
        }


# 导入具体的下载器实现
try:
    from .aiohttp_downloader import AioHttpDownloader
except ImportError:
    AioHttpDownloader = None

try:
    from .cffi_downloader import CurlCffiDownloader
except ImportError:
    CurlCffiDownloader = None

try:
    from .httpx_downloader import HttpXDownloader
except ImportError:
    HttpXDownloader = None

try:
    from .drissionpage_downloader import DrissionPageDownloader
except ImportError:
    DrissionPageDownloader = None

try:
    from .playwright_downloader import PlaywrightDownloader
except ImportError:
    PlaywrightDownloader = None

try:
    from .hybrid_downloader import HybridDownloader
except ImportError:
    HybridDownloader = None

try:
    from .cloakbrowser_downloader import CloakBrowserDownloader
except ImportError:
    CloakBrowserDownloader = None

try:
    from .page_action_handler import PageActionHandler, SelectorConverter
except ImportError:
    PageActionHandler = None
    SelectorConverter = None

# 导出所有可用的类
__all__ = [
    'DownloaderBase',
    'DownloaderMeta', 
    'ActivateRequestManager',
]

# 添加可用的下载器
if AioHttpDownloader:
    __all__.append('AioHttpDownloader')
if CurlCffiDownloader:
    __all__.append('CurlCffiDownloader')
if HttpXDownloader:
    __all__.append('HttpXDownloader')
if DrissionPageDownloader:
    __all__.append('DrissionPageDownloader')
if PlaywrightDownloader:
    __all__.append('PlaywrightDownloader')
if HybridDownloader:
    __all__.append('HybridDownloader')
if CloakBrowserDownloader:
    __all__.append('CloakBrowserDownloader')
if PageActionHandler:
    __all__.append('PageActionHandler')
if SelectorConverter:
    __all__.append('SelectorConverter')

# 提供便捷的下载器映射
DOWNLOADER_MAP = {
    'aiohttp': AioHttpDownloader,
    'httpx': HttpXDownloader, 
    'curl_cffi': CurlCffiDownloader,
    'cffi': CurlCffiDownloader,  # 别名
    'drissionpage': DrissionPageDownloader,
    'playwright': PlaywrightDownloader,
    'hybrid': HybridDownloader,
    'cloakbrowser': CloakBrowserDownloader,
}

# 过滤掉不可用的下载器
DOWNLOADER_MAP = {k: v for k, v in DOWNLOADER_MAP.items() if v is not None}

def get_downloader_class(name: str):
    """根据名称获取下载器类"""
    if name in DOWNLOADER_MAP:
        return DOWNLOADER_MAP[name]
    raise ValueError(f"未知的下载器类型: {name}。可用类型: {list(DOWNLOADER_MAP.keys())}")
