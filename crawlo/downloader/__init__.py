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
- DownloaderBase: 下载器基类（ABC）
- ActivateRequestManager: 活跃请求管理器
"""

from abc import abstractmethod, ABC
from typing import Final, Set, Optional, TYPE_CHECKING, Dict, Any

from crawlo.logging import get_logger
from crawlo.middleware.middleware_manager import MiddlewareManager
from crawlo.utils.misc import safe_get_config

if TYPE_CHECKING:
    from crawlo import Response


class _ActivatedRequest:
    """类式上下文管理器（非生成器），避免 Python 3.12 asynccontextmanager + athrow(CancelledError) bug"""

    __slots__ = ('_mgr', '_request', '_success')

    def __init__(self, mgr: 'ActivateRequestManager', request):
        self._mgr = mgr
        self._request = request
        self._success = False

    async def __aenter__(self):
        self._mgr.add(self._request)
        return self._request

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self._success = True
        self._mgr.remove(self._request, self._success)
        return False  # 不抑制异常，让其向上传播


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
        self._active.discard(request)
        if success:
            self._completed_requests += 1
        else:
            self._failed_requests += 1

    def __call__(self, request):
        """返回类式上下文管理器（非 asynccontextmanager 生成器）"""
        return _ActivatedRequest(self, request)

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
        """Reset statistics (does not clear _active — ongoing requests preserved)"""
        self._total_requests = 0
        self._completed_requests = 0
        self._failed_requests = 0


class DownloaderBase(ABC):
    """下载器基类 — 所有下载器实现应继承此类"""
    
    def __init__(self, crawler):
        self.crawler = crawler
        self._active = ActivateRequestManager()
        self.middleware: Optional[MiddlewareManager] = None
        self.logger = get_logger(self.__class__.__name__)
        self._closed = False
        self._stats_enabled = safe_get_config(crawler.settings, "DOWNLOAD_STATS", True, bool)

    @classmethod
    def create_instance(cls, *args, **kwargs):
        """创建下载器实例"""
        return cls(*args, **kwargs)

    def open(self) -> None:
        """Initialize downloader"""
        if self._closed:
            raise RuntimeError(f"{self.__class__.__name__} is closed, cannot be reopened")
            
        downloader_class = f"{type(self).__module__}.{type(self).__name__}"
        
        # 判断是否为 HybridDownloader 的子下载器（不重复打印启用日志）
        is_hybrid = type(self).__name__ == 'HybridDownloader'
        is_sub_downloader = False
        if not is_hybrid and self.crawler and self.crawler.settings:
            main_downloader_cls = self._get_main_downloader_cls()
            if main_downloader_cls and main_downloader_cls.__name__ == 'HybridDownloader':
                is_sub_downloader = not isinstance(self, main_downloader_cls)

        if not is_sub_downloader and not is_hybrid:
            self.logger.info(f"enabled downloader: {downloader_class}")
    
        concurrency = safe_get_config(self.crawler.settings, "CONCURRENCY", 8, int)
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

    def _get_main_downloader_cls(self):
        """解析 settings 中配置的主下载器类（避免字符串匹配，使用 isinstance）"""
        from . import DOWNLOADER_MAP
        main_downloader_name = self.crawler.settings.get('DOWNLOADER', '')
        if not main_downloader_name:
            return None
        # 支持完整类路径（如 'crawlo.downloader.hybrid_downloader.HybridDownloader'）
        # 和短名称（如 'hybrid'）
        if main_downloader_name in DOWNLOADER_MAP:
            return DOWNLOADER_MAP[main_downloader_name]
        # 尝试按完整类路径加载
        try:
            from crawlo.utils.misc import load_object
            return load_object(main_downloader_name)
        except Exception:
            return None

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
        """Check if idle (no active requests) — 替代 bool() 判断"""
        return len(self._active) == 0

    def __len__(self) -> int:
        """Return active request count"""
        return len(self._active)
    
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


# ============================================================
# 延迟导入具体的下载器实现（仅在库可用时加载）
# 导入后修正 __module__，使日志/序列化显示短路径
# ============================================================

def _import_downloader(mod_name, cls_name):
    """导入下载器并设置 __module__ 为短路径"""
    try:
        import importlib
        mod = importlib.import_module(f'crawlo.downloader.{mod_name}')
        cls = getattr(mod, cls_name)
        cls.__module__ = 'crawlo.downloader'
        return cls
    except ImportError:
        return None

AioHttpDownloader = _import_downloader('aiohttp_downloader', 'AioHttpDownloader')
CurlCffiDownloader = _import_downloader('cffi_downloader', 'CurlCffiDownloader')
HttpXDownloader = _import_downloader('httpx_downloader', 'HttpXDownloader')
DrissionPageDownloader = _import_downloader('drissionpage_downloader', 'DrissionPageDownloader')
PlaywrightDownloader = _import_downloader('playwright_downloader', 'PlaywrightDownloader')
HybridDownloader = _import_downloader('hybrid_downloader', 'HybridDownloader')
CloakBrowserDownloader = _import_downloader('cloakbrowser_downloader', 'CloakBrowserDownloader')
CamoufoxDownloader = _import_downloader('camoufox_downloader', 'CamoufoxDownloader')


__all__ = [
    'DownloaderBase',
    'ActivateRequestManager',
]

# 添加可用的下载器到 __all__
_ALL_DOWNLOADERS = [
    ('AioHttpDownloader', AioHttpDownloader),
    ('CurlCffiDownloader', CurlCffiDownloader),
    ('HttpXDownloader', HttpXDownloader),
    ('DrissionPageDownloader', DrissionPageDownloader),
    ('PlaywrightDownloader', PlaywrightDownloader),
    ('HybridDownloader', HybridDownloader),
    ('CloakBrowserDownloader', CloakBrowserDownloader),
    ('CamoufoxDownloader', CamoufoxDownloader),
]
for name, cls in _ALL_DOWNLOADERS:
    if cls:
        __all__.append(name)

# 下载器映射（仅包含可用的）
DOWNLOADER_MAP = {
    'aiohttp': AioHttpDownloader,
    'httpx': HttpXDownloader,
    'curl_cffi': CurlCffiDownloader,
    'cffi': CurlCffiDownloader,
    'drissionpage': DrissionPageDownloader,
    'playwright': PlaywrightDownloader,
    'hybrid': HybridDownloader,
    'cloakbrowser': CloakBrowserDownloader,
    'camoufox': CamoufoxDownloader,
}
DOWNLOADER_MAP = {k: v for k, v in DOWNLOADER_MAP.items() if v is not None}


def get_downloader_class(name: str):
    """根据名称获取下载器类"""
    if name in DOWNLOADER_MAP:
        return DOWNLOADER_MAP[name]
    raise ValueError(f"未知的下载器类型: {name}。可用类型: {list(DOWNLOADER_MAP.keys())}")
