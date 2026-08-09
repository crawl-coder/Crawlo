#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Playwright 下载器拆分模块（P2-6）
===============================
按关注点从 playwright_downloader.py 拆分出的 Mixin。
"""
from __future__ import annotations

from playwright.async_api import Page
from crawlo.constants import BROWSER_PAGE_GOTO_BLANK_TIMEOUT_MS


class PagePoolMixin:
    """单浏览器多标签页页面池管理。"""

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
        2. 导航到 about:blank 清空内容以防泄露（在锁外执行，减少锁持有时间）
        3. 如果是临时页面（非单浏览器模式），直接关闭
        4. 使用锁保护关键区域，防止竞态条件
        """
        page_id = id(page)
        should_navigate_to_blank = False
        
        async with self._page_semaphore_lock:
            # 检查是否是池中的页面
            if page_id in self._used_pages:
                self._used_pages.discard(page_id)
                
                # 释放信号量，允许排队中的任务进入
                if self._page_semaphore:
                    self._page_semaphore.release()
                    self.logger.debug(f"Released semaphore, pool size: {len(self._page_pool)}, used: {len(self._used_pages)}")
                
                # 标记需要在锁外导航到空白页
                should_navigate_to_blank = True
            else:
                # 非池中页面，直接关闭
                self.logger.debug("Closing non-pooled page")
                try:
                    await page.close()
                except Exception as e:
                    self.logger.debug(f"Failed to close page: {e}")

        # 在锁外导航到空白页，减少锁持有时间，提高并发性能
        if should_navigate_to_blank:
            try:
                await page.goto("about:blank", timeout=BROWSER_PAGE_GOTO_BLANK_TIMEOUT_MS)
            except Exception as e:
                self.logger.debug(f"Failed to navigate to blank page: {e}")
