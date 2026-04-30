#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Playwright 智能等待策略 Mixin

提取自 PlaywrightDownloader，包含：
- WaitStrategy / ResourceType 枚举常量
- 智能等待（网络空闲、DOM 就绪、SPA 检测）
- 资源屏蔽（图片/CSS/字体/广告）
- 自动滚动（懒加载内容）
"""
from urllib.parse import urlparse

from crawlo.downloader.constants import AD_DOMAINS
from crawlo.constants import BROWSER_ELEMENT_WAIT_TIMEOUT_MS, BROWSER_NETWORK_IDLE_TIMEOUT_MS


# ==================== 智能等待策略常量 ====================

class WaitStrategy:
    """等待策略枚举"""
    AUTO = "auto"  # 自动检测最佳等待策略
    NETWORK_IDLE = "networkidle"  # 等待网络空闲
    DOM_READY = "domcontentloaded"  # 等待 DOM 加载完成
    ELEMENT = "element"  # 等待特定元素出现
    CUSTOM = "custom"  # 自定义等待函数


# ==================== 资源类型常量 ====================

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


# ==================== 智能等待 Mixin ====================

class SmartWaitMixin:
    """智能等待、资源屏蔽、自动滚动 Mixin"""

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

    async def _smart_wait_for_page_load(self, page, request):
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

    async def _auto_wait_strategy(self, page, request):
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
                        await element.wait_for(timeout=BROWSER_ELEMENT_WAIT_TIMEOUT_MS)
                        break
                except Exception:
                    continue

            # 额外等待网络稳定
            try:
                await page.wait_for_load_state("networkidle", timeout=BROWSER_NETWORK_IDLE_TIMEOUT_MS)
            except Exception:
                pass
        else:
            # 非 SPA 页面：简单等待网络空闲
            try:
                await page.wait_for_load_state("networkidle", timeout=BROWSER_NETWORK_IDLE_TIMEOUT_MS)
            except Exception:
                pass

    async def _detect_spa(self, page) -> bool:
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

    async def _setup_resource_blocking(self, page, request):
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

    # ==================== 自动滚动 ====================

    def _should_auto_scroll(self, request) -> bool:
        """判断是否需要自动滚动"""
        # 请求级别配置优先
        return request.meta.get("playwright_auto_scroll", self.auto_scroll)

    async def _scroll_to_bottom(self, page, params: dict):
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

    async def _auto_scroll_page(self, page, request):
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
