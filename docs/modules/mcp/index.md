# AI 适配层 (MCP Server)

Crawlo 内置了对 **Model Context Protocol (MCP)** 的原生支持。这使得 Claude、Cursor 等支持 MCP 协议的 AI 工具可以直接调用 Crawlo 的强大爬取能力来获取实时网页数据。

## 什么是 MCP？

MCP 是 Anthropic 推出的一种开放协议，旨在让 AI 模型能够安全、结构化地访问外部数据和工具。通过 Crawlo 的 MCP Server，AI 可以瞬间化身为一个高级爬虫工程师。

## 核心能力

- **多模式抓取 (`fetch`)**：支持 `basic` (快速)、`stealth` (隐身浏览器) 和 `max-stealth` (Camoufox) 三级降级策略。
- **正则内容提取 (`extract`)**：AI 可以指定正则模式，让服务器只传回匹配的内容片段及其上下文，极大地节省 Token 消耗。
- **并发批量抓取 (`spider`)**：AI 可以一次性下发多个 URL 任务，由 Crawlo 高效并发执行。
- **会话持久化**：支持 Cookie 保持和 Session 传递，允许 AI 处理需要登录或多步跳转的复杂流程。

## 快速运行

首先确保安装了带有 MCP 支持的 Crawlo：

```bash
pip install crawlo[mcp]
```

直接运行 MCP 服务器：

```bash
crawlo-mcp
```

## 在 AI 工具中配置

### Claude Desktop

在 `claude_desktop_config.json` 中添加：

```json
{
  "mcpServers": {
    "crawlo": {
      "command": "uvx",
      "args": ["crawlo-mcp"]
    }
  }
}
```

### Cursor

在 Cursor 的 MCP 设置中添加一个新的 Server：
- **Name**: Crawlo
- **Type**: `command`
- **Command**: `uvx crawlo-mcp`

## 技术特性

- **薄适配层设计**：通过 `QuickFetcher` 实现极速响应，常规页面 1-3 秒内返回结果。
- **内容自动优化**：内置 HTML 转 Markdown/Text 功能，去除无关脚本和样式，提供最适合 AI 阅读的内容格式。
- **标准化错误码**：如 `CONNECTIONTIMEOUT`、`CLIENTCONNECTORDNSERROR` 等，让 AI 能根据错误类型自动尝试不同的抓取策略。
- **资源安全控制**：内置并发信号量，防止 AI 工具过度消耗本地资源。
