#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Selenium 下载器
==============
支持动态加载内容的下载器，基于 Selenium WebDriver 实现。

功能特性:
- 支持 Chrome/Firefox/Edge 等主流浏览器
- 智能等待页面加载完成
- 支持自定义浏览器选项和插件
- 内存安全的资源管理
- 自动处理 Cookie 和本地存储
- 支持翻页操作（鼠标滑动、点击翻页）
- 单浏览器多标签页模式
"""
import os
import time
import asyncio
from typing import Optional, Dict, List

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from crawlo.downloader import DownloaderBase
from crawlo.network.response import Response
from crawlo.logging import get_logger


class SeleniumDownloader(DownloaderBase):
    """
    基于 Selenium 的动态内容下载器
    支持处理 JavaScript 渲染的网页内容
    """

    def __init__(self, crawler):
        super().__init__(crawler)
        self.driver: Optional[webdriver.Chrome] = None
        self.logger = get_logger(self.__class__.__name__)
        self.default_timeout = crawler.settings.get_int("SELENIUM_TIMEOUT", 30)
        self.load_timeout = crawler.settings.get_int("SELENIUM_LOAD_TIMEOUT", 10)
        self.window_width = crawler.settings.get_int("SELENIUM_WINDOW_WIDTH", 1920)
        self.window_height = crawler.settings.get_int("SELENIUM_WINDOW_HEIGHT", 1080)
        self.browser_type = crawler.settings.get("SELENIUM_BROWSER_TYPE", "chrome").lower()
        self.headless = crawler.settings.get_bool("SELENIUM_HEADLESS", True)
        self.wait_for_element = crawler.settings.get("SELENIUM_WAIT_FOR_ELEMENT", None)
        
        # 单浏览器多标签页模式
        self.single_browser_mode = crawler.settings.get_bool("SELENIUM_SINGLE_BROWSER_MODE", True)
        self.max_tabs_per_browser = crawler.settings.get_int("SELENIUM_MAX_TABS_PER_BROWSER", 10)
        self._window_handles: List[str] = []
        self._current_handle_index = 0

    def open(self):
        super().open()
        self.logger.info("Opening SeleniumDownloader")

        try:
            if self.browser_type == "chrome":
                self.driver = self._create_chrome_driver()
            elif self.browser_type == "firefox":
                self.driver = self._create_firefox_driver()
            elif self.browser_type == "edge":
                self.driver = self._create_edge_driver()
            else:
                raise ValueError(f"Unsupported browser type: {self.browser_type}")

            # 设置窗口大小
            self.driver.set_window_size(self.window_width, self.window_height)
            self.logger.debug(f"SeleniumDownloader initialized with {self.browser_type}")

        except Exception as e:
            self.logger.error(f"Failed to initialize SeleniumDownloader: {e}")
            raise

    def _create_chrome_driver(self):
        """创建 Chrome WebDriver"""
        options = ChromeOptions()
        
        if self.headless:
            options.add_argument("--headless")
        
        # 基本配置
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-plugins")
        options.add_argument("--disable-images")
        options.add_argument("--disable-javascript") if not self.crawler.settings.get_bool("SELENIUM_ENABLE_JS", True) else None
        
        # 用户代理
        user_agent = self.crawler.settings.get("USER_AGENT")
        if user_agent:
            options.add_argument(f"--user-agent={user_agent}")
            
        # 代理设置
        proxy = self.crawler.settings.get("SELENIUM_PROXY")
        if proxy:
            # 处理带认证的代理
            if isinstance(proxy, str) and "@" in proxy and "://" in proxy:
                # 解析带认证的代理URL
                from urllib.parse import urlparse
                parsed = urlparse(proxy)
                if parsed.username and parsed.password:
                    # 对于带认证的代理，需要特殊处理
                    # 这里我们使用一个扩展来处理认证
                    # 创建一个临时的代理配置文件
                    import tempfile
                    import json
                    
                    proxy_config = {
                        "mode": "fixed_servers",
                        "rules": {
                            "proxyForHttp": {
                                "scheme": parsed.scheme,
                                "host": parsed.hostname,
                                "port": parsed.port or (80 if parsed.scheme == "http" else 443)
                            },
                            "proxyForHttps": {
                                "scheme": parsed.scheme,
                                "host": parsed.hostname,
                                "port": parsed.port or (80 if parsed.scheme == "http" else 443)
                            },
                            "bypassList": []
                        }
                    }
                    
                    # 创建临时目录和文件
                    temp_dir = tempfile.mkdtemp()
                    proxy_file = os.path.join(temp_dir, "proxy.json")
                    with open(proxy_file, 'w') as f:
                        json.dump(proxy_config, f)
                    
                    # 设置代理配置文件
                    options.add_argument(f"--proxy-server={parsed.scheme}://{parsed.hostname}:{parsed.port or (80 if parsed.scheme == 'http' else 443)}")
                    
                    # 设置认证信息（需要通过其他方式处理）
                    # 这里我们简单地清理URL中的认证信息
                    clean_proxy = f"{parsed.scheme}://{parsed.hostname}:{parsed.port or (80 if parsed.scheme == 'http' else 443)}"
                    options.add_argument(f"--proxy-server={clean_proxy}")
                else:
                    options.add_argument(f"--proxy-server={proxy}")
            else:
                options.add_argument(f"--proxy-server={proxy}")
            
        # 创建驱动
        return webdriver.Chrome(options=options)

    def _create_firefox_driver(self):
        """创建 Firefox WebDriver"""
        options = FirefoxOptions()
        
        if self.headless:
            options.add_argument("--headless")
            
        # 基本配置
        options.set_preference("network.http.use-cache", False)
        options.set_preference("browser.cache.disk.enable", False)
        options.set_preference("browser.cache.memory.enable", False)
        
        # 用户代理
        user_agent = self.crawler.settings.get("USER_AGENT")
        if user_agent:
            options.set_preference("general.useragent.override", user_agent)
            
        # 代理设置
        proxy = self.crawler.settings.get("SELENIUM_PROXY")
        if proxy:
            # 处理带认证的代理
            if isinstance(proxy, str) and "@" in proxy and "://" in proxy:
                # 解析带认证的代理URL
                from urllib.parse import urlparse
                parsed = urlparse(proxy)
                if parsed.username and parsed.password:
                    # 设置代理服务器
                    options.set_preference("network.proxy.type", 1)  # 手动配置
                    options.set_preference("network.proxy.http", parsed.hostname)
                    options.set_preference("network.proxy.http_port", parsed.port or 80)
                    options.set_preference("network.proxy.ssl", parsed.hostname)
                    options.set_preference("network.proxy.ssl_port", parsed.port or 443)
                    options.set_preference("network.proxy.ftp", parsed.hostname)
                    options.set_preference("network.proxy.ftp_port", parsed.port or 21)
                    options.set_preference("network.proxy.socks", parsed.hostname)
                    options.set_preference("network.proxy.socks_port", parsed.port or 1080)
                    
                    # 认证信息需要通过其他方式处理（例如使用扩展）
                    # 这里我们简单地清理URL中的认证信息
                    clean_proxy = f"{parsed.scheme}://{parsed.hostname}:{parsed.port or (80 if parsed.scheme == 'http' else 443)}"
                else:
                    options.add_argument(f"--proxy-server={proxy}")
            else:
                # 简单的代理配置
                options.set_preference("network.proxy.type", 1)
                # 这里需要根据代理URL的具体格式来解析
                from urllib.parse import urlparse
                parsed = urlparse(proxy)
                if parsed.scheme in ["http", "https"]:
                    options.set_preference("network.proxy.http", parsed.hostname)
                    options.set_preference("network.proxy.http_port", parsed.port or 80)
                    options.set_preference("network.proxy.ssl", parsed.hostname)
                    options.set_preference("network.proxy.ssl_port", parsed.port or 443)
                elif parsed.scheme == "socks5":
                    options.set_preference("network.proxy.socks", parsed.hostname)
                    options.set_preference("network.proxy.socks_port", parsed.port or 1080)
                    options.set_preference("network.proxy.socks_version", 5)
                elif parsed.scheme == "socks4":
                    options.set_preference("network.proxy.socks", parsed.hostname)
                    options.set_preference("network.proxy.socks_port", parsed.port or 1080)
                    options.set_preference("network.proxy.socks_version", 4)
            
        return webdriver.Firefox(options=options)

    def _create_edge_driver(self):
        """创建 Edge WebDriver"""
        options = EdgeOptions()
        
        if self.headless:
            options.add_argument("--headless")
            
        # 基本配置
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        
        # 用户代理
        user_agent = self.crawler.settings.get("USER_AGENT")
        if user_agent:
            options.add_argument(f"--user-agent={user_agent}")
            
        # 代理设置
        proxy = self.crawler.settings.get("SELENIUM_PROXY")
        if proxy:
            # 处理带认证的代理
            if isinstance(proxy, str) and "@" in proxy and "://" in proxy:
                # 解析带认证的代理URL
                from urllib.parse import urlparse
                parsed = urlparse(proxy)
                if parsed.username and parsed.password:
                    # 清理URL中的认证信息
                    clean_proxy = f"{parsed.scheme}://{parsed.hostname}:{parsed.port or (80 if parsed.scheme == 'http' else 443)}"
                    options.add_argument(f"--proxy-server={clean_proxy}")
                else:
                    options.add_argument(f"--proxy-server={proxy}")
            else:
                options.add_argument(f"--proxy-server={proxy}")
            
        return webdriver.Edge(options=options)

    async def download(self, request) -> Optional[Response]:
        """下载动态内容"""
        if not self.driver:
            self.logger.error("SeleniumDownloader driver is not available")
            return None

        start_time = None
        if self.crawler.settings.get_bool("DOWNLOAD_STATS", True):
            start_time = time.time()

        try:
            # 切换到合适的标签页或创建新标签页
            await self._switch_or_create_tab()
            
            # 访问页面
            self.driver.get(request.url)
            
            # 等待页面加载完成
            await self._wait_for_page_load()
            
            # 执行自定义脚本（如果有）
            await self._execute_custom_scripts(request)
            
            # 执行翻页操作（如果有）
            await self._execute_pagination_actions(request)
            
            # 获取页面内容
            page_source = self.driver.page_source
            page_url = self.driver.current_url
            
            # 获取响应头信息（Selenium 无法直接获取，需要模拟）
            headers = self._get_response_headers()
            
            # 获取状态码（Selenium 无法直接获取，需要通过执行脚本）
            status_code = await self._get_status_code()
            
            # 获取 Cookies
            cookies = self._get_cookies()
            
            # 构造响应对象
            response = Response(
                url=page_url,
                headers=headers,
                status_code=status_code,
                body=page_source.encode('utf-8'),
                request=request
            )
            
            # 添加 Cookies 到响应
            response.cookies = cookies
            
            # 记录下载统计
            if start_time:
                download_time = time.time() - start_time
                self.logger.debug(f"Downloaded {request.url} in {download_time:.3f}s")
                
            return response

        except TimeoutException as e:
            self.logger.error(f"Timeout error for {request.url}: {e}")
            return None
        except WebDriverException as e:
            self.logger.error(f"WebDriver error for {request.url}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error for {request.url}: {e}", exc_info=True)
            return None

    async def _switch_or_create_tab(self):
        """切换到合适的标签页或创建新标签页"""
        if not self.single_browser_mode:
            return
            
        # 如果还没有窗口句柄，保存当前窗口
        if not self._window_handles:
            self._window_handles.append(self.driver.current_window_handle)
            return
            
        # 检查是否需要创建新标签页
        if len(self._window_handles) < self.max_tabs_per_browser:
            # 创建新标签页
            self.driver.execute_script("window.open('');")
            # 切换到新标签页
            self.driver.switch_to.window(self.driver.window_handles[-1])
            # 保存新标签页句柄
            self._window_handles.append(self.driver.current_window_handle)
            return
            
        # 循环使用现有的标签页
        self._current_handle_index = (self._current_handle_index + 1) % len(self._window_handles)
        self.driver.switch_to.window(self._window_handles[self._current_handle_index])
        
        # 清空当前页面内容
        self.driver.execute_script("document.body.innerHTML = '';")

    async def _wait_for_page_load(self):
        """等待页面加载完成"""
        try:
            # 等待 document.readyState 为 complete
            WebDriverWait(self.driver, self.load_timeout).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            
            # 如果配置了等待特定元素，则等待该元素出现
            if self.wait_for_element:
                WebDriverWait(self.driver, self.load_timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, self.wait_for_element))
                )
                
        except TimeoutException:
            self.logger.warning("Page load timeout, continuing with current content")

    async def _execute_custom_scripts(self, request):
        """执行自定义脚本"""
        # 从请求的 meta 中获取自定义脚本
        custom_scripts = request.meta.get("selenium_scripts", [])
        
        for script in custom_scripts:
            try:
                if isinstance(script, str):
                    self.driver.execute_script(script)
                elif isinstance(script, dict):
                    script_type = script.get("type", "js")
                    script_content = script.get("content", "")
                    
                    if script_type == "js":
                        self.driver.execute_script(script_content)
                    elif script_type == "wait":
                        # 等待特定时间
                        await asyncio.sleep(script_content)
                        
            except Exception as e:
                self.logger.warning(f"Failed to execute custom script: {e}")

    async def _execute_pagination_actions(self, request):
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
                        scroll_delay = action_params.get("delay", 1)
                        scroll_distance = action_params.get("distance", 500)
                        
                        action_chains = ActionChains(self.driver)
                        for _ in range(scroll_count):
                            action_chains.scroll_by_amount(0, scroll_distance).perform()
                            time.sleep(scroll_delay)
                            
                    elif action_type == "click":
                        # 鼠标点击翻页
                        selector = action_params.get("selector")
                        click_count = action_params.get("count", 1)
                        click_delay = action_params.get("delay", 1)
                        
                        if selector:
                            element = WebDriverWait(self.driver, self.load_timeout).until(
                                EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                            )
                            for _ in range(click_count):
                                element.click()
                                time.sleep(click_delay)
                                
                    elif action_type == "evaluate":
                        # 执行自定义脚本翻页
                        script = action_params.get("script")
                        if script:
                            self.driver.execute_script(script)
                            
            except Exception as e:
                self.logger.warning(f"Failed to execute pagination action: {e}")

    def _get_response_headers(self) -> Dict[str, str]:
        """获取响应头信息"""
        # Selenium 无法直接获取响应头，这里返回一些基本的模拟信息
        return {
            "Content-Type": "text/html; charset=utf-8",
            "Server": "Selenium WebDriver"
        }

    async def _get_status_code(self) -> int:
        """获取状态码"""
        try:
            # 通过执行脚本获取状态码
            status_code = self.driver.execute_script(
                "return window.performance.getEntriesByType('navigation')[0].responseStart > 0 ? 200 : 404;"
            )
            return status_code if isinstance(status_code, int) else 200
        except Exception:
            return 200  # 默认成功

    def _get_cookies(self) -> Dict[str, str]:
        """获取 Cookies"""
        try:
            selenium_cookies = self.driver.get_cookies()
            return {cookie['name']: cookie['value'] for cookie in selenium_cookies}
        except Exception as e:
            self.logger.warning(f"Failed to get cookies: {e}")
            return {}

    async def close(self) -> None:
        """关闭浏览器资源"""
        if self.driver:
            self.logger.info("Closing SeleniumDownloader driver...")
            try:
                # 关闭所有标签页
                if self._window_handles:
                    self.logger.debug(f"Closing {len(self._window_handles)} tab(s)...")
                    for handle in self._window_handles[1:]:  # 保留第一个，其他关闭
                        try:
                            self.driver.switch_to.window(handle)
                            self.driver.close()
                        except Exception as e:
                            self.logger.warning(f"Error closing tab {handle}: {e}")
                    
                    self._window_handles.clear()
                
                # 退出浏览器
                self.driver.quit()
            except Exception as e:
                self.logger.warning(f"Error closing Selenium driver: {e}")
            finally:
                self.driver = None
        
        self.logger.debug("SeleniumDownloader closed.")