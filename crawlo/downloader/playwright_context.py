#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Playwright 下载器拆分模块（P2-6）
===============================
按关注点从 playwright_downloader.py 拆分出的 Mixin。
"""
from __future__ import annotations

import asyncio
from typing import Optional, Dict  # noqa: F401  # 仅注解引用（future annotations）
from playwright.async_api import Page, BrowserContext  # noqa: F401  # 仅注解引用


class ContextProxyMixin:
    """浏览器上下文创建与代理切换（含降级）。"""

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
