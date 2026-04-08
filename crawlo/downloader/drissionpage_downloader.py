#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
DrissionPage 下载器
===================
基于 DrissionPage 的动态内容下载器。

功能特性:
- 支持 Chrome/Edge 浏览器
- 内置智能等待机制
- 元素自动等待加载
- 内存安全的资源管理
- 单浏览器多标签页模式
- 异步非阻塞操作（通过 asyncio.to_thread）
"""

import asyncio
import os
import signal
import subprocess
import time
from typing import Optional, Dict, List

from DrissionPage import ChromiumPage, ChromiumOptions

from crawlo.downloader import DownloaderBase
from crawlo.downloader.page_action_handler import PageActionHandler, SelectorConverter
from crawlo.downloader.stealth_scripts import get_drissionpage_stealth_script
from crawlo.network.response import Response
from crawlo.logging import get_logger


class DrissionPageDownloader(DownloaderBase):
    """
    基于 DrissionPage 的动态内容下载器
    支持处理 JavaScript 渲染的网页内容

    增强功能:
    - 智能等待策略：自动检测页面特征，选择最佳等待方式
    - 资源屏蔽：屏蔽图片/CSS/字体等，大幅提升加载速度
    - 自动滚动：滚动加载懒加载内容
    - 翻页操作：支持多种翻页方式（滚动、点击、JS）
    """

    def __init__(self, crawler):
        super().__init__(crawler)
        self.logger = get_logger(self.__class__.__name__)
        self.page: Optional[ChromiumPage] = None
        
        # 配置参数
        self.timeout = crawler.settings.get_int("DRISSIONPAGE_TIMEOUT", 30)
        self.headless = crawler.settings.get_bool("DRISSIONPAGE_HEADLESS", True)
        self.browser_path = crawler.settings.get("DRISSIONPAGE_BROWSER_PATH", None)
        self.user_data_path = crawler.settings.get("DRISSIONPAGE_USER_DATA_PATH", None)
        self.proxy = crawler.settings.get("DRISSIONPAGE_PROXY", None)
        
        # 等待策略
        self.load_images = crawler.settings.get_bool("DRISSIONPAGE_LOAD_IMAGES", True)
        
        # 滚动配置
        self.auto_scroll = crawler.settings.get_bool("DRISSIONPAGE_AUTO_SCROLL", False)
        self.scroll_delay = crawler.settings.get_int("DRISSIONPAGE_SCROLL_DELAY", 1)
        
        # 标签页管理
        self._tabs: List[ChromiumPage] = []
        self._used_pages: set = set()
        self.max_pages = crawler.settings.get_int("DRISSIONPAGE_MAX_PAGES", 10)
        
        # 反检测配置
        self.stealth_level = crawler.settings.get("DRISSIONPAGE_STEALTH_LEVEL", "basic")

    @staticmethod
    def _cleanup_orphan_processes():
        """清理可能残留的浏览器进程"""
        try:
            if os.name == 'nt':  # Windows
                # 查找 Chrome 或 DrissionPage 相关进程
                result = subprocess.run(
                    ['tasklist', '/FI', 'IMAGENAME eq chrome.exe', '/FO', 'CSV', '/NH'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0 and 'chrome.exe' in result.stdout.lower():
                    # 不强制清理，因为用户可能在使用 Chrome
                    pass
            else:  # Linux/Mac
                # 查找可能的残留进程
                result = subprocess.run(
                    ['pgrep', '-f', 'drissionpage'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0 and result.stdout.strip():
                    pids = result.stdout.strip().split('\n')
                    for pid in pids:
                        try:
                            os.kill(int(pid), signal.SIGTERM)
                        except (ProcessLookupError, ValueError):
                            pass
        except Exception as e:
            # 静默失败，不影响主流程
            pass

    def open(self):
        """初始化浏览器"""
        super().open()
        self.logger.info("Opening DrissionPageDownloader")

        # 清理可能的残留进程
        self._cleanup_orphan_processes()

        max_retries = 3
        last_error = None
        
        for attempt in range(max_retries):
            try:
                # 创建浏览器选项
                options = self._create_options()
                
                # 尝试不同的初始化策略
                if attempt == 0:
                    # 第一次尝试：标准初始化
                    self.logger.info("Attempting standard initialization...")
                    self.page = ChromiumPage(options)
                elif attempt == 1:
                    # 第二次尝试：使用明确的端口
                    self.logger.info("Attempting with explicit port 9222...")
                    options.set_local_port(9222)
                    self.page = ChromiumPage(options)
                else:
                    # 第三次尝试：创建新配置
                    self.logger.info("Attempting with fresh configuration...")
                    fresh_options = self._create_options()
                    fresh_options.auto_port()  # 使用自动端口
                    self.page = ChromiumPage(fresh_options)
                
                self._tabs.append(self.page)
                self.logger.info("DrissionPageDownloader initialized successfully")
                return  # 成功初始化
                
            except Exception as e:
                last_error = e
                self.logger.warning(
                    f"Failed to initialize DrissionPageDownloader (attempt {attempt + 1}/{max_retries}): {e}"
                )
                
                # 清理可能创建的部分资源
                try:
                    if self.page and self.page in self._tabs:
                        self.page.close()
                        self._tabs.remove(self.page)
                        self.page = None
                    # 如果是浏览器对象问题，尝试清理
                    if hasattr(self, '_browser') and self._browser:
                        try:
                            self._browser.quit()
                        except Exception:
                            pass
                        self._browser = None
                except Exception:
                    pass
                
                # 如果不是最后一次尝试，等待一下再重试
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2  # 递增等待时间：2s, 4s
                    self.logger.info(f"Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
        
        # 所有重试都失败
        self.logger.error(f"Failed to initialize DrissionPageDownloader after {max_retries} attempts: {last_error}")
        raise last_error

    def _create_options(self) -> ChromiumOptions:
        """创建浏览器配置"""
        options = ChromiumOptions()
        
        # 无头模式
        if self.headless:
            options.set_argument('--headless')
        
        # 浏览器路径
        if self.browser_path:
            options.set_browser_path(self.browser_path)
        
        # 用户数据目录（临时目录模式）
        if self.user_data_path:
            options.set_user_data_path(self.user_data_path)
        
        # 代理设置
        if self.proxy:
            options.set_proxy(self.proxy)
        
        # 基本参数
        options.set_argument('--no-sandbox')
        options.set_argument('--disable-dev-shm-usage')
        options.set_argument('--disable-gpu')
        
        # 禁止图片加载（提升速度）
        if not self.load_images:
            options.set_argument('--blink-settings=imagesEnabled=false')
        
        return options

    async def download(self, request) -> Optional[Response]:
        """下载动态内容"""
        if not self.page:
            self.logger.error("DrissionPageDownloader page is not available")
            return None

        start_time = None
        if self.crawler.settings.get_bool("DOWNLOAD_STATS", True):
            start_time = time.time()

        try:
            # 使用 to_thread 避免阻塞事件循环
            response = await asyncio.to_thread(self._download_sync, request)
            
            # 记录统计
            if start_time and response:
                download_time = time.time() - start_time
                self.logger.debug(f"Downloaded {request.url} in {download_time:.3f}s")
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error downloading {request.url}: {e}", exc_info=True)
            return None

    def _download_sync(self, request) -> Optional[Response]:
        """同步下载（在线程中执行）"""
        try:
            # 访问页面
            self.page.get(request.url, timeout=self.timeout)
            
            # 注入反检测脚本
            self._inject_stealth_scripts(request)
            
            # 智能等待页面加载
            self._smart_wait_for_page_load(request)
            
            # 自动滚动加载更多内容
            if self._should_auto_scroll(request):
                self._auto_scroll_page(request)
            
            # 执行自定义操作（如果有）
            self._execute_custom_actions(request)
            
            # 执行翻页操作（如果有）
            self._execute_pagination_actions(request)
            
            # 获取页面内容
            page_source = self.page.html
            current_url = self.page.url
            
            # 获取 cookies
            cookies = self._get_cookies()
            
            # 构造响应对象
            response = Response(
                url=current_url,
                headers={'Content-Type': 'text/html; charset=utf-8'},
                status_code=200,
                body=page_source.encode('utf-8'),
                request=request
            )
            response.cookies = cookies
            
            return response
            
        except Exception as e:
            self.logger.error(f"Sync download error: {e}")
            return None

    def _should_auto_scroll(self, request) -> bool:
        """判断是否需要自动滚动"""
        return request.meta.get('drissionpage_auto_scroll', self.auto_scroll)
    
    def _inject_stealth_scripts(self, request):
        """
        注入反检测脚本
        
        根据 stealth_level 注入不同级别的反检测脚本：
        - none: 不注入任何脚本
        - basic: 仅隐藏 webdriver 标识
        - advanced: 全链路指纹伪造（Canvas、WebGL、AudioContext 等）
        """
        try:
            # 获取请求级别的 stealth_level（优先级高于全局配置）
            request_stealth_level = request.meta.get('drissionpage_stealth_level', self.stealth_level)
            
            # 如果 stealth_level 为 none，则不注入脚本
            if request_stealth_level == 'none':
                self.logger.debug("Stealth level is 'none', skipping anti-detection scripts")
                return
            
            # 获取反检测脚本
            stealth_script = get_drissionpage_stealth_script(request_stealth_level)
            
            if stealth_script:
                self.page.run_js(stealth_script)
                self.logger.debug(f"Injected stealth scripts (level: {request_stealth_level})")
            else:
                self.logger.debug("No stealth scripts to inject (level: none)")
                
        except Exception as e:
            self.logger.warning(f"Failed to inject stealth scripts: {e}")

    def _smart_wait_for_page_load(self, request):
        """智能等待页面加载完成"""
        # 等待文档加载完成
        self.page.wait.doc_loaded()
        
        # 可选的额外等待
        wait_selector = request.meta.get('drissionpage_wait_selector')
        if wait_selector:
            try:
                self.page.ele(wait_selector, timeout=self.timeout * 1000)
            except Exception as e:
                self.logger.warning(f"Wait element '{wait_selector}' not found: {e}")

    def _auto_scroll_page(self, request):
        """
        智能滚动加载懒加载内容
        
        滚动策略：
        1. 滚动一次，等待渲染，检查是否有新内容
        2. 如果有新内容，继续滚动；如果没有，说明到底部
        3. 重复直到滑不动（连续两次无新内容）
        """
        scroll_delay = request.meta.get('drissionpage_scroll_delay', self.scroll_delay)
        max_no_content = request.meta.get('drissionpage_max_no_content', 2)
        
        try:
            consecutive_no_content = 0
            
            # 使用 JavaScript 获取初始高度
            initial_height = self.page.run_js('return document.body.scrollHeight')
            
            while True:
                # 获取当前页面高度
                current_height = self.page.run_js('return document.body.scrollHeight')
                
                # 滚动到底部
                self.page.scroll.to_bottom()
                time.sleep(scroll_delay)
                
                # 获取滚动后的页面高度
                new_height = self.page.run_js('return document.body.scrollHeight')
                
                # 检查是否有新内容加载
                if new_height > current_height:
                    consecutive_no_content = 0
                    self.logger.debug(f"Scroll: {current_height} -> {new_height}px (new content loaded)")
                else:
                    consecutive_no_content += 1
                    self.logger.debug(f"No new content ({consecutive_no_content}/{max_no_content})")
                    
                    if consecutive_no_content >= max_no_content:
                        self.logger.debug("Reached page bottom")
                        break
                
                # 安全检查：防止无限滚动
                if consecutive_no_content > 10:
                    self.logger.warning("Too many scrolls, stopping")
                    break
                    
        except Exception as e:
            self.logger.warning(f"Auto scroll failed: {e}")

    def _scroll_to_bottom(self, params: dict):
        """
        智能滚动到底部（适合懒加载页面）
        
        滚动策略：
        1. 渐进式滚动，每次滚动到底部后等待新内容加载
        2. 检查页面高度是否增加，判断是否有新内容
        3. 当连续多次无新内容时，认为已到达底部
        """
        scroll_delay = params.get("scroll_delay", self.scroll_delay * 1000) / 1000  # 转换为秒
        max_no_content = params.get("max_no_content", 2)
        max_scrolls = params.get("max_scrolls", 50)  # 最大滚动次数限制
        
        self.logger.info(f"    Scroll config: delay={scroll_delay}s, max_no_content={max_no_content}, max_scrolls={max_scrolls}")
        
        try:
            consecutive_no_content = 0
            scroll_count = 0
            
            while scroll_count < max_scrolls:
                scroll_count += 1
                # 使用 JavaScript 获取页面高度
                current_height = self.page.run_js('return document.body.scrollHeight')
                
                self.logger.debug(f"    [{scroll_count}] Current height: {current_height}px")
                
                self.page.scroll.to_bottom()
                time.sleep(scroll_delay)
                
                new_height = self.page.run_js('return document.body.scrollHeight')
                
                if new_height > current_height:
                    consecutive_no_content = 0
                    height_diff = new_height - current_height
                    self.logger.info(f"    [{scroll_count}] Scrolled: {current_height} -> {new_height}px (+{height_diff}px)")
                else:
                    consecutive_no_content += 1
                    self.logger.info(f"    [{scroll_count}] No new content ({consecutive_no_content}/{max_no_content})")
                    if consecutive_no_content >= max_no_content:
                        self.logger.info(f"    ✓ Reached bottom after {scroll_count} scroll(s)")
                        break
                
                # 安全检查
                if consecutive_no_content > 10:
                    self.logger.warning(f"    ⚠ Too many scrolls without content, stopping at #{scroll_count}")
                    break
                    
            if scroll_count >= max_scrolls:
                self.logger.warning(f"    ⚠ Reached max scrolls limit ({max_scrolls}), stopping")
                    
        except Exception as e:
            self.logger.warning(f"    ✗ Scroll to bottom failed: {e}")

    def _execute_custom_actions(self, request):
        """
        执行自定义操作（通用接口，支持 dynamic_actions）
        
        支持的操作类型：
        - scroll: 滚动
        - scroll_to_bottom: 智能滚动到底部
        - click: 点击元素（支持 XPath 和 CSS 选择器）
        - click_and_wait: 点击并等待
        - fill: 填充表单
        - wait: 等待
        - evaluate: 执行JavaScript
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
                        self.logger.info("    → Scrolling to bottom...")
                        self._scroll_to_bottom(action_params)
                        self.logger.info("    ✓ Scroll completed")
                    elif action_type == "scroll":
                        distance = action_params.get("distance", 500)
                        self.logger.info(f"    → Scrolling down {distance}px...")
                        self.page.scroll.down(distance)
                        self.logger.info("    ✓ Scroll completed")
                    elif action_type == "click":
                        selector = PageActionHandler.extract_selector(action)
                        if selector:
                            self.logger.info(f"    → Clicking: {selector}")
                            self._click_with_selector(selector)
                            self.logger.info("    ✓ Click completed")
                    elif action_type == "click_and_wait":
                        selector = PageActionHandler.extract_selector(action)
                        wait_time = action_params.get("wait_time", 2)
                        if selector:
                            self.logger.info(f"    → Clicking and waiting: {selector}")
                            self._click_with_selector(selector)
                            time.sleep(wait_time)
                            self.logger.info(f"    ✓ Click and wait completed (waited {wait_time}s)")
                    elif action_type == "fill":
                        selector = PageActionHandler.extract_selector(action)
                        value = action_params.get("value")
                        if selector and value is not None:
                            self.logger.info(f"    → Filling: {selector}")
                            self._fill_with_selector(selector, value)
                            self.logger.info("    ✓ Fill completed")
                    elif action_type == "wait":
                        wait_time = action_params.get("time", 1)
                        self.logger.info(f"    → Waiting {wait_time}s...")
                        time.sleep(wait_time)
                        self.logger.info("    ✓ Wait completed")
                    elif action_type == "evaluate":
                        script = action_params.get("script")
                        if script:
                            self.logger.info("    → Executing JavaScript...")
                            self.page.run_js(script)
                            self.logger.info("    ✓ JavaScript executed")
                            
            except Exception as e:
                self.logger.warning(f"  ✗ Failed to execute action {i} ({action.get('type', 'unknown')}): {e}")

    def _click_with_selector(self, selector: str):
        """
        智能点击 - 自动识别 XPath 和 CSS 选择器
        
        Args:
            selector: 选择器（XPath 或 CSS）
        """
        selector_type, clean_selector = SelectorConverter.normalize_selector(selector)
        
        if selector_type == "xpath":
            # DrissionPage 原生支持 XPath
            ele = self.page.ele(f"xpath:{clean_selector}")
        else:
            # CSS 选择器
            ele = self.page.ele(clean_selector)
        
        if ele:
            ele.click()

    def _fill_with_selector(self, selector: str, value: str):
        """
        智能填充表单 - 自动识别 XPath 和 CSS 选择器
        
        Args:
            selector: 选择器（XPath 或 CSS）
            value: 要填充的值
        """
        selector_type, clean_selector = SelectorConverter.normalize_selector(selector)
        
        if selector_type == "xpath":
            ele = self.page.ele(f"xpath:{clean_selector}")
        else:
            ele = self.page.ele(clean_selector)
        
        if ele:
            ele.input(value)

    def _execute_pagination_actions(self, request):
        """
        执行翻页操作
        
        支持的操作类型：
        - scroll: 滚动翻页
        - click: 点击翻页
        - evaluate: JS脚本翻页
        """
        pagination_actions = request.meta.get('pagination_actions', [])
        
        for action in pagination_actions:
            try:
                if isinstance(action, dict):
                    action_type = action.get('type')
                    params = action.get('params', {})
                    
                    if action_type == 'scroll':
                        # 滚动翻页
                        scroll_count = params.get('count', 1)
                        scroll_delay = params.get('delay', self.scroll_delay)
                        scroll_distance = params.get('distance', 500)
                        
                        for _ in range(scroll_count):
                            self.page.scroll.down(scroll_distance)
                            time.sleep(scroll_delay)
                            
                    elif action_type == 'click':
                        # 点击翻页
                        selector = params.get('selector')
                        click_count = params.get('count', 1)
                        click_delay = params.get('delay', self.scroll_delay)
                        
                        if selector:
                            for _ in range(click_count):
                                ele = self.page.ele(selector)
                                if ele:
                                    ele.click()
                                    time.sleep(click_delay)
                                    
                    elif action_type == 'evaluate':
                        # JS脚本翻页
                        script = params.get('script')
                        if script:
                            self.page.run_js(script)
                            
                    elif action_type == 'wait':
                        # 等待
                        wait_time = params.get('time', self.scroll_delay)
                        time.sleep(wait_time)
                            
            except Exception as e:
                self.logger.warning(f"Failed to execute pagination action: {e}")

    def _get_cookies(self) -> Dict[str, str]:
        """获取 Cookies"""
        try:
            cookies = self.page.cookies()
            return {cookie['name']: cookie['value'] for cookie in cookies}
        except Exception as e:
            self.logger.warning(f"Failed to get cookies: {e}")
            return {}

    async def new_tab(self, url: str) -> Optional[ChromiumPage]:
        """创建新标签页"""
        try:
            new_page = await asyncio.to_thread(self._new_tab_sync, url)
            if new_page:
                self._tabs.append(new_page)
            return new_page
        except Exception as e:
            self.logger.error(f"Failed to create new tab: {e}")
            return None

    def _new_tab_sync(self, url: str) -> Optional[ChromiumPage]:
        """同步创建新标签页"""
        try:
            new_page = self.page.new_tab(url)
            return new_page
        except Exception as e:
            self.logger.error(f"Sync new tab error: {e}")
            return None

    async def close_tab(self, page: ChromiumPage = None):
        """关闭标签页"""
        try:
            await asyncio.to_thread(self._close_tab_sync, page)
        except Exception as e:
            self.logger.warning(f"Failed to close tab: {e}")

    def _close_tab_sync(self, page: ChromiumPage = None):
        """同步关闭标签页"""
        try:
            target = page or self.page
            if target and target in self._tabs:
                target.close()
                self._tabs.remove(target)
        except Exception as e:
            self.logger.warning(f"Sync close tab error: {e}")

    async def close(self) -> None:
        """关闭浏览器资源"""
        self.logger.info("Closing DrissionPageDownloader...")
        
        # 关闭所有标签页
        for page in self._tabs:
            try:
                await asyncio.to_thread(page.close)
            except Exception as e:
                self.logger.debug(f"Error closing page: {e}")
        
        self._tabs.clear()
        self.page = None
        self._used_pages.clear()
        
        self.logger.info("DrissionPageDownloader closed successfully")
