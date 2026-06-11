"""
Crawlo MCP Server

MCP (Model Context Protocol) 服务器，让 Claude、Cursor 等 AI 工具
可以直接调用 Crawlo 的爬取能力。

这是一个**薄适配层**，只做两件事：
1. 定义 MCP 工具接口（参数、返回值）
2. 调用 Crawlo 框架的能力（QuickFetcher）

安装: pip install crawlo[mcp]
运行: crawlo-mcp

Claude Desktop 配置:
{
  "mcpServers": {
    "crawlo": {
      "command": "python",
      "args": ["-m", "crawlo.mcp"]
    }
  }
}
"""
import asyncio
import base64
from typing import Optional, Dict, List

from mcp.server.fastmcp import FastMCP

from crawlo.mcp.quick_fetcher import QuickFetcher, FetchResult

# 创建 FastMCP 实例
mcp = FastMCP("Crawlo", json_response=True)

async def _get_fetcher() -> QuickFetcher:
    """获取全局 Fetcher 实例（mcp_fetcher 与 quick_fetcher 共享同一实例）"""
    from crawlo.core.application import get_global_context
    ctx = get_global_context()
    if ctx.mcp_fetcher is not None:
        return ctx.mcp_fetcher
    with ctx.mcp_fetcher_lock:
        if ctx.mcp_fetcher is None:
            ctx.mcp_fetcher = QuickFetcher()
        # 共享同一实例，避免启动两个浏览器池
        if ctx.quick_fetcher is None:
            ctx.quick_fetcher = ctx.mcp_fetcher
    return ctx.mcp_fetcher


# 错误分类映射（帮助 AI 理解错误类型并决策下一步操作）
_ERROR_HINTS = {
    "TIMEOUT":         "Suggest: retry or switch to stealth mode.",
    "CONNECTION_ERROR": "Suggest: check URL or retry later.",
    "STEALTH_UNAVAILABLE":   "Suggest: pip install DrissionPage.",
    "MAX_STEALTH_UNAVAILABLE": "Suggest: pip install camoufox.",
    "INVALID_URL":     "Check the URL format and try again.",
    "INVALID_SCHEME":  "URL must use http:// or https://.",
    "EMPTY_RESPONSE":  "Server returned no content.",
    "INVALID_MODE":    "Use basic, stealth, or max-stealth.",
}


def _error_hint(code: str) -> str:
    """根据错误码返回建议操作"""
    return _ERROR_HINTS.get(code, "")


def _format_result(result: FetchResult, max_length: int = 0) -> str:
    """格式化输出结果"""
    lines = [
        f"URL: {result.url}",
        f"Status: {result.status_code}",
        f"Size: {result.size:,} bytes ({result.size/1024:.1f} KB)",
        f"Duration: {result.duration:.2f}s",
    ]

    if result.error:
        lines.append("")
        lines.append(f"ERROR [{result.error_code}]: {result.error}")
        hint = _error_hint(result.error_code)
        if hint:
            lines.append(f"HINT: {hint}")
        return "\n".join(lines)

    if result.cookies:
        cookie_names = list(result.cookies.keys())[:3]
        lines.append(f"Cookies: {', '.join(cookie_names)}{'...' if len(result.cookies) > 3 else ''}")

    lines.append("=" * 60)

    content = result.content
    if max_length > 0 and len(content) > max_length:
        content = content[:max_length] + f"\n\n... (truncated, {len(result.content):,} total chars)"

    lines.append(content)
    return "\n".join(lines)


# ============================================================
# MCP 工具定义
# ============================================================

@mcp.tool()
async def fetch(
    url: str,
    mode: str = "basic",
    format: str = "markdown",
    max_length: int = 0,
    cookies: Optional[Dict[str, str]] = None,
    persist_session: bool = True,
) -> str:
    """Fetch a web page using Crawlo's downloader.

    Crawlo downloads the page content from the given URL and returns it in the
    requested format. Three modes are available:

    - basic: Fast HTTP request (1-3s). Works for most sites.
    - stealth: Uses a headless browser with anti-detection (3-10s).
    - max-stealth: Uses Camoufox for heavily protected sites (10s+).

    Args:
        url: Target URL to fetch
        mode: Fetch mode - basic, stealth, or max-stealth
        format: Output format - html, markdown, or text
        max_length: Maximum characters to return (0 = no limit)
        cookies: Optional cookies to send with the request
        persist_session: Whether to persist cookies for subsequent requests

    Returns:
        Page content with metadata header
    """
    try:
        fetcher = await _get_fetcher()
        result = await fetcher.fetch(
            url, 
            mode=mode, 
            format=format, 
            cookies=cookies,
            persist_session=persist_session
        )
        return _format_result(result, max_length)
    except Exception as e:
        return f"Error: Failed to fetch {url} - {type(e).__name__}: {e}"


