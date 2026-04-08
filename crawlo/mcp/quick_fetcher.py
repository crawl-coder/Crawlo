"""
QuickFetcher - 快速抓取器

MCP 场景下的轻量级抓取器：
- basic 模式：直接使用 aiohttp（快速、1-3秒）
- stealth/max-stealth 模式：调用 Crawlo 的浏览器下载器（反检测）

设计原则：
- MCP 场景需要快速响应，不需要完整的 Spider/Engine 流程
- basic 模式直接用 aiohttp，避免中间件链的开销
- stealth 模式才调用 Crawlo 的反检测能力
"""

import asyncio
import re
import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

import aiohttp
from aiohttp import ClientSession, TCPConnector, ClientTimeout


@dataclass
class FetchResult:
    """抓取结果"""
    url: str
    status_code: int = 0
    content: str = ""
    error: Optional[str] = None
    headers: Dict[str, str] = field(default_factory=dict)
    size: int = 0
    duration: float = 0.0


class QuickFetcher:
    """
    快速抓取器

    针对 MCP 场景优化：
    - basic 模式：aiohttp 直接请求（快速）
    - stealth 模式：DrissionPage（反检测）
    - max-stealth 模式：HybridDownloader + Camoufox（最强反检测）
    """

    def __init__(self, custom_settings: Optional[Dict[str, Any]] = None):
        self._custom_settings = custom_settings or {}
        self._session: Optional[ClientSession] = None

    async def _get_session(self) -> ClientSession:
        """获取或创建 aiohttp session"""
        if self._session is None or self._session.closed:
            timeout = ClientTimeout(total=30, connect=15)
            connector = TCPConnector(
                limit=10,
                limit_per_host=5,
                ttl_dns_cache=300,
            )
            self._session = ClientSession(
                connector=connector,
                timeout=timeout,
            )
        return self._session

    async def fetch(
        self,
        url: str,
        mode: str = 'basic',
        format: str = 'markdown',
        timeout: float = 30.0,
    ) -> FetchResult:
        """
        抓取单个页面

        Args:
            url: 目标 URL
            mode: 抓取模式 - basic/stealth/max-stealth
            format: 输出格式 - html/markdown/text
            timeout: 超时时间（秒）

        Returns:
            FetchResult: 抓取结果
        """
        start = time.time()
        result = FetchResult(url=url)

        try:
            if mode == 'basic':
                response = await self._fetch_basic(url, timeout)
            elif mode == 'stealth':
                response = await self._fetch_stealth(url, timeout)
            elif mode == 'max-stealth':
                response = await self._fetch_max_stealth(url, timeout)
            else:
                raise ValueError(f"Unknown mode: {mode}")

            if response:
                result.status_code = response.status_code
                result.headers = dict(response.headers)
                result.size = len(response.body)

                if format == 'html':
                    result.content = response.text
                elif format == 'markdown':
                    result.content = self._html_to_markdown(response.text)
                else:
                    result.content = self._html_to_text(response.text)

        except Exception as e:
            result.error = f"{type(e).__name__}: {str(e)}"

        result.duration = time.time() - start
        return result

    async def _fetch_basic(self, url: str, timeout: float):
        """basic 模式：直接使用 aiohttp"""
        from crawlo.network.response import Response

        session = await self._get_session()
        try:
            async with session.get(url) as resp:
                body = await resp.read()
                return Response(
                    url=str(resp.url),
                    headers=dict(resp.headers),
                    body=body,
                    status_code=resp.status,
                )
        except Exception as e:
            raise

    async def _fetch_stealth(self, url: str, timeout: float):
        """stealth 模式：使用 DrissionPage"""
        from crawlo.network.response import Response

        try:
            from DrissionPage import ChromiumPage
        except ImportError:
            raise ImportError(
                "DrissionPage not installed. "
                "Install with: pip install DrissionPage"
            )

        page = None
        try:
            page = ChromiumPage()
            page.get(url)

            # 等待页面加载
            page.wait.doc_loaded()

            # 获取内容
            html = page.html
            current_url = page.url

            return Response(
                url=current_url,
                headers={'Content-Type': 'text/html; charset=utf-8'},
                body=html.encode('utf-8'),
                status_code=200,
            )
        finally:
            if page:
                try:
                    page.quit()
                except:
                    pass

    async def _fetch_max_stealth(self, url: str, timeout: float):
        """max-stealth 模式：使用 Camoufox（最强反检测）"""
        from crawlo.network.response import Response

        try:
            from camoufox.sync_api import Camoufox
        except ImportError:
            raise ImportError(
                "Camoufox not installed. "
                "Install with: pip install camoufox"
            )

        browser = None
        try:
            browser = Camoufox(headless=True)
            page = browser.new_page()
            page.goto(url)

            # 等待页面加载
            page.wait_for_load_state('networkidle')

            # 获取内容
            html = page.content()
            current_url = page.url

            return Response(
                url=current_url,
                headers={'Content-Type': 'text/html; charset=utf-8'},
                body=html.encode('utf-8'),
                status_code=200,
            )
        finally:
            if browser:
                try:
                    browser.close()
                except:
                    pass

    async def fetch_multiple(
        self,
        urls: List[str],
        mode: str = 'basic',
        format: str = 'markdown',
        concurrency: int = 2,
    ) -> List[FetchResult]:
        """
        并发抓取多个页面

        Args:
            urls: URL 列表
            mode: 抓取模式
            format: 输出格式
            concurrency: 并发数

        Returns:
            List[FetchResult]: 抓取结果列表
        """
        semaphore = asyncio.Semaphore(concurrency)

        async def _limited_fetch(url: str) -> FetchResult:
            async with semaphore:
                return await self.fetch(url, mode, format)

        tasks = [_limited_fetch(url) for url in urls]
        return await asyncio.gather(*tasks)

    def _html_to_text(self, html: str) -> str:
        """将 HTML 转换为纯文本"""
        # 移除脚本和样式
        text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def _html_to_markdown(self, html: str) -> str:
        """将 HTML 转换为 Markdown"""
        try:
            from markdownify import markdownify as md
            return md(html)
        except ImportError:
            return self._html_to_text(html)

    async def close(self):
        """清理资源"""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None


# 模块级别的单例实例
_fetcher_instance: Optional[QuickFetcher] = None


async def get_fetcher(custom_settings: Optional[Dict[str, Any]] = None) -> QuickFetcher:
    """获取全局 QuickFetcher 实例"""
    global _fetcher_instance
    if _fetcher_instance is None:
        _fetcher_instance = QuickFetcher(custom_settings)
    return _fetcher_instance


async def quick_fetch(
    url: str,
    mode: str = 'basic',
    format: str = 'markdown',
    timeout: float = 30.0,
) -> FetchResult:
    """
    快速抓取单个页面的便捷函数

    Args:
        url: 目标 URL
        mode: 抓取模式 - basic/stealth/max-stealth
        format: 输出格式 - html/markdown/text
        timeout: 超时时间（秒）

    Returns:
        FetchResult: 抓取结果
    """
    fetcher = await get_fetcher()
    return await fetcher.fetch(url, mode, format, timeout)
