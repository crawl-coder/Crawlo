# Crawlo Changelog

本项目遵循 [Semantic Versioning](https://semver.org/lang/zh-CN/)。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)：
每个版本必须包含 `## [x.y.z] - YYYY-MM-DD` 条目；未发布的变更放在 `## [Unreleased]`。

## [Unreleased]（1.7.5 候选）

### Added

- 代理动态模式成本控制：新增 `PROXY_API_TTL`（默认 0 保持逐请求拉取）；
  >0 时缓存 API 结果并合并并发拉取（单飞防惊群），失败不缓存，
  缓存代理被拉黑仍走直连降级兜底
- `crawlo dead-letter replay`：死信定时重放子命令
  （`--max-per-round` / `--interval` 循环 / `--rounds` 上限；默认单轮），
  重放回主 Stream、retry_count 归零、剥离死信元数据，不重复入队
- 稳定性报告模板与短跑实测数据（`docs/releases/stability-report.md`）；
  基准脚本新增 `--distributed` 与 Redis ops/request 指标
  （本地冒烟基线 20.5 ops/request）

### Changed

- `RETRY_PRIORITY` 符号修正（1.7.4 复查发现）：原对已取反内部值做加法，
  默认 -100 实际把 NORMAL 重试升级为等效 HIGH；现作用于**用户优先级标度**
  （负数=降低），并如实注明 legacy 模式下重试内存递归不重新入队、该值暂不被
  队列消费；完整生效路径计划于 1.8.0 `RETRY_QUEUE_MODE=requeue`
  （见 [DEPRECATION.md](docs/reference/DEPRECATION.md)）
- 新增符号语义回归测试（5 项）与 DLQ 重放集成测试（7 项）、
  代理缓存单测（7 项）

## [1.7.4] - 2026-08-10

### Breaking Changes

> 版本策略：1.0 前允许在 patch 版本包含刻意 breaking（即以下两条），
> 以 CHANGELOG 记录 + 迁移指南补偿；自 1.0 起严格执行 SemVer。

- 移除 `crawlo.bot` 兼容存根包（含 channels/core/monitoring/templates/utils
  子包）：旧路径 `from crawlo.bot import ...` 将抛 ModuleNotFoundError，
  请迁移到 `crawlo.extensions.notifications.*`。属刻意提前的 breaking change
  （原计划 v2.0 移除）。

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
- 默认配置友好（P3）：`examples/simple_quickstart/`（23 行 spider +
  12 行管道，与全部示例同网站 ee.ofweek.com）+ `when-to-use.md` 场景决策树
- 稳定性与生产验证（P4）：`scripts/stress_run.py`（长跑压测 + 泄漏斜率）、
  `scripts/redis_ha/`（Sentinel 故障切换演练）、`scripts/failure_inject.py`
  （故障注入）、`docs/deployment/redis-ha.md`（部署与演练指南）
- 可观测性改进：`queue/pending_count` 暴露为 Prometheus 指标
  （`crawlo_queue_pending_count` Gauge），消费积压不再因闲置而消失
- 分布式投递语义文档化：新增 at-least-once 章节
  （重复投递场景 + 幂等保障建议）
- 日志轮转：`LOG_FILE` 默认改为固定文件名（模板），底层切换为
  `TimedRotatingFileHandler`（按天轮转 + `LOG_FILE_BACKUP_COUNT` 限制），
  `LOG_RETENTION_DAYS` 1 → 7；新增 `LOG_FILE_WHEN` / `LOG_FILE_BACKUP_COUNT` /
  `LOG_FILE_UTF8_BACKUP` 配置项；新增 `SafeTimedRotatingFileHandler`
  解决 Windows 下轮转重命名静默失败（告警 + 不崩溃 + flush 不丢日志）；
  新增 `LOG_FILE_WORKER_ID`：分布式集群初始化后自动把 worker_id 追加进
  日志文件名（`LogManager.set_file_path` 动态重建 handler），
  多机/多进程场景各 Worker 日志可区分；**默认开启并跟随运行模式**
  （切 `CrawloConfig.distributed()` 即自动生效，单机无副作用，显式设
  False 可关闭）

### 修复

- 请求去重指纹默认仅 method + 规范化 URL + body（headers/meta 不再参与）：
  修复随机 UA、按请求变化的 Cookie 或 download_slot 不同导致同一 URL
  去重失效（重复抓取 / 翻页死循环）；新增 `DUPEFILTER_INCLUDE_HEADERS` /
  `DUPEFILTER_INCLUDE_META` 可显式纳入指定字段
- Spider 回调直接 `return {...}` / `yield {...}` 统一包装为 `Item`：
  修复 dict 输出被静默丢弃（仅 WARNING）或抛 `OutputError` 的数据丢失问题
- `HttpXDownloader` 改用 Cookie header 合并，消除 httpx 0.28+ per-request
  cookies 废弃警告（DeprecationWarning 全局 error 下会中断爬取）
- `reset_global_context()` 同步重置 CoreInitializer 单例：修复 settings
  缓存跨测试/跨项目泄漏（上一个项目的 SPIDER_MODULES 等配置被后续项目继承）
- `CoreInitializer.initialize()` 增加防御：全局 initializer 注册表被清空
  （如测试替换为空实例）时自动注册内置 initializer，避免阶段执行静默跳过
  导致返回空 settings
- 修复 redis-py 5.x 废弃 `close()` → `aclose()` 迁移（stream/priority/filter/pool/cluster/pipeline）
- `BackpressureableQueueMixin.__init__` 正确初始化 `_stats/_name/_max_size`
  （修复 DiskQueue 实例化报错）
- 调度日志：`Filtered duplicate request` 降为 debug，关闭时打印汇总条数
- Redis Stream 死信升级时不再丢失已投递消息；补回 `_SEED_LOCK_LUA`
- `genspider` 模板修复：item_class 解析过滤导入类、parse 改为 yield Item 对象
  （生成的爬虫可直接运行）

### 修复（代理中间件 ProxyMiddleware 收口，dev/V1.7.4_PLAN.md M2）

- **降级重试不再被去重静默吞掉**：代理失败触发降级时，重试副本携带
  `dont_filter=True` + 防环计数——修复"代理失败自动降级/切换后重试"
  因调度器指纹去重被静默过滤而实际不生效的问题
- **失败代理 TTL 自动恢复**：新增 `PROXY_FAILED_TTL`（默认 300 秒），
  拉黑代理到期自动恢复可选；修复静态池全部拉黑后永久死亡、只能重启的问题
- **动态模式跳过已知失败代理**：API 返回拉黑中的代理时不再"warn 后照用"，
  本轮直连并计入 `proxy/direct_downgrade` 指标
- **失败归因收窄**：仅连接类异常（与 RetryMiddleware 可重试异常同源 +
  OSError）及 403/407/429 响应计入代理失败；目标站故障不再误拉黑健康代理，
  IP 被识别信号不再被当作成功清零计数
- **日志凭据脱敏**：所有代理日志经 mask 输出（`http://***:***@host:port`），
  不再泄漏 user:pass
- **直连降级可观测**：写入 stats `proxy/direct_downgrade`（Prometheus 自动
  映射 `crawlo_proxy_direct_downgrade_total`），纳入监控告警指标清单

### 文档

- 代理配置文档一致性收口（对照源码逐键核查）：删除未实现的
  `PROXY_ENABLED` / `PROXY_WHITELIST` / `PROXY_SWITCH_THRESHOLD` /
  `PROXY_MODE` / `PROXY_API_PARAMS` / `BROWSER_PROXY` 及 jsonpath、
  自定义函数提取器说明；补充"必须在 MIDDLEWARES 注册 ProxyMiddleware"
  前置条件；修正 `meta={'proxy': ...}` 示例为 `Request(proxy=...)`；
  socks5 支持声明收敛为仅 curl-cffi 下载器；项目模板同步清理死配置；
  新增 arch 守护测试（docs 中 PROXY_* 键必须有源码读取点 + 幻影键禁复活）
- 中间件优先级语义修正：文档/注释统一为实际执行序（请求阶段按优先级
  数值降序执行、响应阶段升序），新增执行序契约守护测试锁定
- 请求优先级体系澄清：修正 `Request.__init__` docstring 与
  `RequestPriority` 的档位方向矛盾；补充分布式双档 Stream 映射说明；
  新增中间件插入位置对照表与响应阶段互锁警告
- `RETRY_PRIORITY` 语义修复：原实现对"已取反的内部值"做加法，默认 -100
  实际把 NORMAL 重试升级为等效 HIGH（方向与注释相反）。现改为作用于
  用户优先级标度（负数=降低），并在注释中如实说明：重试默认由
  MiddlewareManager 内存递归重新下载、不重新入队，该值仅在副本被再次
  调度时被队列消费；新增符号语义回归测试

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