@mcp.tool()
async def extract(
    url: str,
    pattern: str,
    mode: str = "basic",
    context_chars: int = 150,
    cookies: Optional[Dict[str, str]] = None,
) -> str:
    """Extract specific content from a web page using regex pattern.

    Fetches the page, converts it to text, then searches for all matches of
    the given regex pattern. Each match is returned with surrounding context.

    Args:
        url: Target URL to fetch
        pattern: Regex pattern to search for
        mode: Fetch mode - basic, stealth, or max-stealth
        context_chars: Number of context characters around each match
        cookies: Optional cookies to send with the request

    Returns:
        Extracted matches with context
    """
    import re

    try:
        fetcher = await _get_fetcher()
        result = await fetcher.fetch(url, mode=mode, format='text', cookies=cookies)

        if result.error:
            return f"Error [{result.error_code}]: {result.error}"

        lines = [
            f"URL: {result.url}",
            f"Pattern: {pattern}",
            "=" * 60,
        ]

        regex = re.compile(pattern, re.DOTALL | re.IGNORECASE)
        matches = list(regex.finditer(result.content))

        if not matches:
            lines.append("No matches found.")
            return "\n".join(lines)

        lines.append(f"Found {len(matches)} match(es):\n")

        for i, match in enumerate(matches, 1):
            start = max(0, match.start() - context_chars)
            end = min(len(result.content), match.end() + context_chars)

            context = result.content[start:end]
            if start > 0:
                context = "..." + context
            if end < len(result.content):
                context = context + "..."

            lines.append(f"Match {i}:")
            lines.append(f"  {match.group()}")
            lines.append(f"  Context: {context}")
            lines.append("")

        return "\n".join(lines)

    except re.error as e:
        return f"Regex error: {e}"
    except Exception as e:
        return f"Error: Failed to extract from {url} - {type(e).__name__}: {e}"


@mcp.tool()
async def spider(
    urls: List[str],
    mode: str = "basic",
    format: str = "markdown",
    concurrency: int = 2,
    delay: float = 0.0,
    cookies: Optional[Dict[str, str]] = None,
) -> str:
    """Crawl multiple pages concurrently using Crawlo's spider engine.

    Fetches multiple URLs concurrently with configurable concurrency limits.
    Results are returned as a structured summary.

    Args:
        urls: List of URLs to crawl
        mode: Fetch mode - basic, stealth, or max-stealth
        format: Output format per page - html, markdown, or text
        concurrency: Number of concurrent requests (max 5)
        delay: Delay between request batches in seconds (use 1.0+ for target site protection)
        cookies: Optional cookies to send with each request

    Returns:
        Summary of all crawled pages
    """
    try:
        fetcher = await _get_fetcher()
        results = await fetcher.fetch_multiple(
            urls,
            mode=mode,
            format=format,
            concurrency=concurrency,
            delay=delay,
        )

        # 统计
        success = sum(1 for r in results if not r.error)
        failed = len(results) - success
        total_size = sum(r.size for r in results)

        lines = [
            "Crawlo Spider Results",
            "=" * 60,
            f"URLs requested: {len(urls)}",
            f"Successful: {success}",
            f"Failed: {failed}",
            f"Total content: {total_size:,} bytes ({total_size/1024:.1f} KB)",
            f"Mode: {mode}",
            f"Concurrency: {concurrency}",
            "=" * 60,
        ]

        # 输出每个结果（截断以节省 token）
        for i, result in enumerate(results, 1):
            lines.append(f"\n--- Page {i}: {result.url} ({result.size:,} bytes) ---")

            if result.error:
                lines.append(f"Error: {result.error}")
            else:
                # 截断内容
                content = result.content[:2000]
                if len(result.content) > 2000:
                    content += f"\n\n... (truncated, {len(result.content):,} total chars)"
                lines.append(content)

        return "\n".join(lines)

    except Exception as e:
        return f"Error: Failed to crawl {len(urls)} URLs - {type(e).__name__}: {e}"


