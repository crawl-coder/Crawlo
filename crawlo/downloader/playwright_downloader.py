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
from typing import Optional, Dict, List, Set
from urllib.parse import urlparse

from playwright.async_api import async_playwright, Playwright, Browser, Page, BrowserContext

from crawlo.downloader import DownloaderBase
from crawlo.utils.page_utils import PageActionHandler, SelectorConverter
from crawlo.downloader.stealth_scripts import get_stealth_scripts
from crawlo.downloader.constants import (
    DEFAULT_ARGS, STEALTH_ARGS, HARMFUL_ARGS,
    WEBRTC_PROTECTION_ARGS, WEBGL_DISABLE_ARGS, CANVAS_NOISE_ARG,
    AD_DOMAINS
)
from crawlo.network.response import Response
from crawlo.logging import get_logger


# 智能等待策略常量
class WaitStrategy:
    """等待策略枚举"""
    AUTO = "auto"  # 自动检测最佳等待策略
    NETWORK_IDLE = "networkidle"  # 等待网络空闲
    DOM_READY = "domcontentloaded"  # 等待 DOM 加载完成
    ELEMENT = "element"  # 等待特定元素出现
    CUSTOM = "custom"  # 自定义等待函数


# 资源类型常量
class ResourceType:
    """资源类型枚举"""
    IMAGE = "image"
    STYLESHEET = "stylesheet"
    FONT = "font"
    MEDIA = "media"
    SCRIPT = "script"
    XHR = "xhr"
    FETCH = "fetch"
    DOCUMENT = "document"
    OTHER = "other"


