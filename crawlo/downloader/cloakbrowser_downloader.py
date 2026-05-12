#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
CloakBrowser 下载器
====================
基于 CloakBrowser 的隐身动态内容下载器。

CloakBrowser 特性:
- 源码级修补的 Chromium（57 项 C++ 补丁）
- 内置全链路指纹伪造，无需 JS 注入
- reCAPTCHA v3 0.9+ 评分
- Cloudflare Turnstile 原生绕过
- 类人行为模拟（humanize）
- GeoIP 自动时区匹配
- 指纹种子持久化

依赖安装:
pip install cloakbrowser
pip install cloakbrowser[geoip]  # GeoIP 支持

使用示例:
# settings.py
DOWNLOADER = "crawlo.downloader.cloakbrowser_downloader.CloakBrowserDownloader"
CLOAKBROWSER_HEADLESS = False
CLOAKBROWSER_HUMANIZE = True
CLOAKBROWSER_GEOIP = True
"""

import time
import asyncio
from typing import Optional, Dict, List, Set

from crawlo.logging import get_logger
from crawlo.network.response import Response
from crawlo.downloader import DownloaderBase
from crawlo.downloader.wait_strategies import SmartWaitMixin, WaitStrategy
from crawlo.utils.page_utils import PageActionHandler, SelectorConverter
from crawlo.constants import BROWSER_PAGE_GOTO_BLANK_TIMEOUT_MS


class CloakBrowserDownloader(DownloaderBase, SmartWaitMixin):
    """
    基于 CloakBrowser 的隐身动态内容下载器

    CloakBrowser 是源码级修补的 Chromium，内置 57 项 C++ 补丁，
    无需 JS 注入即可绕过主流反机器人检测。

    相比 PlaywrightDownloader:
    - 无需 JS 注入即可绕过反检测（C++ 层内置）
    - 内置类人行为模拟（humanize）
    - GeoIP 自动时区匹配
    - 指纹种子持久化
    - reCAPTCHA v3 0.9+ 评分

    使用场景:
    - 高强度反爬网站（Cloudflare、DataDome、PerimeterX 等）
    - reCAPTCHA v3 Enterprise 评分系统
    - 需要持久化浏览器身份的场景
    - Playwright/Camoufox 被检测后的降级方案
    """

    def __init__(self, crawler):
        super().__init__(crawler)
        self.logger = get_logger(self.__class__.__name__)

        # 浏览器实例
        self._browser = None
        self._context = None

        # 页面池
        self._page_pool: List = []
        self._used_pages: set = set()
        self._page_semaphore: Optional[asyncio.Semaphore] = None
        self._page_semaphore_lock = asyncio.Lock()
        self._init_lock = asyncio.Lock()  # 浏览器初始化锁，防止并发重复初始化

        # 当前上下文使用的代理（用于检测代理变化，触发 Context 重建）
        self._current_proxy: Optional[str] = None

        # ===== 基础配置 =====
        self.headless = crawler.settings.get_bool("CLOAKBROWSER_HEADLESS", True)
        # 代理配置：优先使用 CLOAKBROWSER_PROXY（直接代理地址），
        # 未配置时自动从 PROXY_API_URL 获取（浏览器启动时解析）
        self.proxy = crawler.settings.get("CLOAKBROWSER_PROXY", None)
        self.proxy_api_url = crawler.settings.get("PROXY_API_URL", None)
        self.timeout = crawler.settings.get_int("CLOAKBROWSER_TIMEOUT", 30000)
        self.load_timeout = crawler.settings.get_int("CLOAKBROWSER_LOAD_TIMEOUT", 10000)
        self.viewport_width = crawler.settings.get_int("CLOAKBROWSER_VIEWPORT_WIDTH", 1280)
        self.viewport_height = crawler.settings.get_int("CLOAKBROWSER_VIEWPORT_HEIGHT", 720)
        self.max_pages = crawler.settings.get_int("CLOAKBROWSER_MAX_PAGES", 10)

        # ===== CloakBrowser 特有配置 =====
        self.humanize = crawler.settings.get_bool("CLOAKBROWSER_HUMANIZE", False)
        self.human_preset = crawler.settings.get("CLOAKBROWSER_HUMAN_PRESET", "default")
        self.human_config = crawler.settings.get("CLOAKBROWSER_HUMAN_CONFIG", None)
        self.geoip = crawler.settings.get_bool("CLOAKBROWSER_GEOIP", False)
        self.timezone = crawler.settings.get("CLOAKBROWSER_TIMEZONE", None)
        self.locale = crawler.settings.get("CLOAKBROWSER_LOCALE", None)
        self.backend = crawler.settings.get("CLOAKBROWSER_BACKEND", "playwright")
        self.stealth_args = crawler.settings.get_bool("CLOAKBROWSER_STEALTH_ARGS", True)
        self.fingerprint = crawler.settings.get("CLOAKBROWSER_FINGERPRINT", None)
        self.fingerprint_platform = crawler.settings.get("CLOAKBROWSER_FINGERPRINT_PLATFORM", None)
        self.extra_args = crawler.settings.get_list("CLOAKBROWSER_ARGS", [])

        # ===== 持久化配置 =====
        self.persistent_context = crawler.settings.get_bool("CLOAKBROWSER_PERSISTENT_CONTEXT", False)
        self.user_data_dir = crawler.settings.get("CLOAKBROWSER_USER_DATA_DIR", None)

        # ===== 等待策略 =====
        self.wait_strategy = crawler.settings.get("CLOAKBROWSER_WAIT_STRATEGY", WaitStrategy.AUTO)
        self.wait_timeout = crawler.settings.get_int("CLOAKBROWSER_WAIT_TIMEOUT", 10000)
        self.wait_for_element = crawler.settings.get("CLOAKBROWSER_WAIT_FOR_ELEMENT", None)

        # ===== 资源屏蔽 =====
        self.block_resources: Set[str] = set(
            crawler.settings.get_list("CLOAKBROWSER_BLOCK_RESOURCES", ["image", "font", "media"])
        )

        # ===== 自动滚动 =====
        self.auto_scroll = crawler.settings.get_bool("CLOAKBROWSER_AUTO_SCROLL", False)
        self.scroll_delay = crawler.settings.get_int("CLOAKBROWSER_SCROLL_DELAY", 500)

    def open(self):
        super().open()
        self.logger.info("Opening CloakBrowserDownloader (lazy initialization)")

    async def _initialize_browser(self):
        """懒加载：首次 download 时初始化浏览器（不设置代理，代理在 Context 级别设置）"""
        try:
            from cloakbrowser import launch_async
        except ImportError:
            raise ImportError(
                "CloakBrowser is not installed. "
                "Please install with: pip install cloakbrowser[geoip]"
            )

        proxy = None
        try:
            # 构建启动参数（代理不再在 launch 级设置，移至 Context 级）
            launch_kwargs = {
                "headless": self.headless,
                "humanize": self.humanize,
                "geoip": self.geoip,
                "stealth_args": self.stealth_args,
                "backend": self.backend,
            }

            # 代理解析：CLOAKBROWSER_PROXY > PROXY_API_URL 动态获取
            proxy = await self._resolve_proxy()
            # 注意：proxy 不再传入 launch_kwargs，而是由 _create_context 设置

            if self.timezone:
                launch_kwargs["timezone"] = self.timezone
            if self.locale:
                launch_kwargs["locale"] = self.locale
            if self.humanize and self.human_preset:
                launch_kwargs["human_preset"] = self.human_preset
            if self.humanize and self.human_config:
                launch_kwargs["human_config"] = self.human_config

            # 构建额外参数（含指纹种子）
            args = list(self.extra_args)
            if self.fingerprint is not None:
                args.append(f"--fingerprint={self.fingerprint}")
            if self.fingerprint_platform:
                args.append(f"--fingerprint-platform={self.fingerprint_platform}")
            if args:
                launch_kwargs["args"] = args

            # 启动超时：使用 CLOAKBROWSER_TIMEOUT（默认30s）作为启动上限
            # 注意：launch_async 涉及子进程启动，不响应 asyncio 取消信号，
            # 因此使用线程池+超时的方式确保不会无限卡住
            launch_timeout = self.timeout / 1000.0  # ms -> s
            self.logger.info(
                f"Launching CloakBrowser (headless={self.headless}, "
                f"proxy={proxy or 'none'}, humanize={self.humanize}, "
                f"geoip={self.geoip}, timeout={launch_timeout}s)..."
            )

            # 持久化上下文模式
            if self.persistent_context and self.user_data_dir:
                try:
                    from cloakbrowser import launch_persistent_context_async
                except ImportError:
                    raise ImportError(
                        "CloakBrowser persistent context requires cloakbrowser. "
                        "Please install with: pip install cloakbrowser[geoip]"
                    )
                # 持久化模式：代理仍需在 launch 级设置（无法重建 Context）
                if proxy:
                    launch_kwargs["proxy"] = proxy
                self._context = await self._launch_with_timeout(
                    launch_persistent_context_async(self.user_data_dir, **launch_kwargs),
                    timeout=launch_timeout,
                )
                self._browser = None  # 持久化模式无独立 Browser 对象
                self._current_proxy = proxy
            else:
                # 普通模式：launch → browser → context（代理在 Context 级设置）
                self._browser = await self._launch_with_timeout(
                    launch_async(**launch_kwargs),
                    timeout=launch_timeout,
                )
                self.logger.info("CloakBrowser launched, creating context...")
                self._context = await self._create_context(proxy)

            # 初始化信号量
            self._page_semaphore = asyncio.Semaphore(self.max_pages)

            self.logger.info(
                f"CloakBrowserDownloader initialized "
                f"(headless={self.headless}, humanize={self.humanize}, "
                f"geoip={self.geoip}, backend={self.backend})"
            )

        except ImportError:
            raise
        except asyncio.TimeoutError:
            proxy_info = f" with proxy {proxy}" if proxy else ""
            self.logger.error(
                f"CloakBrowser launch timed out after {self.timeout/1000:.0f}s"
                f"{proxy_info}. "
                f"Check if the proxy is reachable, or increase CLOAKBROWSER_TIMEOUT."
            )
            raise
        except Exception as e:
            self.logger.error(f"Failed to initialize CloakBrowser: {e}")
            raise

    async def _launch_with_timeout(self, launch_coro, timeout: float):
        """带强制超时的浏览器启动

        launch_async 涉及子进程启动，在 Windows 上不响应 asyncio 取消信号，
        因此采用双重策略：
        1. asyncio.wait_for 设置超时（正常情况下生效）
        2. 超时后强制终止残留的 Chromium 子进程

        Args:
            launch_coro: launch_async() 或 launch_persistent_context_async() 的协程
            timeout: 超时秒数

        Returns:
            浏览器实例
        """
        try:
            return await asyncio.wait_for(launch_coro, timeout=timeout)
        except asyncio.TimeoutError:
            # 超时后清理残留的 Chromium 子进程
            self._kill_orphan_chromium()
            raise

    def _kill_orphan_chromium(self):
        """清理超时后残留的 Chromium 子进程"""
        import subprocess
        import sys

        try:
            if sys.platform == "win32":
                # Windows: 通过 taskkill 强制终止 chromium/chrome 子进程
                _ = subprocess.run(
                    ["taskkill", "/F", "/IM", "chrome.exe"],
                    capture_output=True, timeout=5,
                )
                _ = subprocess.run(
                    ["taskkill", "/F", "/IM", "chromium.exe"],
                    capture_output=True, timeout=5,
                )
            else:
                # Linux/macOS: 通过 pkill 终止
                for pattern in ["chrome", "chromium", "chromium-browser"]:
                    try:
                        _ = subprocess.run(
                            ["pkill", "-f", pattern],
                            capture_output=True, timeout=5,
                        )
                    except Exception:
                        pass
            self.logger.warning("Cleaned up orphan Chromium processes after launch timeout")
        except Exception as e:
            self.logger.debug(f"Failed to clean up orphan processes: {e}")

    async def download(self, request) -> Optional[Response]:
        """下载动态内容"""
        # 懒加载初始化（加锁防止并发重复初始化）
        if not self._context:
            async with self._init_lock:
                # double-check：获取锁后再次确认
                if not self._context:
                    try:
                        await self._initialize_browser()
                    except Exception as e:
                        self.logger.error(f"Failed to initialize CloakBrowser for {request.url}: {e}")
                        return None

        # 检测代理变化：如果 request.proxy 与当前 Context 的代理不同，重建 Context
        await self._check_proxy_change(request)

        start_time = None
        if self.crawler.settings.get_bool("DOWNLOAD_STATS", True):
            start_time = time.time()

        page = None
        try:
            # 获取页面
            page = await self._get_page()

            # 设置超时
            page.set_default_timeout(self.timeout)
            page.set_default_navigation_timeout(self.load_timeout)

            # 设置视口
            await page.set_viewport_size({
                "width": self.viewport_width,
                "height": self.viewport_height,
            })

            # 资源屏蔽
            await self._setup_resource_blocking(page, request)

            # 请求级设置
            await self._apply_request_settings(page, request)

            # 导航
            wait_until = self._get_wait_until(request)
            response = await page.goto(request.url, wait_until=wait_until)

            # 智能等待
            await self._smart_wait_for_page_load(page, request)

            # 自动滚动
            if self._should_auto_scroll(request):
                await self._auto_scroll_page(page, request)

            # 自定义操作
            await self._execute_custom_actions(page, request)

            # 翻页操作
            await self._execute_pagination_actions(page, request)

            # 提取内容
            page_content = await page.content()
            page_url = page.url
            status_code = response.status if response else 200
            headers = dict(response.headers) if response else {}
            cookies = await self._get_cookies()

            # 构造响应
            crawlo_response = Response(
                url=page_url,
                headers=headers,
                status=status_code,
                body=page_content.encode('utf-8'),
                request=request,
            )
            crawlo_response.cookies = cookies

            if start_time:
                download_time = time.time() - start_time
                self.logger.debug(f"Downloaded {request.url} in {download_time:.3f}s")

            return crawlo_response

        except Exception as e:
            self.logger.debug(f"Download error for {request.url}: {type(e).__name__}: {e}")
            raise
        finally:
            if page:
                await self._release_page(page)

    # ---- 页面池管理 ----

    async def _create_context(self, proxy=None):
        """创建带代理的浏览器上下文

        Args:
            proxy: 代理地址，None 表示直连

        Returns:
            BrowserContext 实例
        """
        context_kwargs = {
            "viewport": {"width": self.viewport_width, "height": self.viewport_height},
            "ignore_https_errors": True,
        }

        # Context 级代理设置（Playwright 原生支持）
        if proxy:
            if isinstance(proxy, str):
                context_kwargs["proxy"] = {"server": proxy}
            elif isinstance(proxy, dict):
                context_kwargs["proxy"] = proxy

        context = await self._browser.new_context(**context_kwargs)
        self._current_proxy = proxy
        self.logger.info(f"Created browser context (proxy={proxy or 'direct'})")
        return context

    async def _check_proxy_change(self, request):
        """检测代理变化，必要时重建 Context

        代理来源优先级：
        1. request.proxy（由 ProxyMiddleware 设置，支持中途切换）
        2. request.meta['proxy_downgraded']（代理降级为直连）
        3. CLOAKBROWSER_PROXY 配置（静态代理，仅在初始化时使用）
        4. 无代理（直连）

        代理切换触发条件：
        - request.proxy 有值且与当前 Context 代理不同 → 切换到新代理
        - request.meta['proxy_downgraded'] 为 True → 降级为直连

        注意：request.proxy 为 None 且无 proxy_downgraded 标记时，
        视为"未指定代理"，保持当前 Context 不变（兼容无 ProxyMiddleware 的场景）。
        """
        request_proxy = getattr(request, 'proxy', None)
        proxy_downgraded = request.meta.get('proxy_downgraded', False)

        # 持久化模式无法重建 Context
        if self.persistent_context and self.user_data_dir:
            if (request_proxy and request_proxy != self._current_proxy) or proxy_downgraded:
                self.logger.warning(
                    f"Proxy change detected but persistent context "
                    f"does not support context rebuild. Current proxy: {self._current_proxy}"
                )
            return

        # 非持久化模式：检测代理变化
        if not self._browser:
            return

        # 确定目标代理
        if proxy_downgraded:
            # 代理降级：切换到直连
            target_proxy = None
        elif request_proxy:
            # 有新代理：切换到新代理
            target_proxy = request_proxy
        else:
            # 未指定代理：保持当前 Context 不变
            return

        if target_proxy != self._current_proxy:
            old_proxy = self._current_proxy
            self.logger.info(
                f"Proxy changed: {old_proxy or 'direct'} → {target_proxy or 'direct'}, "
                f"rebuilding context..."
            )
            await self._rebuild_context(target_proxy)

    async def _rebuild_context(self, new_proxy=None):
        """重建浏览器上下文（关闭旧的，创建新的）

        Args:
            new_proxy: 新代理地址，None 表示直连
        """
        # 1. 关闭所有页面
        for page in self._page_pool:
            try:
                await page.close()
            except Exception:
                pass
        self._page_pool.clear()
        self._used_pages.clear()

        # 2. 关闭旧 Context
        if self._context:
            try:
                await self._context.close()
            except Exception:
                pass
            self._context = None

        # 3. 创建新 Context
        self._context = await self._create_context(new_proxy)

        # 4. 重置信号量
        self._page_semaphore = asyncio.Semaphore(self.max_pages)

        self.logger.info(f"Context rebuilt with proxy: {new_proxy or 'direct'}")

    async def _resolve_proxy(self):
        """解析代理地址

        优先级：
        1. CLOAKBROWSER_PROXY - 直接指定的代理地址
        2. PROXY_API_URL - 从代理 API 动态获取

        代理 API 返回格式支持：
        - 简单字符串: {"proxy": "http://user:pass@ip:port"}
        - 嵌套对象: {"proxy": {"http": "http://...", "https": "http://..."}}
        - IP字段: {"ip": "1.2.3.4:8080"}
        """
        # 1. 直接指定的代理
        if self.proxy:
            self.logger.info(f"Using configured proxy: {self.proxy}")
            return self.proxy

        # 2. 从代理 API 获取
        if not self.proxy_api_url:
            return None

        self.logger.info(f"Fetching proxy from API: {self.proxy_api_url}")
        try:
            import aiohttp
            import json

            connector = aiohttp.TCPConnector(limit=5, force_close=True)
            timeout = aiohttp.ClientTimeout(total=10)

            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                async with session.get(self.proxy_api_url) as resp:
                    if resp.status == 200:
                        content_type = resp.headers.get('content-type', '')
                        if 'application/json' in content_type:
                            data = await resp.json()
                        else:
                            text = await resp.text()
                            data = json.loads(text)

                        # 支持多种字段名和嵌套格式
                        for key in ("proxy", "ip", "url", "address"):
                            if key in data:
                                proxy_value = data[key]
                                # 处理嵌套对象，如 {"proxy": {"http": "...", "https": "..."}}
                                if isinstance(proxy_value, dict):
                                    proxy_value = (
                                        proxy_value.get("https")
                                        or proxy_value.get("http")
                                        or proxy_value.get("url")
                                    )
                                if proxy_value is None:
                                    continue
                                proxy_value = str(proxy_value)
                                if not proxy_value.startswith("http"):
                                    proxy_value = f"http://{proxy_value}"
                                self.logger.info(f"Resolved proxy from API: {proxy_value}")
                                return proxy_value

                        self.logger.warning(f"Proxy API response missing proxy field: {list(data.keys())}")
                    else:
                        self.logger.warning(f"Proxy API returned status {resp.status}")
        except Exception as e:
            self.logger.warning(f"Failed to fetch proxy from API: {e}")

        return None

    async def _get_page(self):
        """获取页面（单浏览器多标签页模式 + 信号量控制并发）"""
        if not self._context:
            raise RuntimeError("Browser context not initialized")

        await self._page_semaphore.acquire()
        semaphore_acquired = True

        try:
            # 尝试从池中获取未使用的页面
            for page in self._page_pool:
                if id(page) not in self._used_pages:
                    self._used_pages.add(id(page))
                    return page

            # 池中无空闲页面，创建新页面
            new_page = await self._context.new_page()
            self._page_pool.append(new_page)
            self._used_pages.add(id(new_page))
            return new_page

        except Exception:
            if semaphore_acquired:
                self._page_semaphore.release()
            raise

    async def _release_page(self, page):
        """归还页面到池中

        优化：将 about:blank 导航移到锁外，减少锁持有时间，
        避免高并发下归还页面时阻塞其他页面获取。
        """
        page_id = id(page)
        should_navigate_to_blank = False

        async with self._page_semaphore_lock:
            if page_id in self._used_pages:
                self._used_pages.discard(page_id)
                if self._page_semaphore:
                    self._page_semaphore.release()
                    self.logger.debug(
                        f"Released page, pool size: {len(self._page_pool)}, "
                        f"used: {len(self._used_pages)}"
                    )
                # 标记需要导航到空白页（在锁外执行）
                should_navigate_to_blank = True
            else:
                # 非池中页面，直接关闭
                try:
                    await page.close()
                except Exception:
                    pass

        # 在锁外导航到空白页，准备下次使用
        if should_navigate_to_blank:
            try:
                await page.goto("about:blank", timeout=BROWSER_PAGE_GOTO_BLANK_TIMEOUT_MS)
            except Exception:
                pass

    # ---- 等待策略（覆盖 SmartWaitMixin，使用 cloakbrowser_ 前缀）----

    def _get_wait_until(self, request) -> str:
        """获取导航等待策略"""
        strategy = request.meta.get("cloakbrowser_wait_strategy", self.wait_strategy)

        if strategy == WaitStrategy.AUTO:
            return "domcontentloaded"
        elif strategy == WaitStrategy.NETWORK_IDLE:
            return "networkidle"
        elif strategy == WaitStrategy.DOM_READY:
            return "domcontentloaded"
        else:
            return "domcontentloaded"

    async def _smart_wait_for_page_load(self, page, request):
        """智能等待页面加载完成"""
        strategy = request.meta.get("cloakbrowser_wait_strategy", self.wait_strategy)

        try:
            if strategy == WaitStrategy.AUTO:
                await self._auto_wait_strategy(page, request)
            elif strategy == WaitStrategy.NETWORK_IDLE:
                await page.wait_for_load_state("networkidle", timeout=self.wait_timeout)
            elif strategy == WaitStrategy.DOM_READY:
                await page.wait_for_load_state("domcontentloaded", timeout=self.wait_timeout)
            elif strategy == WaitStrategy.ELEMENT:
                element_selector = request.meta.get("cloakbrowser_wait_element", self.wait_for_element)
                if element_selector:
                    await page.wait_for_selector(element_selector, timeout=self.wait_timeout)
            elif strategy == WaitStrategy.CUSTOM:
                custom_wait = request.meta.get("cloakbrowser_custom_wait")
                if custom_wait and callable(custom_wait):
                    await custom_wait(page)

            # 如果配置了全局等待特定元素
            if self.wait_for_element and strategy != WaitStrategy.ELEMENT:
                try:
                    await page.wait_for_selector(self.wait_for_element, timeout=self.load_timeout)
                except Exception:
                    self.logger.warning(
                        f"Wait element '{self.wait_for_element}' not found, continuing..."
                    )

        except Exception as e:
            self.logger.warning(f"Page load wait issue: {e}, continuing with current content")

    # ---- 资源屏蔽（覆盖 SmartWaitMixin，使用 cloakbrowser_ 前缀）----

    async def _setup_resource_blocking(self, page, request):
        """设置资源屏蔽"""
        block_resources = request.meta.get("cloakbrowser_block_resources", self.block_resources)

        if not block_resources:
            return

        async def route_handler(route):
            if route.request.resource_type in block_resources:
                await route.abort()
            else:
                await route.continue_()

        await page.route("**/*", route_handler)

    # ---- 自动滚动（覆盖 SmartWaitMixin，使用 cloakbrowser_ 前缀 + humanize 适配）----

    def _should_auto_scroll(self, request) -> bool:
        """判断是否需要自动滚动"""
        return request.meta.get("cloakbrowser_auto_scroll", self.auto_scroll)

    async def _auto_scroll_page(self, page, request):
        """智能滚动加载懒加载内容"""
        scroll_delay = request.meta.get("cloakbrowser_scroll_delay", self.scroll_delay)
        max_no_content = request.meta.get("cloakbrowser_max_no_content", 2)

        params = {
            "scroll_delay": scroll_delay,
            "max_no_content": max_no_content,
        }
        await self._scroll_to_bottom(page, params)

    async def _scroll_to_bottom(self, page, params: dict):
        """智能滚动到底部（适合懒加载页面）

        humanize 模式下使用 time.sleep 代替 page.wait_for_timeout，
        避免发出可被 reCAPTCHA 检测的 CDP 命令。
        """
        scroll_delay = params.get("scroll_delay", 500)
        max_no_content = params.get("max_no_content", 2)

        try:
            consecutive_no_content = 0

            while True:
                current_height = await page.evaluate("document.body.scrollHeight")
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

                # humanize 模式下使用 time.sleep 避免被 reCAPTCHA 检测
                if self.humanize:
                    time.sleep(scroll_delay / 1000)
                else:
                    await page.wait_for_timeout(scroll_delay)

                new_height = await page.evaluate("document.body.scrollHeight")

                if new_height > current_height:
                    consecutive_no_content = 0
                    self.logger.debug(
                        f"Scroll: {current_height} -> {new_height}px (new content loaded)"
                    )
                else:
                    consecutive_no_content += 1
                    self.logger.debug(
                        f"No new content ({consecutive_no_content}/{max_no_content})"
                    )
                    if consecutive_no_content >= max_no_content:
                        self.logger.debug("Reached page bottom after detecting no new content")
                        break

                # 安全检查：防止无限滚动
                if consecutive_no_content > 10:
                    self.logger.warning("Too many scrolls, stopping")
                    break

        except Exception as e:
            self.logger.warning(f"Scroll to bottom failed: {e}")

    # ---- 请求设置 ----

    async def _apply_request_settings(self, page, request):
        """应用请求特定的设置"""
        if request.headers:
            await page.set_extra_http_headers(request.headers)

        if request.cookies:
            from urllib.parse import urlparse
            parsed_url = urlparse(request.url)
            cookies = [
                {"name": k, "value": v, "domain": parsed_url.netloc, "path": "/"}
                for k, v in request.cookies.items()
            ]
            await page.context.add_cookies(cookies)

    # ---- 自定义操作 ----

    async def _execute_custom_actions(self, page, request):
        """执行自定义操作（通用接口，支持 dynamic_actions）

        humanize 模式下注意：
        - 使用 page.click(selector) 而非 query_selector().click()
        - 使用 page.type(selector, text) 而非 page.fill(selector, text)
        - 使用 time.sleep 而非 page.wait_for_timeout()
        """
        custom_actions = PageActionHandler.get_actions_from_request(request)

        if custom_actions:
            self.logger.info(f"Executing {len(custom_actions)} custom action(s)...")

        for i, action in enumerate(custom_actions, 1):
            try:
                if not isinstance(action, dict):
                    continue

                action_type = action.get("type")
                action_params = action.get("params", {})

                self.logger.info(f"  [{i}/{len(custom_actions)}] Executing: {action_type}")

                if action_type == "scroll_to_bottom":
                    await self._scroll_to_bottom(page, action_params)
                elif action_type == "click":
                    selector = PageActionHandler.extract_selector(action)
                    if selector:
                        await self._click_with_selector(page, selector)
                        # 点击后等待内容加载
                        wait_timeout = action_params.get("wait_timeout", 1000)
                        if self.humanize:
                            time.sleep(wait_timeout / 1000)
                        else:
                            await page.wait_for_timeout(wait_timeout)
                elif action_type == "click_and_wait":
                    selector = PageActionHandler.extract_selector(action)
                    if selector:
                        await self._click_with_selector(page, selector)
                        wait_for = action_params.get("wait_for", "networkidle")
                        if wait_for == "networkidle":
                            await page.wait_for_load_state("networkidle")
                        elif wait_for == "domcontentloaded":
                            await page.wait_for_load_state("domcontentloaded")
                        else:
                            wait_timeout = action_params.get("wait_timeout", 2000)
                            if self.humanize:
                                time.sleep(wait_timeout / 1000)
                            else:
                                await page.wait_for_timeout(wait_timeout)
                elif action_type == "fill":
                    selector = PageActionHandler.extract_selector(action)
                    value = action_params.get("value")
                    if selector and value is not None:
                        await self._fill_with_selector(page, selector, value)
                elif action_type == "wait":
                    timeout = action_params.get("timeout", 1000)
                    if self.humanize:
                        time.sleep(timeout / 1000)
                    else:
                        await page.wait_for_timeout(timeout)
                elif action_type == "evaluate":
                    script = action_params.get("script")
                    if script:
                        await page.evaluate(script)
                elif action_type == "scroll":
                    position = action_params.get("position", "bottom")
                    if position == "bottom":
                        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    elif position == "top":
                        await page.evaluate("window.scrollTo(0, 0)")

            except Exception as e:
                self.logger.warning(
                    f"  Failed to execute action {i} ({action.get('type', '?')}): {e}"
                )

    async def _click_with_selector(self, page, selector: str):
        """智能点击 - 自动识别 XPath 和 CSS 选择器

        humanize 模式下使用 page.click() 而非 ElementHandle.click()，
        确保操作经过人化管道。
        """
        selector_type, clean_selector = SelectorConverter.normalize_selector(selector)
        if selector_type == "xpath":
            await page.locator(f"xpath={clean_selector}").click()
        else:
            await page.click(clean_selector)

    async def _fill_with_selector(self, page, selector: str, value: str):
        """智能填充表单 - 自动识别 XPath 和 CSS 选择器

        humanize 模式下推荐使用 page.type() 而非 page.fill()，
        但为了通用性仍使用 fill（type 需要额外参数）。
        """
        selector_type, clean_selector = SelectorConverter.normalize_selector(selector)
        if selector_type == "xpath":
            await page.locator(f"xpath={clean_selector}").fill(value)
        else:
            await page.fill(clean_selector, value)

    # ---- 翻页操作 ----

    async def _execute_pagination_actions(self, page, request):
        """执行翻页操作

        humanize 模式下使用 time.sleep 代替 page.wait_for_timeout()，
        避免发出可被 reCAPTCHA 检测的 CDP 命令。
        """
        pagination_actions = request.meta.get("pagination_actions", [])

        for action in pagination_actions:
            try:
                if not isinstance(action, dict):
                    continue
                action_type = action.get("type")
                params = action.get("params", {})

                if action_type == "scroll":
                    for _ in range(params.get("count", 1)):
                        await page.mouse.wheel(0, params.get("distance", 500))
                        delay = params.get("delay", 1000)
                        if self.humanize:
                            time.sleep(delay / 1000)
                        else:
                            await page.wait_for_timeout(delay)
                elif action_type == "click":
                    selector = params.get("selector")
                    if selector:
                        for _ in range(params.get("count", 1)):
                            await page.click(selector)
                            delay = params.get("delay", 1000)
                            if self.humanize:
                                time.sleep(delay / 1000)
                            else:
                                await page.wait_for_timeout(delay)
                elif action_type == "evaluate":
                    script = params.get("script")
                    if script:
                        await page.evaluate(script)
            except Exception as e:
                self.logger.warning(f"Failed to execute pagination action: {e}")

    # ---- Cookies ----

    async def _get_cookies(self) -> Dict[str, str]:
        """获取 Cookies"""
        try:
            if self._context:
                cookies = await self._context.cookies()
                return {c['name']: c['value'] for c in cookies}
            return {}
        except Exception as e:
            self.logger.warning(f"Failed to get cookies: {e}")
            return {}

    # ---- 资源关闭 ----

    async def close(self) -> None:
        """关闭浏览器资源"""
        self.logger.info("Closing CloakBrowserDownloader...")

        # 关闭页面池
        for page in self._page_pool:
            try:
                await page.close()
            except Exception:
                pass
        self._page_pool.clear()
        self._used_pages.clear()

        # 关闭上下文
        if self._context:
            try:
                await self._context.close()
            except Exception:
                pass
            finally:
                self._context = None

        # 关闭浏览器（持久化模式无独立 browser）
        if self._browser:
            try:
                await self._browser.close()
            except Exception:
                pass
            finally:
                self._browser = None

        self.logger.info("CloakBrowserDownloader closed successfully")
