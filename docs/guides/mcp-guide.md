# MCP 集成指南

> Crawlo 提供 `crawlo-mcp`（Model Context Protocol）服务器，把框架的抓取能力暴露给 Claude / Cursor 等 AI 助手，让 AI 直接读取网页、抽取数据、运行爬虫。

## 什么是 MCP

MCP（Model Context Protocol）是 AI 助手与外部工具之间的标准协议。`crawlo-mcp` 以 **stdio 传输**运行一个 MCP 服务器，AI 客户端（Claude Desktop、Cursor、Codex 等）配置后即可调用 Crawlo 的抓取能力。

## 安装与启动

```bash
# 安装带 mcp 扩展的 Crawlo
pip install "crawlo[mcp]"

# 启动服务器（stdio，供 MCP 客户端拉起）
crawlo-mcp

# 或
python -m crawlo.mcp.server
```

验证是否可用：

```bash
crawlo-mcp --help  # 若正常输出帮助即安装成功
```

> 说明：`crawlo-mcp` 需要浏览器依赖时（`stealth` / `max-stealth` 模式），请额外安装对应扩展：
> `pip install "crawlo[render,stealth]"`。

## 六个工具

服务器暴露以下工具（`crawlo.mcp.server`）：

| 工具 | 说明 | 主要参数 |
|---|---|---|
| `fetch` | 抓取网页内容 | `url`、`mode`（basic/stealth/max-stealth）、`format`（html/markdown/text）、`max_length`、`cookies` |
| `extract` | 用 CSS/XPath 抽取页面数据 | `url`、`css`/`xpath`、`mode` |
| `spider` | 运行一个 Crawlo 爬虫 | `spider_name`、`start_urls`、`settings` |
| `evaluate` | 在页面执行 JS 并返回结果 | `url`、`script`、`mode` |
| `screenshot` | 页面截图 | `url`、`mode`、`full_page` |
| `status` | 服务器/框架状态 | 无 |

### fetch 三级抓取模式

- **basic**：普通 HTTP 请求（1-3s），适合大多数公开页面。
- **stealth**：无头浏览器 + 反检测（3-10s），适合有基础反爬的站点。
- **max-stealth**：Camoufox 隐身浏览器（10s+），适合强防护站点（如 Cloudflare）。

## 与 Claude / Cursor 集成

在 MCP 客户端配置文件中注册：

```json
{
  "mcpServers": {
    "crawlo": {
      "command": "crawlo-mcp",
      "args": []
    }
  }
}
```

（Claude Desktop：`~/Library/Application Support/Claude/claude_desktop_config.json`；Cursor：`~/.cursor/mcp.json`。）

配置后，AI 对话中即可说："用 crawlo 抓取 https://example.com 并总结"、"抽取这个页面的所有商品标题" 等。

## 客户端编程示例

用 Python MCP 客户端库直接调用：

```python
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    params = StdioServerParameters(command="crawlo-mcp", args=[])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print("可用工具:", [t.name for t in tools.tools])

            result = await session.call_tool(
                "fetch",
                {"url": "https://example.com", "mode": "basic", "format": "markdown"},
            )
            print(result.content[0].text[:300])


asyncio.run(main())
```

完整可运行示例见 [`examples/mcp_quickstart`](../../examples/mcp_quickstart/)。

## 配置项

`crawlo-mcp` 复用 Crawlo 全局配置（`crawlo.cfg` 或环境变量）：

- `CRAWLO_MCP_DEFAULT_MODE`：默认抓取模式（basic/stealth/max-stealth）
- `CRAWLO_MCP_FETCH_TIMEOUT`：抓取超时（秒）
- `CRAWLO_MCP_MAX_CONTENT`：单次返回内容上限（字符）
- 浏览器相关配置（`BROWSER_HEADLESS`、`CAMOUFOX_SOLVE_CLOUDFLARE` 等）沿用框架默认值

## 实现细节与注意事项

- **stdio 输出污染**：Camoufox 等浏览器可能向 stdout 打印日志，破坏 MCP 协议；服务器通过 `_redirect_browser_stdout()` 重定向浏览器输出，保证 stdio 通道纯净。
- **浏览器单例池**：`stealth` / `max-stealth` 模式复用浏览器实例，长连接下注意内存；可在配置中调低 `BROWSER_MAX_PAGES`。
- **错误提示**：工具失败时返回带 `hint` 的引导信息，方便 AI 自行调整参数重试。
- 生产环境建议通过 supervisor 等守护 `crawlo-mcp`，并限制可访问域名。

## 常见问题

**Q: `crawlo-mcp` 启动后没有任何输出？**
A: stdio 服务器正常，等待客户端连接时不输出内容属正常现象。

**Q: `fetch` 在 stealth 模式下报浏览器未安装？**
A: 安装 `pip install "crawlo[render,stealth]"` 并确认浏览器二进制可用（`playwright install chromium` 等）。

**Q: 如何让 AI 只抓取特定域名？**
A: 在配置中加入白名单中间件或代理层；`crawlo-mcp` 本身不限制 URL。
