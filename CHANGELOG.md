# Crawlo Changelog

本项目遵循 [Semantic Versioning](https://semver.org/lang/zh-CN/)。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)：
每个版本必须包含 `## [x.y.z] - YYYY-MM-DD` 条目；未发布的变更放在 `## [Unreleased]`。

## [Unreleased]

### 工程化（P0 稳定化路线图）

- API 面冻结：新增 `docs/reference/api-surface.md`（454 个公共符号 100% 覆盖审计）
- Deprecation 周期治理：`filterwarnings = error::DeprecationWarning` 全局强制；
  框架内部 40+ 处旧路径引用迁移到新路径；修复 `crawlo.bot` 子模块身份分裂
  （旧路径导入的类对象与新路径不一致）
- 兼容性守护扩展：签名守护从 5 个核心类扩展到 57 类 / 471 个方法；
  新增 import-path 兼容矩阵测试（97 个模块路径 + 34 组顶层符号 + shim 迁移等价）
- 发布纪律：新增 `crawlo release --dry-run` 发布就绪检查（semver + CHANGELOG +
  发布说明 + git tag）+ CHANGELOG.md + CI release-check 门禁
- 插件机制（P1）：`crawlo.plugin` 统一注册表——`register_middleware` /
  `register_pipeline` / `register_extension` + 双通道配置（短名称 / 字符串路径）；
  官方示例 `examples/plugin_hello_world/` + 开发指南
- 生产示例（P2）：`examples/real_world_catalog/` 整站抓取 cookbook
  （分页→详情→去重→JSONL/MySQL 存储→监控→分布式）+ 教程 + CI 冒烟测试

### 修复

- `HttpXDownloader` 改用 Cookie header 合并，消除 httpx 0.28+ per-request
  cookies 废弃警告（DeprecationWarning 全局 error 下会中断爬取）
- `reset_global_context()` 同步重置 CoreInitializer 单例：修复 settings
  缓存跨测试/跨项目泄漏（上一个项目的 SPIDER_MODULES 等配置被后续项目继承）
- `CoreInitializer.initialize()` 增加防御：全局 initializer 注册表被清空
  （如测试替换为空实例）时自动注册内置 initializer，避免阶段执行静默跳过
  导致返回空 settings
- 修复 redis-py 5.x 废弃 `close()` → `aclose()` 迁移（stream/priority/filter/pool/cluster/pipeline）

### 修复

- `BackpressureableQueueMixin.__init__` 正确初始化 `_stats/_name/_max_size`
  （修复 DiskQueue 实例化报错）
- 调度日志：`Filtered duplicate request` 降为 debug，关闭时打印汇总条数
- Redis Stream 死信升级时不再丢失已投递消息；补回 `_SEED_LOCK_LUA`

## [1.7.3] - 2026-08-09

### 架构重构

- 包结构重组：`extension/` → `extensions/`、`factories/` → `core/`、
  `scheduling/` → `commands/`、`config/` → `core/config/`、
  `exceptions/interfaces/db/helpers/network/shell` 分散到各领域
- 初始化系统子包化：`application.py` → `core/initialization/`，
  23 个符号通过 PEP 562 延迟 re-export 保持 100% 向后兼容
- 引擎拆分：Engine / Processor / Scheduler 组件化，中间件链统一继承

### 修复

- 分布式模式下多个关键缺陷（死信、协调器、队列）
- SqliteStorage 并发锁竞争

### 兼容性

- 包结构重组部分不保证向后兼容（见 `docs/releases/v1.7.3.md` 迁移指南）
- 初始化系统子包化部分 100% 向后兼容

## [1.7.2] - 2026-07-15

### 新增

- 分布式协调（Worker 注册、心跳、故障转移、进度聚合）
- Redis Stream 队列 + 死信机制
- 自适应选择器与 Cloudflare 绕过中间件

### 修复

- 连接池与资源生命周期管理
- 编码检测与响应解析
