# Crawlo + MCP：让 AI 直接帮你爬网页

> AI 说"帮我取这个网页的数据"，Crawlo 真的做到了。

---

## 当爬虫遇上 AI

2025 年，AI Coding Agent（如 Claude、Cursor）正在重新定义开发方式。除了帮你写代码，AI 还能直接帮你做事——比如，爬网页。

Crawlo 的 **MCP Server** 让这一切成为现实：

- AI 写代码时遇到一个网页 URL → 直接调用 Crawlo 把内容取回来
- 需要批量采集数据 → AI 调用 Crawlo 并发爬取
- 想知道页面结构 → AI 调用 Crawlo 返回 HTML/Markdown

---

## 什么是 MCP？

**MCP（Model Context Protocol）** 是 Anthropic 提出的开放协议，让 AI 模型能够与外部工具交互。

```
┌─────────┐     MCP Protocol     ┌──────────────┐
│  Claude  │◄──────────────────►│ Crawlo MCP   │
│  (AI)    │    fetch/extract   │   Server      │
└─────────┘                     └──────┬───────┘
                                       │
                                ┌──────▼──────┐
                                │   Crawlo     │
                                │ QuickFetcher │
                                └─────────────┘
```

---

## 安装与配置

```bash
pip install crawlo[mcp]
```

### Claude Desktop 配置

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

启动方式：`crawlo-mcp`（通过 stdio 与 AI 客户端通信）。

---

## MCP 提供的四个工具

### 1. fetch — 取回页面内容

让 AI 直接获取任意网页：

```
你：帮我看看 https://example.com 页面上有什么内容

AI：调用 fetch(url="https://example.com")
  → 返回页面的 Markdown/HTML/纯文本
```

支持三种获取模式：
- **basic**：快速 HTTP 请求（1-3秒），适合大多数网站
- **stealth**：无头浏览器 + 反检测（3-10秒），适合有反爬的网站
- **max-stealth**：Camoufox 浏览器（10秒+），适合重度防护站点

### 2. extract — 正则提取内容

获取页面并用正则表达式提取特定内容：

```
你：从 https://news.ycombinator.com 提取所有链接

AI：调用 extract(url="https://news.ycombinator.com", pattern=r'https?://[^\s"<>]+')
  → 返回所有匹配的 URL 及上下文
```

### 3. spider — 并发爬取多页

一次抓取多个页面，支持并发控制：

```
你：帮我同时抓取这 5 个 URL 的内容

AI：调用 spider(urls=[url1, url2, ...], concurrency=2)
  → 返回所有页面的内容汇总
```

支持配置并发数和请求间隔，避免对目标站点造成压力。

### 4. status — 查看框架状态

查看 Crawlo 的运行环境和可用下载器：

```
AI：调用 status()
  → ✓ AioHttpDownloader
  → ✓ HttpXDownloader  
  → ✗ Playwright (install with: pip install playwright)
  → ...
```

---

## 实战演示

### 场景 1：AI 帮你获取网页内容

**你的输入：**

> 帮我看看 https://news.ycombinator.com 首页上有什么

**Claude 的操作：**

```
→ 调用 fetch(url="https://news.ycombinator.com", format="text")
→ 获取页面内容
→ 分析：首页有 30 篇文章，包括...
```

### 场景 2：AI 帮你批量采集

**你的输入：**

> 帮我同时采集这三篇文章的内容：
> https://example.com/article/1
> https://example.com/article/2
> https://example.com/article/3

**Claude 的操作：**

```
→ 调用 spider(urls=[...], concurrency=2, delay=1.0)
→ 等待所有页面加载完成
→ 汇总结果：3 pages fetched, total 45KB
```

### 场景 3：绕过反爬

**你的输入：**

> 这个网站用 aiohttp 取不到，帮我用浏览器试试

**Claude 的操作：**

```
→ 调用 fetch(url="...", mode="stealth")
→ 使用 DrissionPage 无头浏览器，注入反检测脚本
→ 成功获取页面内容
```

---

## AI + Crawlo = 爬虫开发新范式

有了 Crawlo MCP，开发流程变成：

1. **你**：提出需求（"帮我抓取 XX 网站的数据"）
2. **AI**：分析页面结构 + 调用 Crawlo 获取内容
3. **AI**：生成完整的 Spider 代码
4. **你**：审查、运行、入库

---

---

*关注公众号，获取更多 Crawlo 技术干货和爬虫实战经验。*
