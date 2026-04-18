"""
Crawlo MCP (Model Context Protocol) 模块

让 Claude、Cursor 等 AI 工具能直接调用 Crawlo 的爬取能力。

这是一个**薄适配层**，真正的能力来自 Crawlo 框架本身：
- Downloader 体系（AioHttpDownloader, DrissionPageDownloader 等）
- MiddlewareManager（自动包含 CloudflareBypassMiddleware 等）
- Settings 配置系统

使用方式:
    # 安装
    pip install crawlo[mcp]

    # 运行 MCP Server
    crawlo-mcp
"""

try:
    from crawlo.mcp.server import mcp, main
    from crawlo.mcp.quick_fetcher import QuickFetcher, quick_fetch, FetchResult
except ImportError:
    # mcp 包未安装时的优雅降级
    mcp = None
    main = None
    QuickFetcher = None
    quick_fetch = None
    FetchResult = None

__all__ = [
    'mcp',
    'main',
    'QuickFetcher',
    'quick_fetch',
    'FetchResult',
]
