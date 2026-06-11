# 使用指南

本系列指南按使用场景分类，帮助你解决具体的开发问题。

## 📖 指南分类

### ⚙️ [配置指南](configuration/)
- 基础配置
- 三种部署模式详解（内存/多节点协作/分布式系统）
- 高级配置
- 配置示例

### 🔌 [扩展系统](extension-guide.md)
- 8 个内置扩展：日志/监控/健康检查/请求录制
- 自定义扩展开发
- ExtensionManager 事件订阅

### 📬 [通知系统](notification-guide.md)
- 5 渠道：钉钉/飞书/企微/邮件/短信
- 30+ 内置消息模板
- 自定义模板 + 防刷机制

### 🔗 [中间件参考](../concepts/middleware-reference.md)
- 13 个内置中间件逐一说明
- 洋葱模型执行顺序 + 优先级表
- 自定义中间件开发

### 🌐 [代理配置](proxy-guide.md)
- 静态代理列表 + 动态 API
- 自动切换策略 + 白名单

### 🛡️ [Cloudflare 绕过](cloudflare-bypass.md)
- 自动检测 JS Challenge / Turnstile
- CloakBrowser / Camoufox / Playwright 三种浏览器
- 与 HybridDownloader 协同

### 🧰 [Helpers 工具集](helpers-reference.md)
- TimeUtils: 时间格式化与解析
- TextCleaner: HTML/空白符/文本清洗
- FileDownloader: 异步下载 + 断点续传
- MySQLExistsChecker: 数据库去重检查
- 元素指纹 + 多维度相似度匹配
- 网站改版时选择器自动恢复
- class/层级/文本/属性变化全覆盖
- SQLite/Redis 双存储后端

### 📊 [调度指南](scheduling/)
- [定时任务调度器](scheduling/scheduler.md) — Cron + Interval 双触发模式
- 并发控制
- 限速策略
- [背压系统](scheduling/backpressure.md)


## 🎯 按场景查找

| 你的需求 | 查看指南 |
|---------|---------|
| **如何配置爬虫？** | [配置指南](configuration/) |
| **如何提升性能？** | [调度指南](scheduling/) |
| **如何绕过反爬？** | 查看[反检测中间件](../../crawlo/middleware/) |
| **如何存储数据？** | 查看[数据管道](../../crawlo/pipelines/) |
| **如何部署上线？** | 查看[生产部署文档](../deployment.md) |

## 💡 使用建议

- 🔍 **按需查阅**：不需要从头到尾阅读，根据需求查找对应指南
- 📝 **参考示例**：每个指南都有实际代码示例
- 🔗 **交叉引用**：相关主题会互相链接，方便深入学习

---

**需要解决具体问题？** 选择上方的指南分类开始阅读。
