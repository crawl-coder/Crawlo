#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
CrawloShell 核心类
==================
交互式终端的核心实现，提供 fetch、view 等功能。
"""
import os
import sys
import asyncio
import tempfile
import webbrowser
import atexit
from typing import Optional, Any, Dict

from crawlo.logging import get_logger
from crawlo.network.request import Request
from crawlo.network.response import Response


class _MockCrawler:
    """轻量级 Crawler 替身，供 Shell 中的下载器使用
    
    模拟完整 Crawler 接口，避免中间件初始化时因缺少属性而崩溃。
    """
    
    def __init__(self, settings=None):
        if settings is None or isinstance(settings, dict):
            try:
                from crawlo.settings.setting_manager import SettingManager
                sm = SettingManager()
                if isinstance(settings, dict):
                    # 合并用户配置到 SettingManager
                    for k, v in settings.items():
                        sm.attributes[k] = v
                self.settings = sm
            except Exception:
                self.settings = settings or {}
        else:
            self.settings = settings
        self.spider = _MockSpider()
        self.engine = None
        self.stats = None


class _MockSpider:
    """轻量级 Spider 替身"""
    name = 'shell'
    
    def __str__(self):
        return self.name
    

class CrawloShell:
    """
    Crawlo 交互式终端
    
    提供类似 scrapy shell 的实时交互环境：
    - fetch(url): 抓取页面并更新 request/response
    - view(response): 在浏览器中预览页面
    - 支持 IPython（await 异步代码）和原生 Console 降级
    """
    
    def __init__(self, settings: Optional[Any] = None):
        """
        初始化 Shell
        
        Args:
            settings: 项目配置对象
        """
        self.settings = settings or {}
        self.logger = get_logger(self.__class__.__name__)
        
        # 环境变量
        self.request: Optional[Request] = None
        self.response: Optional[Response] = None
        
        # 内部状态
        self._downloader = None
        self._loop = None
        self._temp_files = []
        
        # 注册清理
        atexit.register(self._cleanup_temp_files)
    
    # ==================== 核心方法 ====================
    
    async def fetch(self, url: str, **kwargs) -> Optional[Response]:
        """
        抓取 URL 并更新环境中的 request/response
        
        Args:
            url: 目标 URL
            **kwargs: 额外请求参数（如 headers, cookies, meta 等）
            
        Returns:
            Response 对象，失败时返回 None
        """
        try:
            # 延迟初始化下载器
            downloader = await self._get_downloader()
            if downloader is None:
                self.logger.error("下载器初始化失败")
                return None
            
            # 创建 Request
            self.request = Request(url=url, **kwargs)
            
            # 执行下载
            self.response = await downloader.fetch(self.request)
            
            if self.response:
                status = getattr(self.response, 'status_code', getattr(self.response, 'status', '?'))
                self.logger.info(f"Fetched {url} (status={status})")
            else:
                self.logger.warning(f"Failed to fetch {url}")
            
            return self.response
            
        except Exception as e:
            self.logger.error(f"Error fetching {url}: {type(e).__name__}: {e}")
            return None
    
    def sync_fetch(self, url: str, **kwargs) -> Optional[Response]:
        """
        同步版本的 fetch（供原生 Console 使用）
        
        Args:
            url: 目标 URL
            **kwargs: 额外请求参数
            
        Returns:
            Response 对象，失败时返回 None
        """
        return self._run_async(self.fetch(url, **kwargs))
    
    def view(self, response: Optional[Response] = None) -> None:
        """
        在浏览器中打开响应 HTML
        
        Args:
            response: 响应对象，默认使用最近一次的 response
        """
        resp = response or self.response
        if resp is None:
            self.logger.warning("No response available. Use fetch(url) first.")
            return
        
        # 获取 HTML 内容
        html = getattr(resp, 'text', getattr(resp, 'body', None))
        if html is None:
            self.logger.warning("Response has no HTML content")
            return
        
        if isinstance(html, bytes):
            encoding = getattr(resp, 'encoding', 'utf-8') or 'utf-8'
            html = html.decode(encoding, errors='replace')
        
        # 写入临时文件
        try:
            fd, path = tempfile.mkstemp(suffix='.html', prefix='crawlo_shell_')
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                f.write(html)
            self._temp_files.append(path)
            
            # 在浏览器中打开
            webbrowser.open(f'file://{path}')
            self.logger.info(f"Opened in browser: {path}")
        except Exception as e:
            self.logger.error(f"Failed to open browser: {e}")
    
    # ==================== 环境命名空间 ====================
    
    def get_namespace(self) -> Dict[str, Any]:
        """
        获取 Shell 环境命名空间
        
        Returns:
            可在交互式终端中使用的变量字典
        """
        return {
            # 核心函数
            'fetch': self.sync_fetch,      # 同步 fetch（原生 Console 用）
            'view': self.view,             # 浏览器预览
            
            # 环境变量
            'request': self.request,
            'response': self.response,
            'settings': self.settings,
            
            # 工具类
            'Request': Request,
        }
    
    def update_namespace(self) -> Dict[str, Any]:
        """更新命名空间中的动态变量（fetch 后调用）"""
        return {
            'request': self.request,
            'response': self.response,
        }
    
    # ==================== 终端启动 ====================
    
    async def start(self, url: Optional[str] = None) -> None:
        """
        启动交互式终端
        
        Args:
            url: 可选，启动时预抓取的 URL
        """
        # 如有 URL，先抓取
        if url:
            self.logger.info(f"Pre-fetching {url}...")
            await self.fetch(url)
        
        # 启动终端
        try:
            from IPython import embed
            from IPython.terminal.interactiveshell import TerminalInteractiveShell
            
            # 使用 IPython
            ns = self.get_namespace()
            ns['fetch_async'] = self.fetch  # 保留异步版本
            
            # 为 IPython 提供 asyncio 支持
            user_ns = ns.copy()
            
            self.logger.info("Starting IPython shell...")
            self.logger.info("Available: fetch(url), view(response), request, response, settings")
            self.logger.info("Use 'await fetch_async(url)' for async fetch in IPython")
            
            embed(
                user_ns=user_ns,
                colors='Neutral',
                banner2=self._get_banner(url),
            )
            
        except ImportError:
            # 降级到原生 Console
            self.logger.info("IPython not found, using standard Python console")
            self._start_basic_console(url)
    
    def _start_basic_console(self, url: Optional[str] = None) -> None:
        """启动原生 Python 交互式终端"""
        import code
        
        ns = self.get_namespace()
        banner = self._get_banner(url)
        banner += "\n(Note: Install IPython for async support: pip install ipython)"
        
        console = code.InteractiveConsole(locals=ns)
        console.interact(banner=banner, exitmsg="Crawlo Shell closed")
    
    def _get_banner(self, url: Optional[str] = None) -> str:
        """获取启动横幅"""
        lines = [
            "=" * 50,
            "  Crawlo Shell - Interactive Console",
            "=" * 50,
            "",
            "Available objects:",
            "  fetch(url)        - Fetch a URL and update request/response",
            "  view(response)    - Open response HTML in browser",
            "  request           - Last Request object",
            "  response          - Last Response object",
            "  settings          - Project settings",
        ]
        
        if url:
            lines.append(f"")
            lines.append(f"Pre-fetched: {url}")
        
        lines.append("")
        lines.append("=" * 50)
        return "\n".join(lines)
    
    # ==================== 内部方法 ====================
    
    async def _get_downloader(self):
        """延迟初始化下载器
        
        优先级：
        1. 框架下载器（通过 download 方法直接下载，绕过中间件）
        2. _SimpleFetcher（纯 aiohttp，无框架依赖）
        """
        if self._downloader is not None:
            return self._downloader
        
        # 先尝试框架下载器
        downloader = self._try_framework_downloader()
        if downloader is not None:
            self._downloader = _DownloaderAdapter(downloader)
            return self._downloader
        
        # 回退到纯 aiohttp
        try:
            self._downloader = _SimpleFetcher()
            self.logger.info("Using simple aiohttp fetcher")
            return self._downloader
        except Exception as e:
            self.logger.error(f"Failed to initialize any downloader: {e}")
            return None
    
    def _try_framework_downloader(self):
        """尝试创建框架下载器实例
        
        注意：Shell 场景下无法使用完整中间件链（需要 crawler.engine），
        因此这里创建的下载器仅用于直接调用 download() 方法（通过 _DownloaderAdapter），
        不走中间件。
        
        如果 open() 因中间件初始化失败，则跳过该下载器，回退到 _SimpleFetcher。
        """
        crawler = _MockCrawler(settings=self.settings)
        
        # 尝试 AioHttpDownloader（最轻量）
        try:
            from crawlo.downloader.aiohttp_downloader import AioHttpDownloader
            dl = AioHttpDownloader(crawler)
            # 跳过 open()，因为中间件初始化会失败
            # 直接通过 _DownloaderAdapter 调用 download()
            return dl
        except Exception:
            pass
        
        return None
    
    def _run_async(self, coro):
        """在事件循环中运行异步协程（同步包装）"""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        
        if loop and loop.is_running():
            # 如果已在事件循环中，创建任务
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, coro).result()
        else:
            return asyncio.run(coro)
    
    async def close(self) -> None:
        """关闭 Shell 并清理资源"""
        if self._downloader is not None:
            try:
                if hasattr(self._downloader, 'close'):
                    await self._downloader.close()
            except Exception as e:
                self.logger.debug(f"Error closing downloader: {e}")
            self._downloader = None
        
        self._cleanup_temp_files()
        self.logger.info("Shell closed")
    
    def _cleanup_temp_files(self) -> None:
        """清理临时文件"""
        for path in self._temp_files:
            try:
                if os.path.exists(path):
                    os.unlink(path)
            except Exception:
                pass
        self._temp_files.clear()


class _DownloaderAdapter:
    """下载器适配器，绕过中间件直接调用 download 方法
    
    Shell 场景不需要完整的中间件链，直接调用下载器的 download 方法即可。
    对于需要 session 的下载器（如 AioHttpDownloader），在首次 fetch 时自动初始化 session。
    """
    
    def __init__(self, downloader):
        self._downloader = downloader
        self._session_initialized = False
    
    async def fetch(self, request: Request) -> Optional[Response]:
        """直接调用下载器的 download 方法"""
        try:
            # 确保 session 已初始化（针对 AioHttpDownloader 等）
            await self._ensure_session()
            return await self._downloader.download(request)
        except Exception as e:
            get_logger(__name__).error(f"Download error: {e}")
            return None
    
    async def _ensure_session(self):
        """确保下载器 session 已初始化"""
        if self._session_initialized:
            return
        
        # 对于 AioHttpDownloader，手动创建 session
        if hasattr(self._downloader, 'session') and self._downloader.session is None:
            try:
                import aiohttp
                from aiohttp import TCPConnector
                self._downloader.session = aiohttp.ClientSession(
                    connector=TCPConnector(limit=10, ttl_dns_cache=300),
                    timeout=aiohttp.ClientTimeout(total=30)
                )
                # 设置默认的最大下载大小（10MB）
                if hasattr(self._downloader, 'max_download_size'):
                    if self._downloader.max_download_size == 0:
                        self._downloader.max_download_size = 10 * 1024 * 1024
                self._session_initialized = True
            except Exception as e:
                get_logger(__name__).debug(f"Failed to init session: {e}")
        else:
            self._session_initialized = True
    
    async def close(self):
        """关闭下载器"""
        try:
            # 如果我们创建了 session，先关闭它
            if self._session_initialized and hasattr(self._downloader, 'session'):
                session = self._downloader.session
                if session and not session.closed:
                    await session.close()
                    self._downloader.session = None
            await self._downloader.close()
        except Exception:
            pass


class _SimpleFetcher:
    """最简单的 HTTP 抓取器（无框架依赖时的回退方案）"""
    
    async def fetch(self, request: Request) -> Optional[Response]:
        """使用 aiohttp 直接抓取"""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    request.url,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    body = await resp.read()
                    return Response(
                        url=request.url,
                        status_code=resp.status,
                        headers=dict(resp.headers),
                        body=body,
                        request=request,
                    )
        except ImportError:
            get_logger(__name__).error("aiohttp is required. Install: pip install aiohttp")
            return None
        except Exception as e:
            get_logger(__name__).error(f"Fetch error: {e}")
            return None
    
    async def close(self):
        """无需清理"""
        pass
