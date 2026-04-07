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
import time
from typing import Optional, Dict, List

from DrissionPage import ChromiumPage, ChromiumOptions

from crawlo.downloader import DownloaderBase
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

    def open(self):
        """初始化浏览器"""
        super().open()
        self.logger.info("Opening DrissionPageDownloader")

        try:
            # 创建浏览器选项
            options = self._create_options()
            
            # 创建页面对象
            self.page = ChromiumPage(options=options)
            self._tabs.append(self.page)
            
            self.logger.debug("DrissionPageDownloader initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize DrissionPageDownloader: {e}")
            raise

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
        
        # 设置超时
        options.set_timeout(self.timeout)
        
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
            initial_height = self.page.scroll_height
            
            while True:
                # 获取当前页面高度
                current_height = self.page.scroll_height
                
                # 滚动到底部
                self.page.scroll.to_bottom()
                time.sleep(scroll_delay)
                
                # 获取滚动后的页面高度
                new_height = self.page.scroll_height
                
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
        scroll_delay = params.get("scroll_delay", self.scroll_delay)
        max_no_content = params.get("max_no_content", 2)
        
        try:
            consecutive_no_content = 0
            
            while True:
                current_height = self.page.scroll_height
                self.page.scroll.to_bottom()
                time.sleep(scroll_delay)
                new_height = self.page.scroll_height
                
                if new_height > current_height:
                    consecutive_no_content = 0
                    self.logger.debug(f"Scroll: {current_height} -> {new_height}px")
                else:
                    consecutive_no_content += 1
                    if consecutive_no_content >= max_no_content:
                        break
                
                if consecutive_no_content > 10:
                    self.logger.warning("Too many scrolls, stopping")
                    break
                    
        except Exception as e:
            self.logger.warning(f"Scroll to bottom failed: {e}")

    def _execute_custom_actions(self, request):
        """
        执行自定义操作
        
        支持的操作类型：
        - scroll: 滚动
        - scroll_to_bottom: 智能滚动到底部
        - click: 点击元素
        - click_and_wait: 点击并等待
        - fill: 填充表单
        - wait: 等待
        - evaluate: 执行JavaScript
        """
        custom_actions = request.meta.get('drissionpage_actions', [])
        
        for action in custom_actions:
            try:
                if isinstance(action, dict):
                    action_type = action.get("type")
                    action_params = action.get("params", {})
                    
                    if action_type == "scroll_to_bottom":
                        self._scroll_to_bottom(action_params)
                    elif action_type == "scroll":
                        distance = action_params.get("distance", 500)
                        self.page.scroll.down(distance)
                    elif action_type == "click":
                        selector = action_params.get("selector")
                        if selector:
                            ele = self.page.ele(selector)
                            if ele:
                                ele.click()
                    elif action_type == "click_and_wait":
                        selector = action_params.get("selector")
                        wait_time = action_params.get("wait_time", 2)
                        if selector:
                            ele = self.page.ele(selector)
                            if ele:
                                ele.click()
                                time.sleep(wait_time)
                    elif action_type == "fill":
                        selector = action_params.get("selector")
                        value = action_params.get("value")
                        if selector and value is not None:
                            ele = self.page.ele(selector)
                            if ele:
                                ele.input(value)
                    elif action_type == "wait":
                        wait_time = action_params.get("time", 1)
                        time.sleep(wait_time)
                    elif action_type == "evaluate":
                        script = action_params.get("script")
                        if script:
                            self.page.run_script(script)
                            
            except Exception as e:
                self.logger.warning(f"Failed to execute custom action: {e}")

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
                            self.page.run_script(script)
                            
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
            except Exception:
                pass
        
        self._tabs.clear()
        self.page = None
        
        self.logger.debug("DrissionPageDownloader closed.")
