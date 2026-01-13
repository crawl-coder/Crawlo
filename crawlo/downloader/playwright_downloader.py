#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Playwright 下载器
===============
支持动态加载内容的下载器，基于 Playwright 实现。

功能特性:
- 支持 Chromium/Firefox/WebKit 浏览器引擎
- 异步非阻塞操作
- 智能等待页面加载完成
- 支持自定义浏览器上下文和选项
- 内存安全的资源管理
- 自动处理 Cookie 和本地存储
- 支持翻页操作（鼠标滑动、点击翻页）
- 单浏览器多标签页模式
"""
import time
from typing import Optional, Dict, List
from urllib.parse import urlparse

from playwright.async_api import async_playwright, Playwright, Browser, Page, BrowserContext

from crawlo.downloader import DownloaderBase
from crawlo.network.response import Response
from crawlo.logging import get_logger


class PlaywrightDownloader(DownloaderBase):
    """
    基于 Playwright 的动态内容下载器
    支持处理 JavaScript 渲染的网页内容，性能优于 Selenium
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
        self.single_browser_mode = crawler.settings.get_bool("PLAYWRIGHT_SINGLE_BROWSER_MODE", True)
        self.max_pages_per_browser = crawler.settings.get_int("PLAYWRIGHT_MAX_PAGES_PER_BROWSER", 10)
        self._page_pool: List[Page] = []
        self._used_pages: set = set()

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
            
            # 应用请求特定的设置
            await self._apply_request_settings(page, request)
            
            # 访问页面
            response = await page.goto(request.url, wait_until="networkidle")
            
            # 等待页面加载完成
            await self._wait_for_page_load(page)
            
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
            launch_kwargs = {
                "headless": self.headless
            }
            
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
            self.context = await self.browser.new_context()
            
            # 应用全局设置
            await self._apply_global_settings()
            
            self.logger.debug(f"PlaywrightDownloader initialized with {self.browser_type}")
            
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

    async def _wait_for_page_load(self, page: Page):
        """等待页面加载完成"""
        try:
            # 等待网络空闲
            await page.wait_for_load_state("networkidle")
            
            # 如果配置了等待特定元素，则等待该元素出现
            if self.wait_for_element:
                await page.wait_for_selector(self.wait_for_element, timeout=self.load_timeout)
                
        except Exception as e:
            self.logger.warning(f"Page load wait timeout, continuing with current content: {e}")

    async def _execute_custom_actions(self, page: Page, request):
        """执行自定义操作"""
        # 从请求的 meta 中获取自定义操作
        custom_actions = request.meta.get("playwright_actions", [])
        
        for action in custom_actions:
            try:
                if isinstance(action, dict):
                    action_type = action.get("type")
                    action_params = action.get("params", {})
                    
                    if action_type == "click":
                        selector = action_params.get("selector")
                        if selector:
                            await page.click(selector)
                    elif action_type == "fill":
                        selector = action_params.get("selector")
                        value = action_params.get("value")
                        if selector and value is not None:
                            await page.fill(selector, value)
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
                            
            except Exception as e:
                self.logger.warning(f"Failed to execute custom action: {e}")

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
            # 关闭所有页面
            if self._page_pool:
                self.logger.debug(f"Closing {len(self._page_pool)} page(s)...")
                for page in self._page_pool:
                    try:
                        await page.close()
                    except Exception as e:
                        self.logger.warning(f"Error closing page: {e}")
                
                self._page_pool.clear()
                self._used_pages.clear()
            
            # 关闭上下文
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
        """获取页面实例（支持单浏览器多标签页模式）"""
        # 如果启用了单浏览器模式且页面池中有可用页面
        if self.single_browser_mode and self._page_pool:
            # 检查是否需要创建新页面
            if len(self._page_pool) < self.max_pages_per_browser:
                # 创建新页面
                if not self.context:
                    raise RuntimeError("Browser context not initialized")
                new_page = await self.context.new_page()
                self._page_pool.append(new_page)
                self._used_pages.add(id(new_page))
                return new_page
            
            # 尝试从池中获取未使用的页面
            for page in self._page_pool:
                if id(page) not in self._used_pages:
                    self._used_pages.add(id(page))
                    return page
        
        # 创建新页面
        if not self.context:
            raise RuntimeError("Browser context not initialized")
            
        page = await self.context.new_page()
        
        # 如果启用了单浏览器模式，将页面添加到池中
        if self.single_browser_mode:
            self._page_pool.append(page)
            self._used_pages.add(id(page))
            
            # 如果超过最大页面数，移除最早的页面
            if len(self._page_pool) > self.max_pages_per_browser:
                old_page = self._page_pool.pop(0)
                self._used_pages.discard(id(old_page))
                try:
                    await old_page.close()
                except:
                    pass
        
        return page

    async def _release_page(self, page: Page):
        """归还页面到池中"""
        if self.single_browser_mode:
            page_id = id(page)
            if page_id in self._used_pages:
                self._used_pages.discard(page_id)
                # 清空页面内容，准备下次使用
                try:
                    await page.goto("about:blank")
                except:
                    pass
        else:
            # 非单浏览器模式，直接关闭页面
            try:
                await page.close()
            except:
                pass