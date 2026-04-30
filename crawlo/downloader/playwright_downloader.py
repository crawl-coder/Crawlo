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
        self.default_timeout = crawler.settings.get_int("PLAYWRIGHT_TIMEOUT", 30000)  # 毫秒
        self.load_timeout = crawler.settings.get_int("PLAYWRIGHT_LOAD_TIMEOUT", 10000)  # 毫秒
        self.browser_type = crawler.settings.get("PLAYWRIGHT_BROWSER_TYPE", "chromium").lower()
        self.headless = crawler.settings.get_bool("PLAYWRIGHT_HEADLESS", True)
        self.wait_for_element = crawler.settings.get("PLAYWRIGHT_WAIT_FOR_ELEMENT", None)
        self.viewport_width = crawler.settings.get_int("PLAYWRIGHT_VIEWPORT_WIDTH", 1920)
        self.viewport_height = crawler.settings.get_int("PLAYWRIGHT_VIEWPORT_HEIGHT", 1080)

        # 单浏览器多标签页模式
        # 策略：启动一个浏览器，创建多个tab复用，控制最大并发数
        self.single_browser_mode = crawler.settings.get_bool("PLAYWRIGHT_SINGLE_BROWSER_MODE", True)
        self.max_pages_per_browser = crawler.settings.get_int("PLAYWRIGHT_MAX_PAGES_PER_BROWSER", 10)
        self._page_pool: List[Page] = []  # 页面池（复用的tab）
        self._used_pages: set = set()  # 正在使用的页面ID
        self._page_semaphore: Optional[asyncio.Semaphore] = None  # 页面池信号量，控制最大并发数
        self._page_semaphore_lock = asyncio.Lock()  # 信号量操作锁，防止竞态条件

        # ===== 智能等待配置 =====
        self.wait_strategy = crawler.settings.get("PLAYWRIGHT_WAIT_STRATEGY", WaitStrategy.AUTO)
        self.wait_timeout = crawler.settings.get_int("PLAYWRIGHT_WAIT_TIMEOUT", 10000)

        # ===== 资源屏蔽配置 =====
        self.block_resources: Set[str] = set(
            crawler.settings.get_list("PLAYWRIGHT_BLOCK_RESOURCES", ["image", "font", "media"])
        )
        self.block_ads = crawler.settings.get_bool("PLAYWRIGHT_BLOCK_ADS", True)
        # 使用常量中的广告域名黑名单

        # ===== 反检测配置 =====
        self.stealth_level = crawler.settings.get("PLAYWRIGHT_STEALTH_LEVEL", "basic")
        
        # ===== 高级反检测配置 =====
        self.block_webrtc = crawler.settings.get_bool("PLAYWRIGHT_BLOCK_WEBRTC", False)
        self.hide_canvas = crawler.settings.get_bool("PLAYWRIGHT_HIDE_CANVAS", False)
        self.allow_webgl = crawler.settings.get_bool("PLAYWRIGHT_ALLOW_WEBGL", True)
        self.real_chrome = crawler.settings.get_bool("PLAYWRIGHT_REAL_CHROME", False)
        self.google_referer = crawler.settings.get_bool("PLAYWRIGHT_GOOGLE_REFERER", True)
        self.ignore_https_errors = crawler.settings.get_bool("PLAYWRIGHT_IGNORE_HTTPS_ERRORS", True)

        # ===== 自动滚动配置 =====
        self.auto_scroll = crawler.settings.get_bool("PLAYWRIGHT_AUTO_SCROLL", False)
        self.scroll_count = crawler.settings.get_int("PLAYWRIGHT_SCROLL_COUNT", 3)
        self.scroll_delay = crawler.settings.get_int("PLAYWRIGHT_SCROLL_DELAY", 500)

    def open(self):
        super().open()
        self.logger.info("Opening PlaywrightDownloader")

    async def download(self, request) -> Optional[Response]:
        """下载动态内容"""
        if not self.playwright or not self.browser or not self.context:
            try:
                await self._initialize_playwright()
            except Exception as e:
                self.logger.error(f"Failed to initialize Playwright for {request.url}: {e}")
                return None

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

            # ===== 设置资源屏蔽（在导航前设置）=====
            await self._setup_resource_blocking(page, request)

            # ===== 应用反检测脚本（在导航前注入）=====
            if self.stealth_level != 'none':
                await self._inject_stealth_scripts(page)

            # 应用请求特定的设置
            await self._apply_request_settings(page, request)

            # 访问页面 - 根据等待策略选择不同的 wait_until
            wait_until = self._get_wait_until(request)
            response = await page.goto(request.url, wait_until=wait_until, referer=referer)

            # ===== 智能等待页面加载 =====
            await self._smart_wait_for_page_load(page, request)

            # ===== 自动滚动加载更多内容 =====
            if self._should_auto_scroll(request):
                await self._auto_scroll_page(page, request)

            # 执行自定义操作（如果有）
            await self._execute_custom_actions(page, request)

            # 执行翻页操作（如果有）
            await self._execute_pagination_actions(page, request)

            # 获取页面内容
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
        """初始化 Playwright"""
        try:
            self.playwright = await async_playwright().start()
            
            # 获取代理配置
            proxy_config = self.crawler.settings.get("PLAYWRIGHT_PROXY")
            
            # 构建启动参数
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
            
            # 如果配置了代理，则添加代理参数
            if proxy_config:
                if isinstance(proxy_config, str):
                    # 简单的代理URL
                    launch_kwargs["proxy"] = {
                        "server": proxy_config
                    }
                elif isinstance(proxy_config, dict):
                    # 完整的代理配置
                    launch_kwargs["proxy"] = proxy_config
            
            # 根据配置选择浏览器类型
            if self.browser_type == "chromium":
                self.browser = await self.playwright.chromium.launch(**launch_kwargs)
            elif self.browser_type == "firefox":
                self.browser = await self.playwright.firefox.launch(**launch_kwargs)
            elif self.browser_type == "webkit":
                self.browser = await self.playwright.webkit.launch(**launch_kwargs)
            else:
                raise ValueError(f"Unsupported browser type: {self.browser_type}")
            
            # 创建浏览器上下文
            context_options = {
                "viewport": {"width": self.viewport_width, "height": self.viewport_height},
                "screen": {"width": self.viewport_width, "height": self.viewport_height},
                "is_mobile": False,
                "has_touch": False,
                # 暗色主题绕过 creepjs 的 prefersLightColor 检测
                "color_scheme": "dark",
                "device_scale_factor": 2,
                "permissions": ["geolocation", "notifications"],
            }
            
            # 忽略 HTTPS 错误
            if self.ignore_https_errors:
                context_options["ignore_https_errors"] = True
            
            self.context = await self.browser.new_context(**context_options)
            
            # 初始化页面池信号量
            if self.single_browser_mode:
                self._page_semaphore = asyncio.Semaphore(self.max_pages_per_browser)
            
            # 应用全局设置
            await self._apply_global_settings()
            
            self.logger.debug(f"PlaywrightDownloader initialized with {self.browser_type} (stealth_level={self.stealth_level})")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Playwright: {e}")
            raise

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
            
        # 设置代理
        proxy = self.crawler.settings.get("PLAYWRIGHT_PROXY")
        if proxy:
            # Playwright 的代理设置在启动浏览器时配置
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
        2. 导航到 about:blank 清空内容以防泄露
        3. 如果是临时页面（非单浏览器模式），直接关闭
        4. 使用锁保护关键区域，防止竞态条件
        """
        page_id = id(page)
        
        async with self._page_semaphore_lock:
            # 检查是否是池中的页面
            if page_id in self._used_pages:
                self._used_pages.discard(page_id)
                
                # 释放信号量，允许排队中的任务进入
                if self._page_semaphore:
                    self._page_semaphore.release()
                    self.logger.debug(f"Released semaphore, pool size: {len(self._page_pool)}, used: {len(self._used_pages)}")
                
                # 清空页面内容，准备下次使用
                try:
                    await page.goto("about:blank", timeout=BROWSER_PAGE_GOTO_BLANK_TIMEOUT_MS)
                except Exception as e:
                    self.logger.debug(f"Failed to navigate to blank page: {e}")
            else:
                # 非池中页面，直接关闭
                self.logger.debug("Closing non-pooled page")
                try:
                    await page.close()
                except Exception as e:
                    self.logger.debug(f"Failed to close page: {e}")