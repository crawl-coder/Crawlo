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
import atexit
import re
import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from urllib.parse import urlparse

import aiohttp
from aiohttp import ClientSession, TCPConnector, ClientTimeout


@dataclass
class FetchResult:
    """抓取结果"""
    url: str
    status_code: int = 0
    content: str = ""
    error: Optional[str] = None
    error_code: Optional[str] = None
    headers: Dict[str, str] = field(default_factory=dict)
    cookies: Dict[str, str] = field(default_factory=dict)
    size: int = 0
    duration: float = 0.0
    success: bool = False


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
        self._cookies: Dict[str, str] = {}  # Session-level cookies

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
                cookie_jar=aiohttp.CookieJar(unsafe=True)
            )
        return self._session

    async def fetch(
        self,
        url: str,
        mode: str = 'basic',
        format: str = 'markdown',
        timeout: float = 30.0,
        cookies: Optional[Dict[str, str]] = None,
        headers: Optional[Dict[str, str]] = None,
        persist_session: bool = True,
    ) -> FetchResult:
        """
        抓取单个页面

        Args:
            url: 目标 URL
            mode: 抓取模式 - basic/stealth/max-stealth
            format: 输出格式 - html/markdown/text
            timeout: 超时时间（秒）
            cookies: 自定义 Cookie
            headers: 自定义 Header
            persist_session: 是否保持会话（Cookie）

        Returns:
            FetchResult: 抓取结果
        """
        start = time.time()
        result = FetchResult(url=url)
        
        # URL 验证
        if not url or not isinstance(url, str):
            result.error = "URL cannot be empty"
            result.error_code = "INVALID_URL"
            result.duration = time.time() - start
            return result
        
        parsed = urlparse(url)
        if parsed.scheme not in ('http', 'https'):
            result.error = f"URL must use HTTP or HTTPS scheme, got: {parsed.scheme or 'empty'}"
            result.error_code = "INVALID_SCHEME"
            result.duration = time.time() - start
            return result
        
        if not parsed.netloc:
            result.error = "URL must contain a valid domain"
            result.error_code = "INVALID_URL"
            result.duration = time.time() - start
            return result
        
        # 合并 Cookie
        current_cookies = self._cookies.copy() if persist_session else {}
        if cookies:
            current_cookies.update(cookies)

        try:
            if mode == 'basic':
                response = await self._fetch_basic(url, timeout, current_cookies, headers)
            elif mode == 'stealth':
                response = await self._fetch_stealth(url, timeout, current_cookies, headers)
                if response is None:
                    result.error = "Stealth mode failed: DrissionPage not installed or browser error"
                    result.error_code = "STEALTH_UNAVAILABLE"
                    return result
            elif mode == 'max-stealth':
                response = await self._fetch_max_stealth(url, timeout, current_cookies, headers)
                if response is None:
                    result.error = "Max-stealth mode failed: camoufox not installed or browser error"
                    result.error_code = "MAX_STEALTH_UNAVAILABLE"
                    return result
            else:
                result.error = f"Unknown mode: {mode}"
                result.error_code = "INVALID_MODE"
                return result

            if response:
                result.status_code = response.status
                result.headers = dict(response.headers)
                result.cookies = response.cookies if hasattr(response, 'cookies') else {}
                result.size = len(response.body)
                result.success = 200 <= response.status < 400

                if persist_session and result.cookies:
                    self._cookies.update(result.cookies)

                if format == 'html':
                    result.content = response.text
                elif format == 'markdown':
                    result.content = self._html_to_markdown(response.text)
                else:
                    result.content = self._html_to_text(response.text)
            else:
                result.error = "No response received"
                result.error_code = "EMPTY_RESPONSE"

        except Exception as e:
            result.error = str(e)
            result.error_code = type(e).__name__.upper()

        result.duration = time.time() - start
        return result

    async def _fetch_basic(self, url: str, timeout: float, cookies: Dict[str, str], headers: Optional[Dict[str, str]]):
        """basic 模式：直接使用 aiohttp"""
        from crawlo.network.response import Response
        from yarl import URL

        session = await self._get_session()
        async with session.get(url, cookies=cookies, headers=headers) as resp:
            body = await resp.read()
            response = Response(
                url=str(resp.url),
                headers=dict(resp.headers),
                body=body,
                status=resp.status,
            )
            # 提取与当前 URL 相关的 Cookie（避免获取所有域名的 Cookie）
            url_obj = URL(url)
            response.cookies = {
                c.key: c.value 
                for c in session.cookie_jar 
                if c.domain == url_obj.host or url_obj.host.endswith(c.domain.lstrip('.'))
            }
            return response

    async def _fetch_stealth(self, url: str, timeout: float, cookies: Dict[str, str], headers: Optional[Dict[str, str]]):
        """stealth 模式：使用 DrissionPage"""
        from crawlo.network.response import Response

        try:
            from DrissionPage import ChromiumPage, ChromiumOptions
        except ImportError:
            return None  # 依赖未安装，返回 None 让调用方处理

        page = None
        try:
            # 创建无头浏览器选项
            co = ChromiumOptions()
            co.set_argument('--headless', True)
            co.set_argument('--disable-gpu')
            co.set_argument('--no-sandbox')
            
            page = ChromiumPage(addr_or_opts=co)
            
            # 设置 Cookie
            if cookies:
                for k, v in cookies.items():
                    try:
                        page.set.cookie(name=k, value=v, url=url)
                    except Exception:
                        pass  # Cookie 设置失败不影响主流程
            
            # 访问页面
            page.get(url, timeout=timeout)
            page.wait.doc_loaded()

            html = page.html
            current_url = page.url
            
            # 获取页面 Cookie
            try:
                page_cookies = {c['name']: c['value'] for c in page.cookies()}
            except Exception:
                page_cookies = {}

            response = Response(
                url=current_url,
                headers={'Content-Type': 'text/html; charset=utf-8'},
                body=html.encode('utf-8') if isinstance(html, str) else html,
                status=200,
            )
            response.cookies = page_cookies
            return response
            
        except Exception as e:
            # 浏览器操作失败，记录错误但继续执行
            return None
        finally:
            if page:
                try:
                    page.quit()
                except Exception:
                    pass

    async def _fetch_max_stealth(self, url: str, timeout: float, cookies: Dict[str, str], headers: Optional[Dict[str, str]]):
        """max-stealth 模式：使用 Camoufox（最强反检测）"""
        from crawlo.network.response import Response

        try:
            from camoufox.async_api import AsyncCamoufox
        except ImportError:
            return None  # 依赖未安装，返回 None 让调用方处理

        try:
            async with AsyncCamoufox(headless=True) as browser:
                context = await browser.new_context()
                
                # 设置 Cookie
                if cookies:
                    try:
                        pw_cookies = [{"name": k, "value": v, "url": url} for k, v in cookies.items()]
                        await context.add_cookies(pw_cookies)
                    except Exception:
                        pass  # Cookie 设置失败不影响主流程
                
                page = await context.new_page()
                
                # 设置自定义 Header
                if headers:
                    try:
                        await page.set_extra_http_headers(headers)
                    except Exception:
                        pass
                    
                await page.goto(url, wait_until='networkidle', timeout=timeout * 1000)
                
                html = await page.content()
                current_url = page.url
                
                # 获取 Cookie
                try:
                    page_cookies = {c['name']: c['value'] for c in await context.cookies()}
                except Exception:
                    page_cookies = {}

                response = Response(
                    url=current_url,
                    headers={'Content-Type': 'text/html; charset=utf-8'},
                    body=html.encode('utf-8') if isinstance(html, str) else html,
                    status=200,
                )
                response.cookies = page_cookies
                return response
                
        except Exception as e:
            # 浏览器操作失败，记录错误但继续执行
            return None

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
        # 使用 return_exceptions=True 确保所有任务都完成，即使个别失败
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 将异常转换为 FetchResult
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                final_results.append(FetchResult(
                    url=urls[i],
                    error=str(result),
                    error_code=type(result).__name__.upper()
                ))
            else:
                final_results.append(result)
        
        return final_results

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
        """Convert HTML to Markdown"""
        try:
            from markdownify import markdownify as md
            return md(html)
        except ImportError:
            # Fallback to plain text if markdownify is not available
            return self._html_to_text(html)

    async def close(self):
        """清理资源"""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
        self._cookies.clear()


def _cleanup_fetcher():
    """清理全局 Fetcher 实例（程序退出时调用）"""
    global _fetcher_instance
    if _fetcher_instance is not None:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(_fetcher_instance.close())
            else:
                loop.run_until_complete(_fetcher_instance.close())
        except Exception:
            pass  # 清理失败不影响退出
        _fetcher_instance = None


# 注册退出清理
atexit.register(_cleanup_fetcher)


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
