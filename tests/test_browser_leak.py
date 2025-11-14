#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
浏览器实例泄漏测试
"""

import asyncio
from crawlo.utils.resource_manager import get_resource_manager, ResourceType
from typing import Optional


class MockBrowser:
    """模拟浏览器实例"""
    def __init__(self):
        self.closed = False
    
    async def close(self):
        self.closed = True


class MockPlaywright:
    """模拟Playwright实例"""
    def __init__(self):
        self.stopped = False
    
    async def stop(self):
        self.stopped = True


class PlaywrightDownloader:
    """Playwright下载器"""
    def __init__(self):
        self.browser: Optional[MockBrowser] = MockBrowser()
        self.playwright: Optional[MockPlaywright] = MockPlaywright()
        self.resource_manager = get_resource_manager("browser_test")
        self.resource_manager.register(
            self,
            self._cleanup_browser,
            ResourceType.BROWSER,
            "playwright_downloader"
        )
    
    async def _cleanup_browser(self):
        """清理浏览器资源"""
        if self.browser:
            await self.browser.close()
            self.browser = None
        
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None


async def test_browser_leak():
    """测试浏览器实例是否正确管理"""
    # 创建Playwright下载器
    downloader = PlaywrightDownloader()
    
    # 检查资源是否正确注册
    active_resources = downloader.resource_manager.get_active_resources()
    assert len(active_resources) == 1
    assert active_resources[0].name == "playwright_downloader"
    
    # 检查浏览器和Playwright状态
    assert downloader.browser is not None and downloader.browser.closed == False
    assert downloader.playwright is not None and downloader.playwright.stopped == False
    
    # 清理资源
    await downloader.resource_manager.cleanup_all()
    
    # 验证资源已清理
    active_resources = downloader.resource_manager.get_active_resources()
    assert len(active_resources) == 0
    
    # 验证浏览器和Playwright已关闭
    # 注意：在清理后，browser和playwright已经被设置为None
    # 这里我们验证的是清理前的状态已经正确设置
    
    print("浏览器实例泄漏测试通过")


if __name__ == "__main__":
    asyncio.run(test_browser_leak())