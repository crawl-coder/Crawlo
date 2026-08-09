#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Playwright 下载器拆分模块（P2-6）
===============================
按关注点从 playwright_downloader.py 拆分出的 Mixin。
"""
from __future__ import annotations

from urllib.parse import urlparse
from playwright.async_api import Page
from crawlo.utils.parsing import PageActionHandler, SelectorConverter


class PageActionsMixin:
    """请求级页面设置、自定义动作执行与分页操作。"""

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

