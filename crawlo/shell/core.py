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
        self._user_ns = {}  # 交互式终端命名空间
        
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
                
                # 更新交互式命名空间中的 request/response
                self._user_ns['request'] = self.request
                self._user_ns['response'] = self.response
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
        self._user_ns.update({
            # 核心函数
            'fetch': self.sync_fetch,      # 同步 fetch（原生 Console 用）
            'view': self.view,             # 浏览器预览
            
            # 环境变量
            'request': self.request,
            'response': self.response,
            'settings': self.settings,
            
            # 工具类
            'Request': Request,
        })
        return self._user_ns
    
    def update_namespace(self) -> Dict[str, Any]:
        """更新命名空间中的动态变量（fetch 后调用）"""
        self._user_ns['request'] = self.request
        self._user_ns['response'] = self.response
        return self._user_ns
    
    # ==================== 终端启动 ====================
    
    async def start(self, url: Optional[str] = None) -> None:
        """
        启动交互式终端
        
        Args:
            url: 可选，启动时预抓取的 URL
        """
        # 初始化命名空间
        self.get_namespace()
        
        # 如有 URL，先抓取
        if url:
            self.logger.info(f"Pre-fetching {url}...")
            await self.fetch(url)
        
        # 启动终端
        try:
            from IPython import embed
            
            # 使用 IPython
            self._user_ns['fetch_async'] = self.fetch  # 保留异步版本
            
            self.logger.info("Starting IPython shell...")
            self.logger.info("Available: fetch(url), view(response), request, response, settings")
            self.logger.info("Use 'await fetch_async(url)' for async fetch in IPython")
            
            embed(
                user_ns=self._user_ns,
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
        
        banner = self._get_banner(url)
        banner += "\n(Note: Install IPython for async support: pip install ipython)"
        
        console = code.InteractiveConsole(locals=self._user_ns)
        console.interact(banner=banner, exitmsg="Crawlo Shell closed")
    
    def _get_banner(self, url: Optional[str] = None) -> str:
        """获取启动横幅"""
        lines = [
            "=" * 60,
            "  Crawlo Shell - Interactive Console",
            "=" * 60,
            "",
            "Available objects:",
            "  fetch(url)        - Fetch a URL and update request/response",
            "  view(response)    - Open response HTML in browser",
            "  request           - Last Request object",
            "  response          - Last Response object",
            "  settings          - Project settings",
            "",
            "Selector tips:",
            "  response.css('div.title::text').get()",
            "  response.xpath('//h1/text()').getall()",
            "  response.json()",
            "  response.css('.btn', adaptive=True).get() # Try adaptive mode",
            "",
            "Dynamic rendering (if HybridDownloader is used):",
            "  fetch(url, meta={'use_dynamic_loader': True})",
        ]
        
        if url:
            lines.append(f"")
            lines.append(f"Pre-fetched: {url}")
        
        lines.append("")
        lines.append("=" * 60)
        return "\n".join(lines)
    
    # ==================== 内部方法 ====================
    
    async def _get_downloader(self):
        """延迟初始化下载器
        
        优先级：
        1. AioHttpDownloader (框架下载器，绕过中间件直接 download)
        2. _SimpleFetcher (纯 aiohttp 回退)
        
        注意：不使用 HybridDownloader，因为其 _get_or_create_downloader()
        会调用子下载器的 open()，而 open() 必须初始化 MiddlewareManager，
        在 Shell 场景中无法提供完整 Crawler 上下文。
        """
        if self._downloader is not None:
            return self._downloader
        
        crawler = _MockCrawler(settings=self.settings)
        
        # 1. 尝试 AioHttpDownloader（轻量，session 由 _DownloaderAdapter 管理）
        try:
            from crawlo.downloader.aiohttp_downloader import AioHttpDownloader
            dl = AioHttpDownloader(crawler)
            self._downloader = _DownloaderAdapter(dl)
            self.logger.info("Using AioHttpDownloader (shell mode)")
            return self._downloader
        except Exception as e:
            self.logger.debug(f"Failed to init AioHttpDownloader: {e}")
        
        # 2. 回退到纯 aiohttp
        try:
            self._downloader = _SimpleFetcher()
            self.logger.info("Using simple aiohttp fetcher (no framework features)")
            return self._downloader
        except Exception as e:
            self.logger.error(f"Failed to initialize any downloader: {e}")
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
    
    Shell 场景不需要完整的中间件链。
    核心职责：
    1. 跳过 open()（避免 MiddlewareManager 初始化）
    2. 手动管理 session 生命周期（_ensure_session / close）
    3. 直接调用 download() 绕过 fetch() 的中间件链路
    """
    
    def __init__(self, downloader):
        self._downloader = downloader
        self._session_initialized = False
    
    async def fetch(self, request: Request) -> Optional[Response]:
        """直接调用下载器的 download 方法"""
        try:
            await self._ensure_session()
            return await self._downloader.download(request)
        except Exception as e:
            get_logger(__name__).error(f"Download error: {e}")
            return None
    
    async def _ensure_session(self):
        """确保下载器 session 已初始化
        
        对于 AioHttpDownloader，由于跳过了 open()，需要手动创建 session
        并设置必要的属性（max_download_size 等）。
        """
        if self._session_initialized:
            return
        
        dl = self._downloader
        
        if hasattr(dl, 'session') and dl.session is None:
            try:
                import aiohttp
                from aiohttp import TCPConnector
                
                dl.session = aiohttp.ClientSession(
                    connector=TCPConnector(limit=10, ttl_dns_cache=300),
                    timeout=aiohttp.ClientTimeout(total=30)
                )
                
                # 设置默认的最大下载大小（10MB）
                # open() 未调用时此值为 0，会导致所有请求被拒绝
                if hasattr(dl, 'max_download_size') and dl.max_download_size == 0:
                    dl.max_download_size = 10 * 1024 * 1024
                
                self._session_initialized = True
            except Exception as e:
                get_logger(__name__).debug(f"Failed to init session: {e}")
        else:
            self._session_initialized = True
    
    async def close(self):
        """关闭下载器，优先关闭手动创建的 session"""
        try:
            # 先关闭我们手动创建的 session
            if self._session_initialized and hasattr(self._downloader, 'session'):
                session = self._downloader.session
                if session and not getattr(session, 'closed', True):
                    await session.close()
                    self._downloader.session = None
            # 再尝试下载器自身的 close
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