class PlaywrightDownloader(DownloaderBase):
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
                status_code=status_code,
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
            self.logger.error(f"Error downloading {request.url}: {e}")
            return None
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

    # ==================== 智能等待策略 ====================

    def _get_wait_until(self, request) -> str:
        """获取导航等待策略"""
        # 请求级别的配置优先
        strategy = request.meta.get("playwright_wait_strategy", self.wait_strategy)

        if strategy == WaitStrategy.AUTO:
            # 自动模式：先使用 domcontentloaded 快速加载，后续智能等待
            return "domcontentloaded"
        elif strategy == WaitStrategy.NETWORK_IDLE:
            return "networkidle"
        elif strategy == WaitStrategy.DOM_READY:
            return "domcontentloaded"
        else:
            return "domcontentloaded"

    async def _smart_wait_for_page_load(self, page: Page, request):
        """智能等待页面加载完成"""
        strategy = request.meta.get("playwright_wait_strategy", self.wait_strategy)

        try:
            if strategy == WaitStrategy.AUTO:
                await self._auto_wait_strategy(page, request)
            elif strategy == WaitStrategy.NETWORK_IDLE:
                await page.wait_for_load_state("networkidle", timeout=self.wait_timeout)
            elif strategy == WaitStrategy.DOM_READY:
                await page.wait_for_load_state("domcontentloaded", timeout=self.wait_timeout)
            elif strategy == WaitStrategy.ELEMENT:
                element_selector = request.meta.get("playwright_wait_element", self.wait_for_element)
                if element_selector:
                    await page.wait_for_selector(element_selector, timeout=self.wait_timeout)
            elif strategy == WaitStrategy.CUSTOM:
                custom_wait = request.meta.get("playwright_custom_wait")
                if custom_wait and callable(custom_wait):
                    await custom_wait(page)

            # 如果配置了全局等待特定元素，则等待该元素出现
            if self.wait_for_element and strategy != WaitStrategy.ELEMENT:
                try:
                    await page.wait_for_selector(self.wait_for_element, timeout=self.load_timeout)
                except Exception:
                    self.logger.warning(f"Wait element '{self.wait_for_element}' not found, continuing...")

        except Exception as e:
            self.logger.warning(f"Page load wait issue: {e}, continuing with current content")

    async def _auto_wait_strategy(self, page: Page, request):
        """自动检测最佳等待策略"""
        # 1. 等待 DOM 加载完成
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=self.wait_timeout)
        except Exception:
            pass

        # 2. 检测页面是否为 SPA（单页应用）
        is_spa = await self._detect_spa(page)

        if is_spa:
            # SPA 页面：等待特定元素或网络空闲
            # 尝试检测主要内容区域
            content_selectors = [
                '[data-testid]', '[role="main"]', 'main', 'article',
                '.content', '.main-content', '#content', '#main'
            ]

            for selector in content_selectors:
                try:
                    element = page.locator(selector).first
                    if await element.count() > 0:
                        await element.wait_for(timeout=3000)
                        break
                except Exception:
                    continue

            # 额外等待网络稳定
            try:
                await page.wait_for_load_state("networkidle", timeout=5000)
            except Exception:
                pass
        else:
            # 非 SPA 页面：简单等待网络空闲
            try:
                await page.wait_for_load_state("networkidle", timeout=5000)
            except Exception:
                pass

    async def _detect_spa(self, page: Page) -> bool:
        """检测页面是否为单页应用"""
        try:
            # 检测常见的 SPA 框架标识
            spa_indicators = await page.evaluate("""
                () => {
                    const indicators = [];
                    // React
                    if (document.querySelector('[data-reactroot]') ||
                        document.querySelector('[data-reactid]') ||
                        typeof __REACT_DEVTOOLS_GLOBAL_HOOK__ !== 'undefined') {
                        indicators.push('react');
                    }
                    // Vue
                    if (document.querySelector('[data-v-]') ||
                        document.querySelector('[__vue__]') ||
                        typeof Vue !== 'undefined') {
                        indicators.push('vue');
                    }
                    // Angular
                    if (document.querySelector('[ng-app]') ||
                        document.querySelector('[ng-version]') ||
                        typeof ng !== 'undefined') {
                        indicators.push('angular');
                    }
                    // 检测是否有大量空内容（懒加载）
                    const bodyText = document.body.innerText;
                    if (bodyText.trim().length < 100) {
                        indicators.push('lazy_load');
                    }
                    return indicators.length > 0;
                }
            """)
            return spa_indicators
        except Exception:
            return False

    # ==================== 资源屏蔽 ====================

    async def _setup_resource_blocking(self, page: Page, request):
        """设置资源屏蔽"""
        # 获取请求级别的资源屏蔽配置
        block_resources = request.meta.get("playwright_block_resources", self.block_resources)
        block_ads = request.meta.get("playwright_block_ads", self.block_ads)

        if not block_resources and not block_ads:
            return

        async def route_handler(route):
            request_obj = route.request
            resource_type = request_obj.resource_type
            url = request_obj.url

            # 检查是否为广告
            if block_ads:
                parsed_url = urlparse(url)
                domain = parsed_url.netloc.lower()
                # 检查域名是否在广告黑名单中
                for ad_domain in AD_DOMAINS:
                    if ad_domain in domain:
                        await route.abort()
                        return

            # 检查资源类型是否需要屏蔽
            if resource_type in block_resources:
                await route.abort()
                return

            # 允许其他资源
            await route.continue_()

        await page.route("**/*", route_handler)

    # ==================== 反检测 ====================

    async def _inject_stealth_scripts(self, page: Page):
        """
        注入反检测脚本
        
        根据 stealth_level 注入不同级别的反检测脚本：
        - none: 不注入任何脚本
        - basic: 仅隐藏 webdriver 标识
        - advanced: 全链路指纹伪造（Canvas、WebGL、AudioContext 等）
        """
        try:
            # 如果 stealth_level 为 none，则不注入脚本
            if self.stealth_level == 'none':
                self.logger.debug("Stealth level is 'none', skipping anti-detection scripts")
                return
            
            # 获取请求级别的 stealth_level（优先级高于全局配置）
            request_stealth_level = page.request.meta.get('playwright_stealth_level', self.stealth_level) if hasattr(page, 'request') and page.request else self.stealth_level
            
            # 从 stealth_scripts 模块获取脚本
            stealth_script = get_stealth_scripts(request_stealth_level)
            
            if stealth_script:
                await page.add_init_script(stealth_script)
                self.logger.debug(f"Injected stealth scripts (level: {request_stealth_level})")
            else:
                self.logger.debug("No stealth scripts to inject (level: none)")
                
        except Exception as e:
            self.logger.warning(f"Failed to inject stealth scripts: {e}")

    # ==================== 自动滚动 ====================

    def _should_auto_scroll(self, request) -> bool:
        """判断是否需要自动滚动"""
        # 请求级别配置优先
        return request.meta.get("playwright_auto_scroll", self.auto_scroll)

    async def _scroll_to_bottom(self, page: Page, params: dict):
        """
        智能滚动到底部（适合懒加载页面）
        
        滚动策略：
        1. 渐进式滚动，每次滚动到底部后等待新内容加载
        2. 检查页面高度是否增加，判断是否有新内容
        3. 当连续多次无新内容时，认为已到达底部
        
        Args:
            page: Playwright Page 对象
            params: 参数配置
                - scroll_delay: 每次滚动后的等待延迟（毫秒），默认 500
                - max_no_content: 连续无新内容的最大次数，默认 2
        """
        scroll_delay = params.get("scroll_delay", 500)
        max_no_content = params.get("max_no_content", 2)
        
        try:
            consecutive_no_content = 0
            
            while True:
                # 获取当前页面高度
                current_height = await page.evaluate("document.body.scrollHeight")
                
                # 滚动到底部
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                
                # 等待新内容加载和渲染
                await page.wait_for_timeout(scroll_delay)
                
                # 获取滚动后的页面高度
                new_height = await page.evaluate("document.body.scrollHeight")
                
                # 检查是否有新内容加载
                if new_height > current_height:
                    # 有新内容，重置计数器
                    consecutive_no_content = 0
                    self.logger.debug(f"Scroll: {current_height} -> {new_height}px (new content loaded)")
                else:
                    # 没有新内容
                    consecutive_no_content += 1
                    self.logger.debug(f"No new content ({consecutive_no_content}/{max_no_content})")
                    
                    # 连续多次无新内容，说明到底部了
                    if consecutive_no_content >= max_no_content:
                        self.logger.debug("Reached page bottom after detecting no new content")
                        break
                
                # 安全检查：防止无限滚动
                if consecutive_no_content > 10:
                    self.logger.warning("Too many scrolls, stopping")
                    break

        except Exception as e:
            self.logger.warning(f"Scroll to bottom failed: {e}")

    async def _auto_scroll_page(self, page: Page, request):
        """
        智能滚动加载懒加载内容
        
        复用 _scroll_to_bottom 的逻辑，从 request.meta 获取参数
        """
        scroll_delay = request.meta.get("playwright_scroll_delay", self.scroll_delay)
        max_consecutive_no_content = request.meta.get("playwright_max_no_content", 2)
        
        # 转换为 params 格式，复用 _scroll_to_bottom
        params = {
            "scroll_delay": scroll_delay,
            "max_no_content": max_consecutive_no_content
        }
        
        await self._scroll_to_bottom(page, params)

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
        1. 只启动一个浏览器实例
        2. 维护一个页面池，复用标签页
        3. 控制最大并发数（max_pages_per_browser）
        4. 使用完毕后归还到池中，不关闭
        """
        if not self.context:
            raise RuntimeError("Browser context not initialized")
        
        # 如果启用了单浏览器模式
        if self.single_browser_mode:
            # 尝试从池中获取未使用的页面
            for page in self._page_pool:
                if id(page) not in self._used_pages:
                    self._used_pages.add(id(page))
                    return page
            
            # 如果池中还有空间，创建新页面
            if len(self._page_pool) < self.max_pages_per_browser:
                new_page = await self.context.new_page()
                self._page_pool.append(new_page)
                self._used_pages.add(id(new_page))
                return new_page
            
            # 如果池已满，等待其他页面释放
            self.logger.warning(f"Page pool full ({self.max_pages_per_browser}), waiting for page release...")
            for _ in range(10):  # 最多等待 10 次
                await asyncio.sleep(0.5)
                # 检查是否有页面释放
                for page in self._page_pool:
                    if id(page) not in self._used_pages:
                        self._used_pages.add(id(page))
                        return page
            # 如果等待后仍未获取到页面，创建临时页面作为后备
            self.logger.warning("Page pool wait timeout, creating temporary page")
            temp_page = await self.context.new_page()
            return temp_page
        
        # 非单浏览器模式，直接创建新页面
        return await self.context.new_page()

    async def _release_page(self, page: Page):
        """
        释放页面（归还到池中复用）
        
        策略：
        1. 如果是池中的页面，标记为未使用
        2. 导航到 about:blank 清空内容
        3. 如果是临时页面，直接关闭
        """
        page_id = id(page)
        
        # 检查是否是池中的页面
        if page_id in self._used_pages:
            self._used_pages.discard(page_id)
            # 清空页面内容，准备下次使用
            try:
                await page.goto("about:blank", timeout=1000)
            except:
                pass
        else:
            # 临时页面，直接关闭
            try:
                await page.close()
            except:
                pass