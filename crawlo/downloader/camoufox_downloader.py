#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Camoufox 下载器
================
基于 Camoufox 的隐身浏览器下载器。

Camoufox 特性:
- 基于 Firefox 的隐身浏览器
- 全链路指纹伪造（Canvas、WebGL、AudioContext 等）
- 内置 Cloudflare Turnstile 自动解决
- 比普通浏览器更强的反检测能力

依赖安装:
pip install camoufox
playwright install  # 如果需要 Chromium 兼容模式

使用示例:
# settings.py
DOWNLOADER = "crawlo.downloader.CamoufoxDownloader"
CAMOUFOX_HEADLESS = True
CAMOUFOX_HUMANIZE = True
CAMOUFOX_SOLVE_CLOUDFLARE = True
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
from crawlo.constants import (
    BROWSER_PAGE_GOTO_BLANK_TIMEOUT_MS,
    BROWSER_ELEMENT_WAIT_TIMEOUT_MS,
    BROWSER_NETWORK_IDLE_TIMEOUT_MS,
)
from crawlo.utils.misc import (
    get_browser_config,
    get_browser_config_int,
    get_browser_config_bool,
    get_browser_config_list,
)


class CamoufoxDownloader(DownloaderBase):
    """
    基于 Camoufox 的隐身浏览器下载器

    Camoufox 是一个专门为反爬虫设计的 Firefox 变体，
    内置了全链路指纹伪造和 Cloudflare 绕过能力。

    相比 Playwright:
    - 更强的反检测能力（无需额外注入脚本）
    - 内置 Cloudflare Turnstile 自动解决
    - 更真实的浏览器指纹

    代理切换策略：
    Camoufox 不支持 Context 级代理，代理变化时需要重启整个浏览器实例。

    使用场景:
    - 高强度反爬网站（Cloudflare、PerimeterX 等）
    - 需要真实浏览器指纹的场景
    - Playwright/DrissionPage 被检测的场景
    """

    def __init__(self, crawler):
        super().__init__(crawler)
        self.logger = get_logger(self.__class__.__name__)

        # Camoufox 实例
        self._browser = None
        self._context = None
        self._page_pool: List = []
        self._used_pages: set = set()
        self._init_lock = asyncio.Lock()  # 浏览器初始化锁，防止并发重复初始化

        # 当前浏览器使用的代理（用于检测代理变化，触发浏览器重启）
        self._current_proxy = None
        
        s = crawler.settings
        # === 浏览器通用配置（三级回退：CAMOUFOX_* → BROWSER_* → 默认值）===
        self.headless = get_browser_config_bool(s, "CAMOUFOX", "HEADLESS", True)
        self.proxy = get_browser_config(s, "CAMOUFOX", "PROXY", None)
        self.humanize = get_browser_config_bool(s, "CAMOUFOX", "HUMANIZE", True)
        self.block_resources: Set[str] = set(
            get_browser_config_list(s, "CAMOUFOX", "BLOCK_RESOURCES", ["image", "font", "media"])
        )
        self.timeout = get_browser_config_int(s, "CAMOUFOX", "TIMEOUT", 30000)
        self.load_timeout = get_browser_config_int(s, "CAMOUFOX", "LOAD_TIMEOUT", 10000)
        self.viewport_width = get_browser_config_int(s, "CAMOUFOX", "VIEWPORT_WIDTH", 1280)
        self.viewport_height = get_browser_config_int(s, "CAMOUFOX", "VIEWPORT_HEIGHT", 720)
        self.max_pages = get_browser_config_int(s, "CAMOUFOX", "MAX_PAGES", 10)
        self.auto_scroll = get_browser_config_bool(s, "CAMOUFOX", "AUTO_SCROLL", False)
        self.scroll_delay = get_browser_config_int(s, "CAMOUFOX", "SCROLL_DELAY", 500)
        self.wait_strategy = get_browser_config(s, "CAMOUFOX", "WAIT_STRATEGY", "auto")
        self.wait_timeout = get_browser_config_int(s, "CAMOUFOX", "WAIT_TIMEOUT", 10000)
        self.wait_for_element = get_browser_config(s, "CAMOUFOX", "WAIT_FOR_ELEMENT", None)

        # === Camoufox 特有配置 ===
        self.solve_cloudflare = s.get_bool("CAMOUFOX_SOLVE_CLOUDFLARE", True)

    def open(self):
        """初始化 Camoufox 下载器（懒加载，首次 download 时才启动浏览器）"""
        super().open()
        self.logger.info("Opening CamoufoxDownloader (lazy initialization)")

    async def _initialize_browser(self, proxy=None):
        """初始化 Camoufox 浏览器

        Args:
            proxy: 代理配置，None 表示直连
        """
        try:
            from camoufox import Camoufox
        except ImportError:
            raise ImportError(
                "Camoufox is not installed. Please install it with: pip install camoufox"
            )

        # Configure browser startup parameters
        config = {
            "headless": self.headless,
            "humanize": self.humanize,
            "os": platform.system().lower() or "windows",
        }

        # 代理配置
        effective_proxy = proxy or self.proxy
        if effective_proxy:
            if isinstance(effective_proxy, str):
                config["proxy"] = {"server": effective_proxy}
            elif isinstance(effective_proxy, dict):
                config["proxy"] = effective_proxy

        # Cloudflare 绕过配置
        if self.solve_cloudflare:
            config["solve_cloudflare"] = True

        # 启动浏览器
        self._browser = Camoufox(**config)
        self._context = self._browser
        self._current_proxy = effective_proxy

        self.logger.info(
            f"CamoufoxDownloader initialized "
            f"(headless={self.headless}, proxy={effective_proxy or 'direct'})"
        )

    async def _check_proxy_change(self, request):
        """检测代理变化，必要时重启浏览器

        Camoufox 不支持 Context 级代理，代理变化时需要重启整个浏览器实例。

        代理切换触发条件：
        - request.proxy 有值且与当前浏览器代理不同 → 切换到新代理
        - request.meta['proxy_downgraded'] 为 True → 降级为直连

        注意：request.proxy 为 None 且无 proxy_downgraded 标记时，
        视为"未指定代理"，保持当前浏览器不变（兼容无 ProxyMiddleware 的场景）。
        """
        request_proxy = getattr(request, 'proxy', None)
        proxy_downgraded = request.meta.get('proxy_downgraded', False)

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
                f"restarting Camoufox browser..."
            )
            await self._restart_browser(target_proxy)

    async def _restart_browser(self, new_proxy=None):
        """重启 Camoufox 浏览器

        Args:
            new_proxy: 新代理配置，None 表示直连
        """
        # 1. 关闭旧浏览器
        await self.close()

        # 2. 用新代理启动浏览器
        await self._initialize_browser(proxy=new_proxy)

    async def download(self, request) -> Optional[Response]:
        """下载动态内容"""
        # 懒加载初始化（加锁防止并发重复初始化）
        if not self._browser or not self._context:
            async with self._init_lock:
                # double-check：获取锁后再次确认
                if not self._browser or not self._context:
                    try:
                        await self._initialize_browser()
                    except Exception as e:
                        self.logger.error(f"Failed to initialize Camoufox for {request.url}: {e}")
                        return None

        # 检测代理变化：如果 request.proxy 与当前浏览器的代理不同，重启浏览器
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
                "height": self.viewport_height
            })
            
            # 设置资源屏蔽
            await self._setup_resource_blocking(page, request)
            
            # 应用请求设置
            await self._apply_request_settings(page, request)
            
            # 访问页面
            wait_until = self._get_wait_until(request)
            response = await page.goto(request.url, wait_until=wait_until)
            
            # 智能等待
            await self._smart_wait_for_page_load(page, request)
            
            # 自动滚动
            if self._should_auto_scroll(request):
                await self._auto_scroll_page(page, request)
            
            # 执行自定义操作
            await self._execute_custom_actions(page, request)
            
            # 执行翻页操作
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
            crawlo_response.cookies = cookies
            
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
            if page:
                await self._release_page(page)

    async def _get_page(self):
        """获取页面实例"""
        # 尝试从池中获取未使用的页面
        for page in self._page_pool:
            if id(page) not in self._used_pages:
                self._used_pages.add(id(page))
                return page
        
        # 如果池中还有空间，创建新页面
        if len(self._page_pool) < self.max_pages:
            new_page = await self._context.new_page()
            self._page_pool.append(new_page)
            self._used_pages.add(id(new_page))
            return new_page
        
        # 如果池已满，创建临时页面
        self.logger.warning(f"Page pool full ({self.max_pages}), creating temporary page")
        temp_page = await self._context.new_page()
        return temp_page

    async def _release_page(self, page):
        """释放页面"""
        page_id = id(page)
        
        if page_id in self._used_pages:
            self._used_pages.discard(page_id)
            try:
                await page.goto("about:blank", timeout=BROWSER_PAGE_GOTO_BLANK_TIMEOUT_MS)
            except:
                pass
        else:
            try:
                await page.close()
            except:
                pass

    def _get_wait_until(self, request) -> str:
        """获取导航等待策略"""
        strategy = request.meta.get("camoufox_wait_strategy", self.wait_strategy)
        
        if strategy == "auto":
            return "domcontentloaded"
        elif strategy == "networkidle":
            return "networkidle"
        else:
            return "domcontentloaded"

    async def _smart_wait_for_page_load(self, page, request):
        """智能等待页面加载"""
        strategy = request.meta.get("camoufox_wait_strategy", self.wait_strategy)
        
        try:
            if strategy == "auto":
                await self._auto_wait_strategy(page, request)
            elif strategy == "networkidle":
                await page.wait_for_load_state("networkidle", timeout=self.wait_timeout)
            elif strategy == "domcontentloaded":
                await page.wait_for_load_state("domcontentloaded", timeout=self.wait_timeout)
            elif strategy == "element":
                element_selector = request.meta.get("camoufox_wait_element", self.wait_for_element)
                if element_selector:
                    await page.wait_for_selector(element_selector, timeout=self.wait_timeout)
            
            # 如果配置了全局等待元素
            if self.wait_for_element and strategy != "element":
                try:
                    await page.wait_for_selector(self.wait_for_element, timeout=self.load_timeout)
                except Exception:
                    self.logger.warning(f"Wait element '{self.wait_for_element}' not found")
                    
        except Exception as e:
            self.logger.warning(f"Page load wait issue: {e}")

    async def _auto_wait_strategy(self, page, request):
        """自动检测最佳等待策略"""
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=self.wait_timeout)
        except Exception:
            pass
        
        # 等待主要内容区域
        content_selectors = [
            '[data-testid]', '[role="main"]', 'main', 'article',
            '.content', '.main-content', '#content', '#main'
        ]
        
        for selector in content_selectors:
            try:
                element = page.locator(selector).first
                if await element.count() > 0:
                    await element.wait_for(timeout=BROWSER_ELEMENT_WAIT_TIMEOUT_MS)
                    break
            except Exception:
                continue
        
        # 额外等待网络稳定
        try:
            await page.wait_for_load_state("networkidle", timeout=BROWSER_NETWORK_IDLE_TIMEOUT_MS)
        except Exception:
            pass

    async def _setup_resource_blocking(self, page, request):
        """设置资源屏蔽"""
        block_resources = request.meta.get("camoufox_block_resources", self.block_resources)
        
        if not block_resources:
            return
        
        async def route_handler(route):
            resource_type = route.request.resource_type
            
            if resource_type in block_resources:
                await route.abort()
            else:
                await route.continue_()
        
        await page.route("**/*", route_handler)

    async def _apply_request_settings(self, page, request):
        """应用请求特定设置"""
        if request.headers:
            await page.set_extra_http_headers(request.headers)
        
        if request.cookies:
            cookies = []
            for name, value in request.cookies.items():
                parsed_url = urlparse(request.url)
                cookies.append({
                    "name": name,
                    "value": value,
                    "domain": parsed_url.netloc,
                    "path": "/"
                })
            await page.context.add_cookies(cookies)

    def _should_auto_scroll(self, request) -> bool:
        """判断是否需要自动滚动"""
        return request.meta.get("camoufox_auto_scroll", self.auto_scroll)

    async def _auto_scroll_page(self, page, request):
        """自动滚动页面"""
        scroll_delay = request.meta.get("camoufox_scroll_delay", self.scroll_delay)
        max_no_content = request.meta.get("camoufox_max_no_content", 2)
        
        try:
            consecutive_no_content = 0
            
            while True:
                current_height = await page.evaluate("document.body.scrollHeight")
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(scroll_delay)
                new_height = await page.evaluate("document.body.scrollHeight")
                
                if new_height > current_height:
                    consecutive_no_content = 0
                else:
                    consecutive_no_content += 1
                    if consecutive_no_content >= max_no_content:
                        break
                
                if consecutive_no_content > 10:
                    break
                    
        except Exception as e:
            self.logger.warning(f"Auto scroll failed: {e}")

    async def _execute_custom_actions(self, page, request):
        """执行自定义操作"""
        custom_actions = PageActionHandler.get_actions_from_request(request)
        
        for i, action in enumerate(custom_actions, 1):
            try:
                if isinstance(action, dict):
                    action_type = action.get("type")
                    action_params = action.get("params", {})
                    
                    if action_type == "click":
                        selector = PageActionHandler.extract_selector(action)
                        if selector:
                            await self._click_with_selector(page, selector)
                    elif action_type == "fill":
                        selector = PageActionHandler.extract_selector(action)
                        value = action_params.get("value")
                        if selector and value is not None:
                            await self._fill_with_selector(page, selector, value)
                    elif action_type == "wait":
                        timeout = action_params.get("timeout", 1000)
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
                    elif action_type == "click_in_frame":
                        # 跨 iframe 点击（解决跨域 iframe 内元素无法被 page.click 访问的问题）
                        frame_selector = action_params.get("frame", "")
                        selector = action_params.get("selector", "")
                        if frame_selector and selector:
                            target = page.frame(name=frame_selector) or page.frame(url=frame_selector)
                            if target:
                                await target.click(selector)
                            else:
                                self.logger.warning(f"Frame not found: {frame_selector}")
                            
            except Exception as e:
                self.logger.warning(f"Failed to execute action {i}: {e}")

    async def _click_with_selector(self, page, selector: str):
        """智能点击"""
        selector_type, clean_selector = SelectorConverter.normalize_selector(selector)
        
        if selector_type == "xpath":
            element = page.locator(f"xpath={clean_selector}")
            await element.click()
        else:
            await page.click(clean_selector)

    async def _fill_with_selector(self, page, selector: str, value: str):
        """智能填充"""
        selector_type, clean_selector = SelectorConverter.normalize_selector(selector)
        
        if selector_type == "xpath":
            element = page.locator(f"xpath={clean_selector}")
            await element.fill(value)
        else:
            await page.fill(clean_selector, value)

    async def _execute_pagination_actions(self, page, request):
        """执行翻页操作"""
        pagination_actions = request.meta.get("pagination_actions", [])
        
        for action in pagination_actions:
            try:
                if isinstance(action, dict):
                    action_type = action.get("type")
                    params = action.get("params", {})
                    
                    if action_type == "scroll":
                        scroll_count = params.get("count", 1)
                        scroll_delay = params.get("delay", 1000)
                        scroll_distance = params.get("distance", 500)
                        
                        for _ in range(scroll_count):
                            await page.mouse.wheel(0, scroll_distance)
                            await page.wait_for_timeout(scroll_delay)
                            
                    elif action_type == "click":
                        selector = params.get("selector")
                        if selector:
                            await page.click(selector)
                            await page.wait_for_timeout(params.get("delay", 1000))
                            
                    elif action_type == "evaluate":
                        script = params.get("script")
                        if script:
                            await page.evaluate(script)
                            
            except Exception as e:
                self.logger.warning(f"Failed to execute pagination action: {e}")

    async def _get_cookies(self) -> Dict[str, str]:
        """获取 Cookies"""
        try:
            if self._context:
                cookies = await self._context.cookies()
                return {cookie['name']: cookie['value'] for cookie in cookies}
            return {}
        except Exception as e:
            self.logger.warning(f"Failed to get cookies: {e}")
            return {}

    async def close(self) -> None:
        """关闭浏览器资源"""
        self.logger.info("Closing CamoufoxDownloader...")
        
        # 关闭页面池
        for page in self._page_pool:
            try:
                await page.close()
            except Exception as e:
                self.logger.debug(f"Error closing page: {e}")
        
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
        
        # 关闭浏览器
        if self._browser:
            try:
                # Camoufox 可能没有 close 方法，使用 __exit__
                if hasattr(self._browser, 'close'):
                    await self._browser.close()
                elif hasattr(self._browser, '__exit__'):
                    self._browser.__exit__(None, None, None)
            except Exception as e:
                self.logger.debug(f"Error closing browser: {e}")
            finally:
                self._browser = None
                self._context = None
                self._current_proxy = None

        self.logger.info("CamoufoxDownloader closed successfully")
