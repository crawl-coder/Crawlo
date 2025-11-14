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
from typing import Final, Set, Optional, TYPE_CHECKING
from contextlib import asynccontextmanager

from crawlo.logging import get_logger
from crawlo.middleware.middleware_manager import MiddlewareManager

if TYPE_CHECKING:
    from crawlo import Response


class ActivateRequestManager:
    """活跃请求管理器 - 跟踪和管理正在处理的请求"""

    def __init__(self):
        self._active: Final[Set] = set()
        self._total_requests: int = 0
        self._completed_requests: int = 0
        self._failed_requests: int = 0

    def add(self, request):
        """添加活跃请求"""
        self._active.add(request)
        self._total_requests += 1
        return request

    def remove(self, request, success: bool = True):
        """移除活跃请求并更新统计"""
        self._active.discard(request)  # 使用discard避免KeyError
        if success:
            self._completed_requests += 1
        else:
            self._failed_requests += 1

    @asynccontextmanager
    async def __call__(self, request):
        """上下文管理器用法"""
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
        """返回当前活跃请求数"""
        return len(self._active)
    
    def get_stats(self) -> dict:
        """获取请求统计信息"""
        completed = self._completed_requests + self._failed_requests
        return {
            'active_requests': len(self._active),
            'total_requests': self._total_requests,
            'completed_requests': self._completed_requests,
            'failed_requests': self._failed_requests,
            'success_rate': (
                self._completed_requests / completed * 100 
                if completed > 0 else 100.0  # 无完成请求时返回100%
            )
        }
    
    def reset_stats(self):
        """重置统计信息"""
        self._total_requests = 0
        self._completed_requests = 0
        self._failed_requests = 0
        # 注意：不清空 _active，因为可能有正在进行的请求


class DownloaderMeta(ABCMeta):
    def __subclasscheck__(self, subclass):
        required_methods = ('fetch', 'download', 'create_instance', 'close')
        is_subclass = all(
            hasattr(subclass, method) and callable(getattr(subclass, method, None)) for method in required_methods
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
        from crawlo.utils.misc import safe_get_config
        self._stats_enabled = safe_get_config(crawler.settings, "DOWNLOADER_STATS", True, bool)

    @classmethod
    def create_instance(cls, *args, **kwargs):
        """创建下载器实例"""
        return cls(*args, **kwargs)

    def open(self) -> None:
        """初始化下载器"""
        if self._closed:
            raise RuntimeError(f"{self.__class__.__name__} 已关闭，无法重新打开")
            
        # 获取下载器类的完整路径
        downloader_class = f"{type(self).__module__}.{type(self).__name__}"
        
        # 输出启用的下载器信息（类似MiddlewareManager的格式）
        self.logger.info(f"enabled downloader: \n  {downloader_class}")
        
        # 安全获取CONCURRENCY配置
        concurrency = 8
        if self.crawler and self.crawler.settings is not None:
            if hasattr(self.crawler.settings, 'get_int') and callable(getattr(self.crawler.settings, 'get_int', None)):
                try:
                    concurrency = self.crawler.settings.get_int('CONCURRENCY', 8)
                except Exception:
                    concurrency = 8
            elif isinstance(self.crawler.settings, dict):
                try:
                    concurrency = int(self.crawler.settings.get('CONCURRENCY', 8))
                except (TypeError, ValueError):
                    concurrency = 8
            else:
                try:
                    concurrency = int(getattr(self.crawler.settings, 'CONCURRENCY', 8))
                except (AttributeError, TypeError, ValueError):
                    concurrency = 8
        else:
            concurrency = 8
        
        # 输出下载器配置摘要
        self.logger.debug(
            f"{self.crawler.spider} <下载器类：{downloader_class}> "
            f"<并发数：{concurrency}>"
        )
        
        try:
            self.middleware = MiddlewareManager.create_instance(self.crawler)
            self.logger.debug(f"{self.__class__.__name__} 中间件初始化完成")
        except Exception as e:
            self.logger.error(f"中间件初始化失败: {e}")
            raise

    async def fetch(self, request) -> 'Optional[Response]':
        """获取请求响应（经过中间件处理）"""
        if self._closed:
            raise RuntimeError(f"{self.__class__.__name__} 已关闭")
            
        if not self.middleware:
            raise RuntimeError("中间件未初始化")
            
        async with self._active(request):
            try:
                response = await self.middleware.download(request)
                return response
            except Exception as e:
                self.logger.error(f"下载请求 {request.url} 失败: {e}")
                raise

    @abstractmethod
    async def download(self, request) -> 'Response':
        """子类必须实现的下载方法"""
        pass

    async def close(self) -> None:
        """关闭下载器并清理资源"""
        if not self._closed:
            self._closed = True
            if self._stats_enabled:
                stats = self.get_stats()
                self.logger.info(f"{self.__class__.__name__} 统计: {stats}")
            self.logger.debug(f"{self.__class__.__name__} 已关闭")

    def idle(self) -> bool:
        """检查是否空闲（无活跃请求）"""
        return len(self._active) == 0

    def __len__(self) -> int:
        """返回活跃请求数"""
        return len(self._active)
    
    def get_stats(self) -> dict:
        """获取下载器统计信息"""
        base_stats = {
            'downloader_class': self.__class__.__name__,
            'is_idle': self.idle(),
            'is_closed': self._closed
        }
        
        if self._stats_enabled:
            base_stats.update(self._active.get_stats())
            
        return base_stats
    
    def reset_stats(self):
        """重置统计信息"""
        if self._stats_enabled:
            self._active.reset_stats()
    
    def health_check(self) -> dict:
        """健康检查"""
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
    from .selenium_downloader import SeleniumDownloader
except ImportError:
    SeleniumDownloader = None

try:
    from .playwright_downloader import PlaywrightDownloader
except ImportError:
    PlaywrightDownloader = None

try:
    from .hybrid_downloader import HybridDownloader
except ImportError:
    HybridDownloader = None

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
if SeleniumDownloader:
    __all__.append('SeleniumDownloader')
if PlaywrightDownloader:
    __all__.append('PlaywrightDownloader')
if HybridDownloader:
    __all__.append('HybridDownloader')

# 提供便捷的下载器映射
DOWNLOADER_MAP = {
    'aiohttp': AioHttpDownloader,
    'httpx': HttpXDownloader, 
    'curl_cffi': CurlCffiDownloader,
    'cffi': CurlCffiDownloader,  # 别名
    'selenium': SeleniumDownloader,
    'playwright': PlaywrightDownloader,
    'hybrid': HybridDownloader,
}

# 过滤掉不可用的下载器
DOWNLOADER_MAP = {k: v for k, v in DOWNLOADER_MAP.items() if v is not None}

def get_downloader_class(name: str):
    """根据名称获取下载器类"""
    if name in DOWNLOADER_MAP:
        return DOWNLOADER_MAP[name]
    raise ValueError(f"未知的下载器类型: {name}。可用类型: {list(DOWNLOADER_MAP.keys())}")
