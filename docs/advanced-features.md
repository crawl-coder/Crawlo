# 高级特性与 AI 集成

Crawlo 提供了一系列针对现代 Web 抓取挑战的高级特性，特别是针对 AI 代理（如 Claude/Cursor）的集成支持。

## 1. AI 适配层 (MCP Server)

### 什么是 MCP？
MCP 是 **Model Context Protocol** 的简称。Crawlo 实现了 MCP 服务，允许 AI 工具（如 Claude Desktop、Cursor）直接调用 Crawlo 进行网页数据抓取。

### 核心能力
- **`fetch`**: 将网页转换为 Markdown 或纯文本，供 AI 直接阅读。
- **`extract`**: AI 指定正则模式，在服务端完成内容提取。
- **`spider`**: 批量抓取多个 URL，并返回结构化摘要。
- **Session 保持**: 自动维护 Cookie 和会话状态。

---

## 2. 自适应选择器 (Adaptive Selector)

### 核心功能：自愈
当目标网站改版，传统的 CSS/XPath 选择器失效时，自适应选择器会自动启动。

### 匹配维度
- **元素指纹**：利用 Tag、Text、Path、Attributes 等多维特征。
- **加权算法**：基于加权平均相似度匹配，找回改版后的元素。
- **LRU 缓存**：内置内存缓存层，确保在高并发抓取时性能依然卓越。

---

## 3. 混合下载器 (Hybrid Downloader)

### 智能切换
根据 URL 正则模式或域名，在 **aiohttp (快)** 与 **Playwright (全)** 之间自动切换。

### 反检测 (Stealth)
集成 Playwright Stealth 脚本，伪造全链路浏览器指纹（Navigator, WebGL, Canvas, AudioContext 等），规避反爬检测。

---

## 4. Cloudflare 自动绕过 (Bypass)

### 智能识别
自动识别 403/503 错误及 Cloudflare Turnstile 挑战。

### 动态降级
一旦检测到挑战，系统会自动从协议下载降级为浏览器渲染，并执行绕过逻辑。

---

## 5. 分布式部署

### 集群架构
- **任务分发**：使用 Redis 列表（List）分发任务。
- **全局指纹**：使用 Redis 集合（Set）进行去重。
- **状态同步**：共享爬虫运行状态。

---

## 6. 通知系统

### 多平台支持
- **飞书 (Feishu)**：发送抓取报告及异常告警。
- **钉钉 (DingTalk)**：集成自定义机器人。
- **邮件 (Email)**：支持 SMTP 发送。
