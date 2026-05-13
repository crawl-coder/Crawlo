# 一般问题

## Crawlo 是什么？

Crawlo 是一个基于 asyncio 的现代化、高性能 Python 异步爬虫框架。它具有以下特点：

- 🚀 **高性能**：基于 asyncio 和 aiohttp，充分利用异步 I/O
- 🛡️ **强大反反爬**：内置混合下载器、Cloudflare 绕过、自适应选择器
- 🤖 **AI 集成**：支持 MCP Server，Claude/Cursor 可直接调用
- 📊 **智能调度**：优先级队列、自动重试、智能限速、背压系统
- 🔄 **灵活配置**：Standalone/Distributed/Auto 三种模式

## Crawlo 与 Scrapy 有什么区别？

| 特性 | Crawlo | Scrapy |
|------|--------|--------|
| **异步模型** | asyncio（原生异步） | Twisted（回调式） |
| **性能** | 更高（原生异步 I/O） | 高 |
| **学习曲线** | 低（类 Scrapy API） | 中等 |
| **浏览器渲染** | 内置支持 | 需要插件 |
| **AI 集成** | 原生支持 MCP | 不支持 |
| **自适应选择器** | 内置（元素自愈） | 不支持 |
| **Cloudflare 绕过** | 内置 | 需要插件 |

**选择建议**：
- 如果是新项目，推荐 Crawlo（更现代、更强大）
- 如果已有 Scrapy 项目，可以平滑迁移到 Crawlo

## Crawlo 支持哪些 Python 版本？

Crawlo 支持 **Python 3.11+**。

推荐使用 Python 3.11+ 以获得最佳性能和兼容性。

Crawlo 已内置对 **Python 3.14** 的适配支持，包括子解释器并行执行和增强的 asyncio 内省等新特性。

## Crawlo 是免费的吗？

是的！Crawlo 采用 MIT 许可证，完全免费开源。

## Crawlo 适合做什么？

- ✅ 数据采集和网页抓取
- ✅ 数据监控和价格跟踪
- ✅ SEO 分析和 competitor research
- ✅ 学术研究和数据分析
- ✅ API 测试和集成

## Crawlo 不适合做什么？

- ❌ 实时数据流处理（考虑 Kafka）
- ❌ 大规模分布式计算（考虑 Spark）
- ❌ 桌面应用开发
- ❌ Web 后端开发

## Crawlo 的性能如何？

在同等硬件条件下：
- 比同步爬虫快 **5-10倍**
- 比传统异步爬虫快 **2-3倍**
- 单机可达 **1000+ 请求/秒**（取决于目标网站）

## Crawlo 如何处理反爬虫？

Crawlo 提供多层反反爬机制：

1. **智能混合下载器**：自动切换协议/浏览器
2. **Cloudflare 绕过**：内置多种绕过策略
3. **隐身浏览器**：全链路指纹伪造
4. **自适应选择器**：网站改版自动适配
5. **智能限速**：自动调整请求频率
6. **代理支持**：简单代理和动态代理

## Crawlo 如何存储数据？

支持多种存储方式：

- **文件**：JSON、CSV、JSON Lines
- **数据库**：MySQL、MongoDB、Redis
- **自定义**：通过 Pipeline 扩展

## Crawlo 支持分布式吗？

支持！Crawlo 提供三种运行模式：

- **Standalone**：单机模式（内存队列）
- **Distributed**：分布式模式（Redis 队列）
- **Auto**：智能检测（推荐）

查看 [配置指南](../guides/configuration/) 了解详细信息。

## 如何获取帮助？

- 📖 查看 [文档](../)
- ❓ 查看 [常见问题](index.md)
- 🐛 提交 [GitHub Issue](https://github.com/crawl-coder/Crawlo/issues)
- 💬 参与社区讨论

---

**还有其他问题？** 查看其他分类的 FAQ 或提交 Issue。
