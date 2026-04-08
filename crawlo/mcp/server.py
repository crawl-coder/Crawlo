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
      "command": "uvx",
      "args": ["crawlo-mcp"]
    }
  }
}
"""

from mcp.server.fastmcp import FastMCP

from crawlo.mcp.quick_fetcher import QuickFetcher, FetchResult

# 创建 FastMCP 实例
mcp = FastMCP("Crawlo", json_response=True)

# 全局 Fetcher 实例（延迟初始化）
_fetcher: QuickFetcher = None


async def _get_fetcher() -> QuickFetcher:
    """获取全局 Fetcher 实例"""
    global _fetcher
    if _fetcher is None:
        _fetcher = QuickFetcher()
    return _fetcher


def _format_result(result: FetchResult, max_length: int = 0) -> str:
    """格式化输出结果"""
    lines = [
        f"URL: {result.url}",
        f"Status: {result.status_code}",
        f"Size: {result.size:,} bytes ({result.size/1024:.1f} KB)",
        f"Duration: {result.duration:.2f}s",
        "=" * 60,
    ]

    if result.error:
        lines.append(f"Error: {result.error}")
        return "\n".join(lines)

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

    Returns:
        Page content with metadata header
    """
    fetcher = await _get_fetcher()
    result = await fetcher.fetch(url, mode=mode, format=format)
    return _format_result(result, max_length)


@mcp.tool()
async def extract(
    url: str,
    pattern: str,
    mode: str = "basic",
    context_chars: int = 150,
) -> str:
    """Extract specific content from a web page using regex pattern.

    Fetches the page, converts it to text, then searches for all matches of
    the given regex pattern. Each match is returned with surrounding context.

    Args:
        url: Target URL to fetch
        pattern: Regex pattern to search for
        mode: Fetch mode - basic, stealth, or max-stealth
        context_chars: Number of context characters around each match

    Returns:
        Extracted matches with context
    """
    import re

    fetcher = await _get_fetcher()
    result = await fetcher.fetch(url, mode=mode, format='text')

    if result.error:
        return f"Error: {result.error}"

    lines = [
        f"URL: {result.url}",
        f"Pattern: {pattern}",
        "=" * 60,
    ]

    try:
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

    except re.error as e:
        lines.append(f"Regex error: {e}")

    return "\n".join(lines)


@mcp.tool()
async def spider(
    urls: list[str],
    mode: str = "basic",
    format: str = "markdown",
    concurrency: int = 2,
) -> str:
    """Crawl multiple pages concurrently using Crawlo's spider engine.

    Fetches multiple URLs concurrently with configurable concurrency limits.
    Results are returned as a structured summary.

    Args:
        urls: List of URLs to crawl
        mode: Fetch mode - basic, stealth, or max-stealth
        format: Output format per page - html, markdown, or text
        concurrency: Number of concurrent requests

    Returns:
        Summary of all crawled pages
    """
    fetcher = await _get_fetcher()
    results = await fetcher.fetch_multiple(
        urls,
        mode=mode,
        format=format,
        concurrency=concurrency,
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


def main():
    """MCP Server 入口点"""
    mcp.run(transport='stdio')


if __name__ == '__main__':
    main()