@mcp.tool()
async def evaluate(
    url: str,
    script: str,
    mode: str = "stealth",
) -> str:
    """Execute JavaScript on a web page and return the result.

    Uses a headless browser to load the page and run custom JavaScript.
    Useful for extracting data that requires JS rendering or interacting
    with the page before extraction.

    Args:
        url: Target URL
        script: JavaScript code to execute (e.g., 'document.title')
        mode: stealth or max-stealth

    Returns:
        JavaScript execution result as string
    """
    try:
        fetcher = await _get_fetcher()
        return await fetcher.evaluate(url, script, mode=mode)
    except Exception as e:
        return f"Error: {type(e).__name__}: {e}"


@mcp.tool()
async def screenshot(
    url: str,
    mode: str = "stealth",
) -> str:
    """Take a screenshot of a web page.

    Loads the page in a headless browser and captures a screenshot.
    Returns the image as a base64-encoded PNG string that the AI can
    analyze visually.

    Args:
        url: Target URL
        mode: stealth or max-stealth

    Returns:
        Base64-encoded PNG image or error message
    """
    try:
        fetcher = await _get_fetcher()
        data = await fetcher.screenshot(url, mode=mode)
        if data:
            b64 = base64.b64encode(data).decode('utf-8')
            return f"Screenshot of {url}\nSize: {len(data):,} bytes\nBase64: data:image/png;base64,{b64}"
        return f"Error: Failed to capture screenshot of {url}"
    except Exception as e:
        return f"Error: {type(e).__name__}: {e}"


@mcp.tool()
async def status() -> str:
    """Get Crawlo framework status and environment info.

    Returns information about the Crawlo installation, Python environment,
    and available downloaders.

    Returns:
        Status information
    """
    import sys
    import platform

    lines = [
        "Crawlo MCP Server Status",
        "=" * 60,
        f"Python: {sys.version.split()[0]}",
        f"Platform: {platform.system()} {platform.release()}",
        f"Architecture: {platform.machine()}",
        "",
        "Available Downloaders:",
    ]

    # 检查各下载器是否可用
    downloaders = [
        ('AioHttpDownloader', 'aiohttp'),
        ('HttpXDownloader', 'httpx'),
        ('CurlCffiDownloader', 'curl_cffi'),
        ('DrissionPageDownloader', 'DrissionPage'),
        ('PlaywrightDownloader', 'playwright'),
        ('HybridDownloader', None),
    ]

    for name, pkg in downloaders:
        try:
            if pkg:
                __import__(pkg.replace('-', '_'))
            lines.append(f"  ✓ {name}")
        except ImportError:
            lines.append(f"  ✗ {name} (install: pip install {pkg})")

    # 检查 Camoufox
    try:
        __import__('camoufox')
        lines.append("  ✓ Camoufox (max-stealth mode available)")
    except ImportError:
        lines.append("  ✗ Camoufox (install: pip install camoufox)")

    # 检查 markdownify
    try:
        __import__('markdownify')
        lines.append("  ✓ markdownify (markdown conversion)")
    except ImportError:
        lines.append("  ✗ markdownify (markdown fallback to text)")

    return "\n".join(lines)


# ============================================================
# MCP Prompts
# ============================================================

@mcp.prompt()
def scrape_prompt() -> str:
    """Scraping workflow prompt"""
    return """You are a web scraping assistant. For each task:
1. Use fetch() first with mode='basic' to get page content in markdown
2. If fetch() returns empty or error, retry with mode='stealth'
3. Use extract() with regex to find specific patterns in the content
4. For bulk URLs, use spider() with concurrency=2 and delay=1.0
5. Use evaluate() to run JavaScript for dynamic content extraction
6. Use screenshot() for visual analysis when needed"""

@mcp.prompt()
def data_collection_prompt() -> str:
    """Data collection workflow prompt"""
    return """To collect structured data from a website:
1. fetch(url, mode='basic', format='markdown') — get the page
2. If the page uses JavaScript rendering, retry with mode='stealth'
3. Use extract(url, pattern, mode) to find specific data with regex
4. For multiple similar pages, collect URLs first, then use spider()
5. For heavily protected sites, use mode='max-stealth'
6. After each fetch, cookies are persisted automatically via persist_session"""


def main():
    """MCP Server 入口点"""
    mcp.run(transport='stdio')


if __name__ == '__main__':
    main()
