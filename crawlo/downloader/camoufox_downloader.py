#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Camoufox 下载器 (v0.4+ 同步 API)
=================================
基于 Camoufox 的隐身浏览器下载器。

Camoufox v0.4+ 变更为同步 API（camoufox.sync_api），
所有浏览器调用通过 `asyncio.to_thread()` 在后台线程执行。

Camoufox 特性:
- 基于 Firefox 的隐身浏览器
- 全链路指纹伪造（Canvas、WebGL、AudioContext 等）
- 内置 Cloudflare Turnstile 自动解决

依赖安装:
    pip install camoufox

使用示例:
    # settings.py
    DOWNLOADER = "crawlo.downloader.CamoufoxDownloader"
    CAMOUFOX_HEADLESS = True
    CAMOUFOX_HUMANIZE = True
"""
import time
import asyncio
import platform
from typing import Optional, Dict, List, Set
from urllib.parse import urlparse

from crawlo.downloader import DownloaderBase
from crawlo.utils.page_utils import PageActionHandler, SelectorConverter
from crawlo.network.response import Response
from crawlo.logging import get_logger
from crawlo.constants import BROWSER_ELEMENT_WAIT_TIMEOUT_MS
from crawlo.utils.misc import (
    get_browser_config,
    get_browser_config_int,
    get_browser_config_bool,
    get_browser_config_list,
)


class CamoufoxDownloader(DownloaderBase):
    """
    基于 Camoufox (v0.4+ sync API) 的隐身浏览器下载器
    """

    def __init__(self, crawler):
        super().__init__(crawler)
        self.logger = get_logger(self.__class__.__name__)

        # Camoufox 实例与页面引用
        self._browser = None
        self._page = None
        self._init_lock = asyncio.Lock()
        self._current_proxy = None

        s = crawler.settings
        self.headless = get_browser_config_bool(s, "CAMOUFOX", "HEADLESS", True)
        self.proxy = get_browser_config(s, "CAMOUFOX", "PROXY", None)
        self.humanize = get_browser_config_bool(s, "CAMOUFOX", "HUMANIZE", True)
        self.timeout = get_browser_config_int(s, "CAMOUFOX", "TIMEOUT", 30000)
        self.load_timeout = get_browser_config_int(s, "CAMOUFOX", "LOAD_TIMEOUT", 60000)
        self.viewport_width = get_browser_config_int(s, "CAMOUFOX", "VIEWPORT_WIDTH", 1280)
        self.viewport_height = get_browser_config_int(s, "CAMOUFOX", "VIEWPORT_HEIGHT", 720)
        self.block_resources: Set[str] = set(
            get_browser_config_list(s, "CAMOUFOX", "BLOCK_RESOURCES", ["image", "font", "media"])
        )
        self.auto_scroll = get_browser_config_bool(s, "CAMOUFOX", "AUTO_SCROLL", False)
        self.scroll_delay = get_browser_config_int(s, "CAMOUFOX", "SCROLL_DELAY", 500)
        self.wait_strategy = get_browser_config(s, "CAMOUFOX", "WAIT_STRATEGY", "auto")
        self.wait_timeout = get_browser_config_int(s, "CAMOUFOX", "WAIT_TIMEOUT", 10000)
        self.wait_for_element = get_browser_config(s, "CAMOUFOX", "WAIT_FOR_ELEMENT", None)
        self.solve_cloudflare = s.get_bool("CAMOUFOX_SOLVE_CLOUDFLARE", True)

    def open(self):
        super().open()
        self.logger.info("Opening CamoufoxDownloader (lazy initialization, sync API)")

    async def _initialize_browser(self, proxy=None):
        """初始化 Camoufox 浏览器（v0.4+ sync API）"""
        try:
            from camoufox import Camoufox
        except ImportError:
            raise ImportError(
                "Camoufox is not installed. Please install it with: pip install camoufox"
            )

        config = {
            "headless": self.headless,
            "humanize": self.humanize,
            "os": platform.system().lower() or "windows",
        }
        effective_proxy = proxy or self.proxy
        if effective_proxy:
            if isinstance(effective_proxy, str):
                config["proxy"] = {"server": effective_proxy}
            elif isinstance(effective_proxy, dict):
                config["proxy"] = effective_proxy
        if self.solve_cloudflare:
            config["solve_cloudflare"] = True

        # 同步 API: 在后台线程中创建实例并进入上下文
        def _create():
            browser = Camoufox(**config)
            page = browser.__enter__()  # with Camoufox() as page
            return browser, page

        self._browser, self._page = await asyncio.to_thread(_create)
        self._current_proxy = effective_proxy
        self.logger.info(
            f"Camoufox initialized (headless={self.headless}, "
            f"proxy={effective_proxy or 'direct'})"
        )

    # ---- 同步下载核心（在后台线程运行）----

    def _sync_download(self, request) -> Optional[Response]:
        """同步执行下载（在 asyncio.to_thread 中运行）"""
        page = self._page
        if page is None:
            return None

        try:
            response = page.goto(request.url, wait_until="domcontentloaded")
            page_content = page.content()
            page_url = page.url
            status_code = response.status if response else 200
            headers = dict(response.headers) if response else {}

            crawlo_response = Response(
                url=page_url,
                headers=headers,
                status=status_code,
                body=page_content.encode('utf-8'),
                request=request,
            )
            return crawlo_response
        except Exception as e:
            self.logger.debug(f"Sync download error for {request.url}: {type(e).__name__}: {e}")
            raise

    async def download(self, request) -> Optional[Response]:
        """下载动态内容"""
        # 懒加载初始化
        if not self._browser or not self._page:
            async with self._init_lock:
                if not self._browser or not self._page:
                    try:
                        await self._initialize_browser()
                    except Exception as e:
                        self.logger.error(f"Failed to initialize Camoufox for {request.url}: {e}")
                        return None

        # 后台线程执行同步下载
        try:
            return await asyncio.to_thread(self._sync_download, request)
        except Exception as e:
            self.logger.debug(f"Download error for {request.url}: {type(e).__name__}: {e}")
            raise

    async def close(self) -> None:
        """关闭浏览器资源"""
        self.logger.info("Closing CamoufoxDownloader...")

        def _close():
            if self._page:
                try:
                    self._page.close()
                except Exception:
                    pass
            if self._browser:
                try:
                    self._browser.__exit__(None, None, None)
                except Exception:
                    pass

        if self._browser or self._page:
            await asyncio.to_thread(_close)

        self._page = None
        self._browser = None
        self._current_proxy = None
        self.logger.info("CamoufoxDownloader closed successfully")
