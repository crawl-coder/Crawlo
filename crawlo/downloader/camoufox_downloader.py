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
import asyncio
from typing import Optional, Set

from crawlo.downloader import DownloaderBase
from crawlo.http.response import Response
from crawlo.logging import get_logger
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
            # Camoufox v0.4+ 自动检测系统版本，不显式传递 os 参数
        }
        effective_proxy = proxy or self.proxy
        if effective_proxy:
            if isinstance(effective_proxy, str):
                config["proxy"] = {"server": effective_proxy}
            elif isinstance(effective_proxy, dict):
                config["proxy"] = effective_proxy

        # 排除内置插件（UBO 下载常因网络问题失败）
        try:
            from camoufox.addons import DefaultAddons
            config["exclude_addons"] = [DefaultAddons.UBO]
        except ImportError:
            pass

        # 同步 API: 在后台线程中创建实例并进入上下文
        # Camoufox v0.4+ __enter__() 返回 Browser，需用 new_page() 获取页面
        def _create():
            browser = Camoufox(**config)
            browser_instance = browser.__enter__()  # 返回 playwright.sync_api.Browser
            page = browser_instance.new_page()
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

        # 代理切换检测（浏览器重启式：Camoufox 代理在浏览器实例级，变更需重启）
        await self._check_proxy_change(request)

        # 后台线程执行同步下载
        try:
            return await asyncio.to_thread(self._sync_download, request)
        except Exception as e:
            self.logger.debug(f"Download error for {request.url}: {type(e).__name__}: {e}")
            raise

    async def _check_proxy_change(self, request):
        """检测代理变化，必要时重启浏览器（浏览器重启式代理切换）

        代理来源优先级：
        1. request.proxy（由 ProxyMiddleware 设置，支持中途切换）
        2. request.meta['proxy_downgraded']（代理降级为直连）
        3. CAMOUFOX_PROXY 配置（静态代理，仅在初始化时使用）
        4. 无代理（直连）

        代理切换触发条件：
        - request.proxy 有值且与当前代理不同 → 重启浏览器并切换到新代理
        - request.meta['proxy_downgraded'] 为 True → 降级为直连

        注意：request.proxy 为 None 且无 proxy_downgraded 标记时，
        视为"未指定代理"，保持当前浏览器不变（兼容无 ProxyMiddleware 的场景）。
        """
        request_proxy = getattr(request, 'proxy', None)
        proxy_downgraded = request.meta.get('proxy_downgraded', False)

        if not self._browser:
            return

        # 确定目标代理
        if proxy_downgraded:
            target_proxy = None
        elif request_proxy:
            target_proxy = request_proxy
        else:
            return

        if target_proxy != self._current_proxy:
            old_proxy = self._current_proxy
            self.logger.info(
                f"Proxy changed: {old_proxy or 'direct'} → {target_proxy or 'direct'}, "
                f"restarting browser..."
            )
            await self._restart_browser(target_proxy)

    async def _restart_browser(self, proxy=None):
        """重启浏览器：关闭旧实例，用新代理重新初始化"""
        await self.close()
        await self._initialize_browser(proxy=proxy)

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
