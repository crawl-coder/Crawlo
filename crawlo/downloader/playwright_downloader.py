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
import re
import asyncio
from typing import Optional, Dict, List, Set
from urllib.parse import urlparse

from playwright.async_api import async_playwright, Playwright, Browser, Page, BrowserContext

from crawlo.downloader import DownloaderBase
from crawlo.constants import BROWSER_PAGE_GOTO_BLANK_TIMEOUT_MS
from crawlo.utils.page_utils import PageActionHandler, SelectorConverter
from crawlo.downloader.stealth import StealthMixin
from crawlo.downloader.wait_strategies import SmartWaitMixin, WaitStrategy, ResourceType
from crawlo.downloader.constants import (
    DEFAULT_ARGS, STEALTH_ARGS, HARMFUL_ARGS,
    WEBRTC_PROTECTION_ARGS, WEBGL_DISABLE_ARGS, CANVAS_NOISE_ARG
)
from crawlo.network.response import Response
from crawlo.logging import get_logger
from crawlo.utils.misc import (
    get_browser_config,
    get_browser_config_int,
    get_browser_config_bool,
    get_browser_config_list,
)



class PlaywrightDownloader(DownloaderBase, SmartWaitMixin, StealthMixin):
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

    async def _create_context(self, proxy=None):
        """创建带代理的浏览器上下文

        Args:
            proxy: 代理配置，支持 str 或 dict 格式，None 表示直连

        Returns:
            BrowserContext 实例
        """
        context_options = {
            "viewport": {"width": self.viewport_width, "height": self.viewport_height},
            "screen": {"width": self.viewport_width, "height": self.viewport_height},
            "is_mobile": False,
            "has_touch": False,
            "color_scheme": "dark",
            "device_scale_factor": 2,
            "permissions": ["geolocation", "notifications"],
        }

        # 忽略 HTTPS 错误
        if self.ignore_https_errors:
            context_options["ignore_https_errors"] = True

        # Context 级代理设置（Playwright 原生支持）
        if proxy:
            if isinstance(proxy, str):
                context_options["proxy"] = {"server": proxy}
            elif isinstance(proxy, dict):
                context_options["proxy"] = proxy

        context = await self.browser.new_context(**context_options)
        self._current_proxy = proxy
        self.logger.info(f"Created browser context (proxy={proxy or 'direct'})")
        return context

    async def _check_proxy_change(self, request):
        """检测代理变化，必要时重建 Context

        代理来源优先级：
        1. request.proxy（由 ProxyMiddleware 设置，支持中途切换）
        2. request.meta['proxy_downgraded']（代理降级为直连）
        3. PLAYWRIGHT_PROXY 配置（静态代理，仅在初始化时使用）
        4. 无代理（直连）

        代理切换触发条件：
        - request.proxy 有值且与当前 Context 代理不同 → 切换到新代理
        - request.meta['proxy_downgraded'] 为 True → 降级为直连

        注意：request.proxy 为 None 且无 proxy_downgraded 标记时，
        视为"未指定代理"，保持当前 Context 不变（兼容无 ProxyMiddleware 的场景）。
        """
        request_proxy = getattr(request, 'proxy', None)
        proxy_downgraded = request.meta.get('proxy_downgraded', False)

        if not self.browser:
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
                f"rebuilding context..."
            )
            await self._rebuild_context(target_proxy)

    async def _rebuild_context(self, new_proxy=None):
        """重建浏览器上下文

        Args:
            new_proxy: 新代理配置，None 表示直连
        """
        # 1. 关闭所有页面
        if self._page_pool:
            for page in self._page_pool:
                try:
                    await page.close()
                except Exception:
                    pass
            self._page_pool.clear()
            self._used_pages.clear()

        # 2. 关闭旧 Context
        if self.context:
            try:
                await self.context.close()
            except Exception:
                pass
            self.context = None

        # 3. 创建新 Context
        self.context = await self._create_context(new_proxy)

        # 4. 重置信号量
        if self.single_browser_mode:
            self._page_semaphore = asyncio.Semaphore(self.max_pages_per_browser)

        # 5. 应用全局设置
        await self._apply_global_settings()

        self.logger.info(f"Context rebuilt with proxy: {new_proxy or 'direct'}")

    async def _apply_global_settings(self):
        """应用全局浏览器设置"""
        if not self.context:
            return
            
        # 设置用户代理
        user_agent = self.crawler.settings.get("USER_AGENT")
        if user_agent:
            await self.context.set_extra_http_headers({"User-Agent": user_agent})
        
        # 添加 Google Referer
        if self.google_referer:
            # 在请求级别设置，这里只做标记
            pass

    async def _apply_request_settings(self, page: Page, request):
        """应用请求特定的设置"""
        # 设置请求头
        if request.headers:
            await page.set_extra_http_headers(request.headers)

        # 设置 Cookies
        if request.cookies:
            cookies = []
            for name, value in request.cookies.items():
                # 需要确定域名和路径
                parsed_url = urlparse(request.url)
                cookies.append({
                    "name": name,
                    "value": value,
                    "domain": parsed_url.netloc,
                    "path": "/"
                })
            await page.context.add_cookies(cookies)

    async def _execute_custom_actions(self, page: Page, request):
        """
        执行自定义操作（通用接口，支持 dynamic_actions）
        
        支持的操作类型：
        - click: 点击元素（支持 XPath 和 CSS 选择器）
        - fill: 填充表单
        - wait: 等待
        - evaluate: 执行JavaScript
        - scroll: 滚动
        - scroll_to_bottom: 智能滚动到底部（适合懒加载页面）
        - click_and_wait: 点击并等待新内容（适合翻页）
        """
        # 使用通用处理器获取操作列表（兼容多种键名）
        custom_actions = PageActionHandler.get_actions_from_request(request)
        
        if custom_actions:
            self.logger.info(f"Executing {len(custom_actions)} custom action(s)...")
        
        for i, action in enumerate(custom_actions, 1):
            try:
                if isinstance(action, dict):
                    action_type = action.get("type")
                    action_params = action.get("params", {})
                    
                    self.logger.info(f"  [{i}/{len(custom_actions)}] Executing: {action_type}")
                    
                    if action_type == "scroll_to_bottom":
                        # 智能滚动到底部（封装好的懒加载滚动）
                        self.logger.info("    → Scrolling to bottom...")
                        await self._scroll_to_bottom(page, action_params)
                        self.logger.info("    ✓ Scroll completed")
                    elif action_type == "click":
                        selector = PageActionHandler.extract_selector(action)
                        if selector:
                            self.logger.info(f"    → Clicking: {selector}")
                            await self._click_with_selector(page, selector)
                            # 点击后等待内容加载
                            wait_timeout = action_params.get("wait_timeout", 1000)
                            await page.wait_for_timeout(wait_timeout)
                            self.logger.info("    ✓ Click completed")
                    elif action_type == "click_and_wait":
                        # 点击并等待新内容加载（适合翻页）
                        selector = PageActionHandler.extract_selector(action)
                        wait_timeout = action_params.get("wait_timeout", 2000)
                        wait_for = action_params.get("wait_for", "networkidle")
                        
                        if selector:
                            self.logger.info(f"    → Clicking and waiting: {selector}")
                            # 点击前记录内容数量
                            before_count = action_params.get("before_count")
                            
                            # 点击按钮（支持 XPath 和 CSS）
                            await self._click_with_selector(page, selector)
                            
                            # 等待新内容
                            if wait_for == "networkidle":
                                await page.wait_for_load_state("networkidle")
                            elif wait_for == "domcontentloaded":
                                await page.wait_for_load_state("domcontentloaded")
                            else:
                                await page.wait_for_timeout(wait_timeout)
                            
                            # 验证是否有新内容
                            if before_count:
                                after_count = await page.evaluate(before_count)
                                self.logger.debug(f"Page content count: {after_count}")
                            self.logger.info("    ✓ Click and wait completed")
                    elif action_type == "fill":
                        selector = PageActionHandler.extract_selector(action)
                        value = action_params.get("value")
                        if selector and value is not None:
                            self.logger.info(f"    → Filling: {selector}")
                            await self._fill_with_selector(page, selector, value)
                            self.logger.info("    ✓ Fill completed")
                    elif action_type == "wait":
                        timeout = action_params.get("timeout", 1000)
                        self.logger.info(f"    → Waiting {timeout}ms...")
                        await page.wait_for_timeout(timeout)
                        self.logger.info("    ✓ Wait completed")
                    elif action_type == "evaluate":
                        script = action_params.get("script")
                        if script:
                            self.logger.info("    → Executing JavaScript...")
                            await page.evaluate(script)
                            self.logger.info("    ✓ JavaScript executed")
                    elif action_type == "scroll":
                        position = action_params.get("position", "bottom")
                        self.logger.info(f"    → Scrolling to {position}...")
                        if position == "bottom":
                            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        elif position == "top":
                            await page.evaluate("window.scrollTo(0, 0)")
                        self.logger.info("    ✓ Scroll completed")
                    elif action_type == "click_in_frame":
                        # 跨 iframe 点击（解决跨域 iframe 内元素无法被 page.click 访问的问题）
                        frame_selector = action_params.get("frame", "")
                        selector = action_params.get("selector", "")
                        if frame_selector and selector:
                            target = page.frame(name=frame_selector) or page.frame(url=frame_selector)
                            if target:
                                await target.click(selector)
                                self.logger.info(f"    ✓ Clicked '{selector}' in frame '{frame_selector}'")
                            else:
                                self.logger.warning(f"    ✗ Frame not found: {frame_selector}")
                            
            except Exception as e:
                self.logger.warning(f"  ✗ Failed to execute action {i} ({action.get('type', 'unknown')}): {e}")

    async def _click_with_selector(self, page: Page, selector: str):
        """
        智能点击 - 自动识别 XPath 和 CSS 选择器
        
        Args:
            page: Playwright 页面对象
            selector: 选择器（XPath 或 CSS）
        """
        selector_type, clean_selector = SelectorConverter.normalize_selector(selector)
        
        if selector_type == "xpath":
            # 使用 XPath
            element = page.locator(f"xpath={clean_selector}")
            await element.click()
        else:
            # 使用 CSS
            await page.click(clean_selector)

    async def _fill_with_selector(self, page: Page, selector: str, value: str):
        """
        智能填充表单 - 自动识别 XPath 和 CSS 选择器
        
        Args:
            page: Playwright 页面对象
            selector: 选择器（XPath 或 CSS）
            value: 要填充的值
        """
        selector_type, clean_selector = SelectorConverter.normalize_selector(selector)
        
        if selector_type == "xpath":
            element = page.locator(f"xpath={clean_selector}")
            await element.fill(value)
        else:
            await page.fill(clean_selector, value)

    async def _execute_pagination_actions(self, page: Page, request):
        """执行翻页操作"""
        # 从请求的 meta 中获取翻页操作
        pagination_actions = request.meta.get("pagination_actions", [])
        
        for action in pagination_actions:
            try:
                if isinstance(action, dict):
                    action_type = action.get("type")
                    action_params = action.get("params", {})
                    
                    if action_type == "scroll":
                        # 鼠标滑动翻页
                        scroll_count = action_params.get("count", 1)
                        scroll_delay = action_params.get("delay", 1000)
                        scroll_distance = action_params.get("distance", 500)
                        
                        for _ in range(scroll_count):
                            await page.mouse.wheel(0, scroll_distance)
                            await page.wait_for_timeout(scroll_delay)
                            
                    elif action_type == "click":
                        # 鼠标点击翻页
                        selector = action_params.get("selector")
                        click_count = action_params.get("count", 1)
                        click_delay = action_params.get("delay", 1000)
                        
                        if selector:
                            for _ in range(click_count):
                                await page.click(selector)
                                await page.wait_for_timeout(click_delay)
                                
                    elif action_type == "evaluate":
                        # 执行自定义脚本翻页
                        script = action_params.get("script")
                        if script:
                            await page.evaluate(script)
                            
            except Exception as e:
                self.logger.warning(f"Failed to execute pagination action: {e}")

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

    async def _get_page(self) -> Page:
        """
        获取页面实例（单浏览器多标签页模式）
        
        策略：
        1. 使用 asyncio.Semaphore 控制并发，页面满时自动排队等待
        2. 优先复用池中空闲的标签页
        3. 如果池未满，创建新标签页
        4. 信号量和页面分配必须配对，防止泄漏
        """
        if not self.context:
            raise RuntimeError("Browser context not initialized")
        
        # 如果启用了单浏览器模式
        if self.single_browser_mode:
            # 等待信号量（如果已满，会在此挂起排队）
            await self._page_semaphore.acquire()
            semaphore_acquired = True  # 标记信号量已获取
            
            try:
                # 尝试从池中获取未使用的页面
                for page in self._page_pool:
                    if id(page) not in self._used_pages:
                        self._used_pages.add(id(page))
                        return page  # 成功获取页面
                
                # 池中无空闲页面，创建新页面
                new_page = await self.context.new_page()
                self._page_pool.append(new_page)
                self._used_pages.add(id(new_page))
                return new_page
                
            except Exception as e:
                # 任何异常都要释放信号量，防止泄漏
                if semaphore_acquired:
                    self._page_semaphore.release()
                self.logger.warning(f"Failed to get page: {e}")
                raise
        
        # 非单浏览器模式，直接创建新页面
        return await self.context.new_page()

    async def _release_page(self, page: Page):
        """
        释放页面（归还到池中复用）
        
        策略：
        1. 如果是池中的页面，标记为未使用并释放信号量
        2. 导航到 about:blank 清空内容以防泄露（在锁外执行，减少锁持有时间）
        3. 如果是临时页面（非单浏览器模式），直接关闭
        4. 使用锁保护关键区域，防止竞态条件
        """
        page_id = id(page)
        should_navigate_to_blank = False
        
        async with self._page_semaphore_lock:
            # 检查是否是池中的页面
            if page_id in self._used_pages:
                self._used_pages.discard(page_id)
                
                # 释放信号量，允许排队中的任务进入
                if self._page_semaphore:
                    self._page_semaphore.release()
                    self.logger.debug(f"Released semaphore, pool size: {len(self._page_pool)}, used: {len(self._used_pages)}")
                
                # 标记需要在锁外导航到空白页
                should_navigate_to_blank = True
            else:
                # 非池中页面，直接关闭
                self.logger.debug("Closing non-pooled page")
                try:
                    await page.close()
                except Exception as e:
                    self.logger.debug(f"Failed to close page: {e}")

        # 在锁外导航到空白页，减少锁持有时间，提高并发性能
        if should_navigate_to_blank:
            try:
                await page.goto("about:blank", timeout=BROWSER_PAGE_GOTO_BLANK_TIMEOUT_MS)
            except Exception as e:
                self.logger.debug(f"Failed to navigate to blank page: {e}")