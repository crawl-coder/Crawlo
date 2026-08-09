#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Playwright 下载器
===============
支持动态加载内容的下载器，基于 Playwright 实现。

功能特性:
- 支持 Chromium/Firefox/WebKit 浏览器引擎
- 异步非阻塞操作
- 智能等待页面加载完成（多种等待策略）
- 资源屏蔽（屏蔽图片/CSS/字体/广告，提升性能）
- 反检测特性（隐藏 webdriver 标识）
- 自动滚动加载更多内容
- 支持自定义浏览器上下文和选项
- 内存安全的资源管理
- 自动处理 Cookie 和本地存储
- 支持翻页操作（鼠标滑动、点击翻页）
- 单浏览器多标签页模式
"""
import time
import asyncio
from typing import Optional, Dict, List, Set

from playwright.async_api import async_playwright, Playwright, Browser, Page, BrowserContext

from crawlo.downloader import DownloaderBase
from crawlo.downloader.stealth import StealthMixin
from crawlo.downloader.playwright_context import ContextProxyMixin
from crawlo.downloader.playwright_actions import PageActionsMixin
from crawlo.downloader.playwright_pool import PagePoolMixin
from crawlo.downloader.wait_strategies import SmartWaitMixin, WaitStrategy
from crawlo.downloader.constants import (
    DEFAULT_ARGS, STEALTH_ARGS, HARMFUL_ARGS,
    WEBRTC_PROTECTION_ARGS, WEBGL_DISABLE_ARGS, CANVAS_NOISE_ARG
)
from crawlo.http.response import Response
from crawlo.logging import get_logger
from crawlo.utils.misc import (
    get_browser_config,
    get_browser_config_int,
    get_browser_config_bool,
    get_browser_config_list,
)



class PlaywrightDownloader(
    DownloaderBase, SmartWaitMixin, StealthMixin,
    ContextProxyMixin, PageActionsMixin, PagePoolMixin,
):
    """
    基于 Playwright 的动态内容下载器
    支持处理 JavaScript 渲染的网页内容，性能优于 Selenium

    增强功能:
    - 智能等待策略：自动检测页面特征，选择最佳等待方式
    - 资源屏蔽：屏蔽图片/CSS/字体等，大幅提升加载速度
    - 反检测：隐藏 webdriver 标识，绕过基础反爬
    - 自动滚动：滚动加载懒加载内容
    """

    def __init__(self, crawler):
        super().__init__(crawler)
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.logger = get_logger(self.__class__.__name__)

        # 当前上下文使用的代理（用于检测代理变化，触发 Context 重建）
        self._current_proxy = None

        s = crawler.settings
        # === 浏览器通用配置（三级回退：PLAYWRIGHT_* → BROWSER_* → 默认值）===
        self.default_timeout = get_browser_config_int(s, "PLAYWRIGHT", "TIMEOUT", 30000)  # 毫秒
        self.load_timeout = get_browser_config_int(s, "PLAYWRIGHT", "LOAD_TIMEOUT", 10000)  # 毫秒
        self.headless = get_browser_config_bool(s, "PLAYWRIGHT", "HEADLESS", True)
        self.wait_for_element = get_browser_config(s, "PLAYWRIGHT", "WAIT_FOR_ELEMENT", None)
        self.viewport_width = get_browser_config_int(s, "PLAYWRIGHT", "VIEWPORT_WIDTH", 1280)
        self.viewport_height = get_browser_config_int(s, "PLAYWRIGHT", "VIEWPORT_HEIGHT", 720)
        self.wait_strategy = get_browser_config(s, "PLAYWRIGHT", "WAIT_STRATEGY", WaitStrategy.AUTO)
        self.wait_timeout = get_browser_config_int(s, "PLAYWRIGHT", "WAIT_TIMEOUT", 10000)
        self.block_resources: Set[str] = set(
            get_browser_config_list(s, "PLAYWRIGHT", "BLOCK_RESOURCES", ["image", "font", "media"])
        )
        self.stealth_level = get_browser_config(s, "PLAYWRIGHT", "STEALTH_LEVEL", "basic")
        self.auto_scroll = get_browser_config_bool(s, "PLAYWRIGHT", "AUTO_SCROLL", False)
        self.scroll_delay = get_browser_config_int(s, "PLAYWRIGHT", "SCROLL_DELAY", 500)

        # === Playwright 特有配置 ===
        self.browser_type = s.get("PLAYWRIGHT_BROWSER_TYPE", "chromium").lower()
        self.single_browser_mode = s.get_bool("PLAYWRIGHT_SINGLE_BROWSER_MODE", True)
        self.max_pages_per_browser = get_browser_config_int(s, "PLAYWRIGHT", "MAX_PAGES", 10)
        self.block_ads = s.get_bool("PLAYWRIGHT_BLOCK_ADS", True)
        self.block_webrtc = s.get_bool("PLAYWRIGHT_BLOCK_WEBRTC", False)
        self.hide_canvas = s.get_bool("PLAYWRIGHT_HIDE_CANVAS", False)
        self.allow_webgl = s.get_bool("PLAYWRIGHT_ALLOW_WEBGL", True)
        self.real_chrome = s.get_bool("PLAYWRIGHT_REAL_CHROME", False)
        self.google_referer = s.get_bool("PLAYWRIGHT_GOOGLE_REFERER", True)
        self.ignore_https_errors = s.get_bool("PLAYWRIGHT_IGNORE_HTTPS_ERRORS", True)
        self.scroll_count = s.get_int("PLAYWRIGHT_SCROLL_COUNT", 3)

        # === 页面池管理 ===
        self._page_pool: List[Page] = []  # 页面池（复用的tab）
        self._used_pages: set = set()  # 正在使用的页面ID
        self._page_semaphore: Optional[asyncio.Semaphore] = None  # 页面池信号量，控制最大并发数
        self._page_semaphore_lock = asyncio.Lock()  # 信号量操作锁，防止竞态条件
        self._init_lock = asyncio.Lock()  # 浏览器初始化锁，防止并发重复初始化

    def open(self):
        super().open()
        self.logger.info("Opening PlaywrightDownloader")

    async def download(self, request) -> Optional[Response]:
        """下载动态内容"""
        if not self.playwright or not self.browser or not self.context:
            # 加锁防止并发重复初始化
            async with self._init_lock:
                # double-check：获取锁后再次确认
                if not self.playwright or not self.browser or not self.context:
                    try:
                        await self._initialize_playwright()
                    except Exception as e:
                        self.logger.error(f"Failed to initialize Playwright for {request.url}: {e}")
                        return None

        # 检测代理变化：如果 request.proxy 与当前 Context 的代理不同，重建 Context
        await self._check_proxy_change(request)

        start_time = None
        if self.crawler.settings.get_bool("DOWNLOAD_STATS", True):
            start_time = time.time()

        page: Optional[Page] = None
        try:
            # 获取页面（支持单浏览器多标签页模式）
            page = await self._get_page()

            # 设置超时
            page.set_default_timeout(self.default_timeout)
            page.set_default_navigation_timeout(self.load_timeout)

            # 设置视口
            await page.set_viewport_size({
                "width": self.viewport_width,
                "height": self.viewport_height
            })
            
            # 设置 Google Referer，绕过某些检测
            referer = None
            if self.google_referer:
                referer = "https://www.google.com/"

            # ===== 应用反检测脚本（在导航前注入，必须保持）=====
            if self.stealth_level != 'none':
                await self._inject_stealth_scripts(page)

            # 应用请求特定的设置
            await self._apply_request_settings(page, request)

            # 访问页面（资源屏蔽延后到页面加载后）
            wait_until = self._get_wait_until(request)
            response = await page.goto(request.url, wait_until=wait_until, referer=referer)

            # ===== 页面加载后再设置资源屏蔽 =====
            await self._setup_resource_blocking(page, request)

            # ===== 智能等待页面加载 =====
            await self._smart_wait_for_page_load(page, request)

            # ===== 自动滚动加载更多内容 =====
            if self._should_auto_scroll(request):
                await self._auto_scroll_page(page, request)

            # 执行自定义操作（如果有）
            await self._execute_custom_actions(page, request)

            # 执行翻页操作（如果有）
            await self._execute_pagination_actions(page, request)

            # 等待页面稳定后获取内容（防止新导航导致 Page.content 失败）
            try:
                await page.wait_for_load_state("networkidle", timeout=5000)
            except Exception:
                await page.wait_for_timeout(500)
            page_content = await page.content()
            page_url = page.url

            # 获取响应信息
            status_code = response.status if response else 200
            headers = dict(response.headers) if response else {}

            # 获取 Cookies
            cookies = await self._get_cookies()

            # 构造响应对象
            crawlo_response = Response(
                url=page_url,
                headers=headers,
                status=status_code,
                body=page_content.encode('utf-8'),
                request=request
            )

            # 添加 Cookies 到响应
            crawlo_response.cookies = cookies

            # 记录下载统计
            if start_time:
                download_time = time.time() - start_time
                self.logger.debug(f"Downloaded {request.url} in {download_time:.3f}s")

            return crawlo_response

        except Exception as e:
            # 网络异常：重新抛出，交由 RetryMiddleware 处理
            # 使用 DEBUG 级别，不打印堆栈
            self.logger.debug(f"Download error for {request.url}: {type(e).__name__}: {e}")
            raise
        finally:
            # 归还页面到池中
            if page:
                await self._release_page(page)

    async def _initialize_playwright(self):
        """初始化 Playwright（代理不再在 launch 级设置，移至 Context 级）"""
        try:
            self.playwright = await async_playwright().start()

            # 获取代理配置
            proxy_config = self.crawler.settings.get("PLAYWRIGHT_PROXY")

            # 构建启动参数（不设置代理，代理在 Context 级设置）
            launch_kwargs = {
                "headless": self.headless,
                "args": list(DEFAULT_ARGS),  # 默认性能优化参数
            }

            # 如果启用隐身模式，添加隐身参数
            if self.stealth_level != 'none':
                launch_kwargs["args"].extend(STEALTH_ARGS)
                launch_kwargs["ignore_default_args"] = list(HARMFUL_ARGS)

                # WebRTC 保护
                if self.block_webrtc:
                    launch_kwargs["args"].extend(WEBRTC_PROTECTION_ARGS)

                # WebGL 控制
                if not self.allow_webgl:
                    launch_kwargs["args"].extend(WEBGL_DISABLE_ARGS)

                # Canvas 指纹保护
                if self.hide_canvas:
                    launch_kwargs["args"].append(CANVAS_NOISE_ARG)

            # 使用真实 Chrome 浏览器
            if self.real_chrome:
                launch_kwargs["channel"] = "chrome"

            # 根据配置选择浏览器类型
            if self.browser_type == "chromium":
                self.browser = await self.playwright.chromium.launch(**launch_kwargs)
            elif self.browser_type == "firefox":
                self.browser = await self.playwright.firefox.launch(**launch_kwargs)
            elif self.browser_type == "webkit":
                self.browser = await self.playwright.webkit.launch(**launch_kwargs)
            else:
                raise ValueError(f"Unsupported browser type: {self.browser_type}")

            # 创建浏览器上下文（代理在 Context 级设置）
            self.context = await self._create_context(proxy_config)

            # 初始化页面池信号量
            if self.single_browser_mode:
                self._page_semaphore = asyncio.Semaphore(self.max_pages_per_browser)

            # 应用全局设置
            await self._apply_global_settings()

            self.logger.debug(f"PlaywrightDownloader initialized with {self.browser_type} (stealth_level={self.stealth_level})")

        except Exception as e:
            self.logger.error(f"Failed to initialize Playwright: {e}")
            raise

    async def _get_cookies(self) -> Dict[str, str]:
        """获取 Cookies"""
        try:
            if self.context:
                playwright_cookies = await self.context.cookies()
                return {cookie['name']: cookie['value'] for cookie in playwright_cookies}
            return {}
        except Exception as e:
            self.logger.warning(f"Failed to get cookies: {e}")
            return {}

    async def close(self) -> None:
        """关闭 Playwright 资源"""
        try:
            # 关闭页面池中的所有页面
            if self._page_pool:
                self.logger.debug(f"Closing {len(self._page_pool)} page(s) in pool...")
                for page in self._page_pool:
                    try:
                        await page.close()
                    except Exception as e:
                        self.logger.warning(f"Error closing page: {e}")
                
                self._page_pool.clear()
                self._used_pages.clear()
            
            # 关闭上下文（会自动关闭所有临时标签页）
            if self.context:
                try:
                    await self.context.close()
                except Exception as e:
                    self.logger.warning(f"Error closing context: {e}")
                finally:
                    self.context = None
            
            # 关闭浏览器
            if self.browser:
                try:
                    await self.browser.close()
                except Exception as e:
                    self.logger.warning(f"Error closing browser: {e}")
                finally:
                    self.browser = None
            
            # 停止 Playwright
            if self.playwright:
                try:
                    await self.playwright.stop()
                except Exception as e:
                    self.logger.warning(f"Error stopping playwright: {e}")
                finally:
                    self.playwright = None
                    
            self.logger.info("PlaywrightDownloader closed.")
        except Exception as e:
            self.logger.error(f"Error during Playwright cleanup: {e}", exc_info=True)
            # 确保资源被清空
            self.context = None
            self.browser = None
            self.playwright = None
