# 核心概念

深入理解 Crawlo 框架的设计理念和核心机制。

## 📖 核心概念

### 🏗️ [架构设计](architecture.md)
- 模块化设计
- 核心组件交互
- 数据流转

### 🧩 [核心组件](core-components.md)
- Engine（引擎）
- Scheduler（调度器）
- Downloader（下载器）
- Spider（爬虫）
- Pipeline（数据管道）
- Middleware（中间件）

### 🔄 [请求生命周期](request-lifecycle.md) 🆕
- 请求创建
- 中间件处理
- 下载执行
- 响应解析
- 数据输出

### 🕷️ [爬虫生命周期](spider-lifecycle.md) 🆕
- 爬虫初始化
- 打开爬虫
- 爬取执行
- 关闭爬虫

### 🔗 [中间件链](middleware-chain.md) 🆕
- 中间件类型
- 执行顺序
- 优先级设置

### ❌ [错误处理机制](error-handling.md) 🆕
- 异常分类
- 重试机制
- 降级策略

### 💾 [检查点系统](checkpoint-guide.md)
- 检查点原理
- 断点续爬
- 状态恢复

### 🔑 [Redis Key 说明](redis-keys.md) 🆕
- 分布式模式下所有 Redis Key 的用途
- Key 类型、数据格式、所属模块

## 🎯 学习建议

这些概念是理解 Crawlo 框架的基础，建议：

1. **先了解架构** - 阅读[架构设计](architecture.md)了解整体
2. **理解组件** - 学习[核心组件](core-components.md)的作用
3. **深入机制** - 根据需求深入各个生命周期和机制

## 🔗 相关资源

- 📚 [教程系列](../tutorials/) - 实践学习
- 🎯 [使用指南](../guides/) - 解决具体问题
- 🔧 [API参考](../reference/) - 技术文档

---

**想深入了解 Crawlo？** → [架构设计](architecture.md)
