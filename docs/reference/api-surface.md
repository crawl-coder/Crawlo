# Crawlo 公共 API 面（API Surface）

> 本文档是 1.0 稳定化的**唯一权威 API 清单**（Single Source of Truth）。
> 基线日期：2026-08-10（P0-A1 首次盘点）。后续 PR 触碰本清单内任何 frozen 符号，
> 必须同步更新本文档，否则 CI 兼容性测试会拦截。

## 1. 状态定义

| 状态 | 含义 | 变更规则 |
|---|---|---|
| `frozen` | 1.0 之前**不可改名、不可删除、不可改签名** | 必须走 Deprecation 周期（见 DEPRECATION.md），至少 2 个 minor |
| `experimental` | 可小幅调整，但需 DeprecationWarning | 调整前更新本文档并记录 |
| `internal` | 下划线开头或仅供框架内部使用 | 不承诺兼容性，用户不应依赖 |
| `optional` | 依赖可选库（Playwright / asyncmy / pymongo 等）才可用 | 缺依赖时导入返回 `None` 或抛 ImportError，行为本身 frozen |

默认规则：**凡出现在本文档的符号，一律视为 `frozen`**，除非显式标注 `experimental`。

## 2. 顶层导出 `crawlo.*`

`from crawlo import ...` 可直接使用的全部符号（PEP 562 延迟导入，行为 frozen）：

| 符号 | 类型 | 状态 | 实际来源 |
|---|---|---|---|
| `Crawler` | 类 | frozen | `crawlo.crawler.Crawler` |
| `CrawlerProcess` | 类 | frozen | `crawlo.crawler.CrawlerProcess` |
| `CrawloFramework` | 类 | frozen | `crawlo.crawler.CrawloFramework` |
| `Spider` | 类 | frozen | `crawlo.spider.Spider` |
| `Item` / `Field` | 类 | frozen | `crawlo.items` |
| `Request` / `Response` | 类 | frozen | `crawlo.http` |
| `DownloaderBase` | 类 | frozen | `crawlo.downloader` |
| `BaseMiddleware` | 类 | frozen | `crawlo.middleware` |
| `Failure` | 类 | frozen | `crawlo.core.errors` |
| `run_spider` / `run_spiders` | 函数 | frozen | `crawlo.crawler` |
| `create_crawler` / `configure_framework` | 函数 | frozen | `crawlo.crawler` |
| `get_framework` / `reset_framework` | 函数 | frozen | `crawlo.crawler` |
| `get_framework_initializer` / `initialize_framework` | 函数 | frozen | `crawlo.core` |
| `cleaners` / `helpers` | 模块别名 | frozen | `crawlo.utils` |
| `TimeUtils` 及 `parse_time` / `format_time` / `time_diff` / `to_timestamp` / `to_datetime` / `now` / `to_timezone` / `to_utc` / `to_local` / `from_timestamp_with_tz` | 类/函数 | frozen | `crawlo.utils.time_utils` |
| `__version__` | 字符串 | frozen | `crawlo.__version__` |

## 3. 核心组件（`crawlo.core`）

### 3.1 Engine 引擎

`crawlo.core.engine.Engine` —— 爬取执行引擎，签名由 `tests/arch/test_public_api_signatures.py` 哈希守护。

- `__init__` / `engine_start` / `start_spider` / `crawl` / `enqueue_request` / `close_spider` / `get_generation_stats`

### 3.2 ApplicationContext 应用上下文

`crawlo.core.application.ApplicationContext` —— 组合式容器（runtime / spider / resource）。

- `register_spider` / `get_spider` / `unregister_spider` / `add_resource` / `remove_resource` / `cleanup`

### 3.3 Processor 处理器

`crawlo.core.processor.Processor` —— 响应处理流水线。

- `open` / `start` / `stop` / `enqueue` / `process_once` / `idle_async` / `close` / `get_stats`

### 3.4 调度

`crawlo.core.scheduling.Scheduler`（`crawlo.core.scheduling.task_scheduler`）：

- `queue_type` / `create_instance` / `open` / `next_request` / `next_request_blocking` / `enqueue_request` / `async_idle` / `async_size` / `close` / `next_request_with_ack` / `ack_request` / `nack_request`

`crawlo.core.scheduling.TaskManager` —— 定时任务调度器（experimental，v0.x 演进中）。

`crawlo.core.scheduling` 模块导出（frozen）：`Scheduler` / `TaskManager`。

### 3.5 初始化系统（`crawlo.core.initialization`）

| 符号 | 状态 | 说明 |
|---|---|---|
| `initialize_framework` / `is_framework_ready` / `get_framework_context` | frozen | 框架初始化主入口 |
| `CoreInitializer` | frozen | 初始化器实现 |
| `Initializer` / `BaseInitializer` / `InitializerRegistry` | frozen | 插件初始化扩展点 |
| `register_initializer` / `register_phase_function` / `get_global_registry` | frozen | 注册 API |
| `InitializationPhase` / `PhaseDefinition` / `PhaseResult` / `PHASE_DEFINITIONS` | frozen | 阶段模型 |
| `InitializationContext` / `InitializationTimer` / `create_initialization_result` | frozen | 上下文与工具 |
| `get_phase_definition` / `get_execution_order` / `validate_dependencies` / `detect_circular_dependencies` / `validate_phase_dependencies` | frozen | 阶段工具 |
| `LoggingInitializer` / `SettingsInitializer` / `CoreComponentsInitializer` / `ExtensionsInitializer` / `FrameworkStartupLogger` / `register_built_in_initializers` | internal | 内置初始化器 |

### 3.6 配置（`crawlo.core.config`）

| 符号 | 状态 | 说明 |
|---|---|---|
| `CrawloConfig` | frozen | 配置对象 |
| `RunMode` | frozen | standalone / distributed / auto 枚举 |
| `BASE_CONFIG` / `MODE_CONFIG_MAP` | frozen | 默认配置与模式映射 |
| `ConfigValidator` | frozen | 配置校验 |
| `create_config` / `validate_config` / `standalone_mode` / `distributed_mode` / `auto_mode` / `from_env` | frozen | 便捷工厂 |
| `_make_standalone` / `_make_distributed` / `_make_auto` / `_make_from_env` | internal | 内部实现 |

### 3.7 其他核心公开符号

| 符号 | 状态 | 说明 |
|---|---|---|
| `crawlo.event.CrawlerEvent` | frozen | 事件枚举（SPIDER_OPENED / SPIDER_CLOSED / REQUEST_SCHEDULED / RESPONSE_RECEIVED / ITEM_SUCCESSFUL / ITEM_DISCARD 等） |
| `crawlo.event.Subscriber` / `NotifyResult` / `CRITICAL_EVENTS` | frozen | 发布/订阅 |
| `crawlo.core.errors.Failure` / `ErrorContext` / `DetailedException` | frozen | 异常体系（详见 `docs/reference/api/index.md`） |
| `crawlo.core.component_base` / `component_registry` / `factories` / `interfaces` | experimental | 组件基类与工厂（内部迁移中，1.0 前收口） |
| `crawlo.core.get_framework_logger(name)` | frozen | 框架日志便捷函数 |

## 4. 爬虫与请求（`crawlo.spider` / `crawlo.http` / `crawlo.items`）

### 4.1 Spider（`crawlo.spider`）

| 符号 | 状态 |
|---|---|
| `Spider` / `SpiderMeta` | frozen |
| `SpiderStatsTracker` / `SpiderDiscoveryState` | frozen |
| `SpiderLoader` / `SpiderResolver` | frozen |
| `create_spider_from_template` | frozen |
| `get_global_spider_registry` / `get_spider_by_name` / `get_all_spider_classes` / `get_spider_names` / `is_spider_registered` / `unregister_spider` / `reset_spider_registry` | frozen |

### 4.2 HTTP 对象（`crawlo.http`）

| 符号 | 状态 | 说明 |
|---|---|---|
| `Request` | frozen | 请求对象（url / method / headers / body / meta / callback / priority / depth / dont_filter 等） |
| `Response` | frozen | 响应对象（css / xpath / json / text / follow / urljoin 等） |
| `RequestPriority` | frozen | 优先级常量 |

### 4.3 Item（`crawlo.items`）

| 符号 | 状态 |
|---|---|
| `Item` / `Field` / `ItemMeta` | frozen |
| `ItemInitError` / `ItemAttributeError` | frozen |

## 5. 下载器（`crawlo.downloader`）

### 5.1 基类与注册 API

| 符号 | 状态 | 说明 |
|---|---|---|
| `DownloaderBase` | frozen | 下载器 ABC：`create_instance` / `open` / `fetch` / `download` / `close` / `idle` / `get_stats` / `health_check` |
| `ActivateRequestManager` | frozen | 活跃请求管理器 |
| `register_downloader(name, cls)` | frozen | 插件注册 API（P3 已落地） |
| `unregister_downloader(name)` | frozen | 注销 API |
| `get_downloader_class(name)` / `DOWNLOADER_MAP` | frozen | 名称→类解析 |

### 5.2 内置下载器

| 符号 | 状态 | 依赖 |
|---|---|---|
| `AioHttpDownloader` | frozen | aiohttp |
| `HttpXDownloader` | frozen | httpx |
| `CurlCffiDownloader` | frozen | curl_cffi |
| `HybridDownloader` | frozen | 多下载器组合 |
| `PlaywrightDownloader` | optional | playwright |
| `DrissionPageDownloader` | optional | drissionpage |
| `CloakBrowserDownloader` | optional | cloakbrowser |
| `CamoufoxDownloader` | optional | camoufox |

设置键：`DOWNLOADER`（默认 `crawlo.downloader.HybridDownloader`），短名称见 `DOWNLOADER_MAP`。

## 6. 中间件（`crawlo.middleware`）

### 6.1 基类与注册

- `BaseMiddleware`（frozen）：`process_request` / `process_response` / `process_exception` / `create_instance`
- `MiddlewareManager`（frozen）：`create_instance` / `download`（中间件链入口）
- `MiddlewarePriority` / `MiddlewarePriorityGroup` / `BUILTIN_MIDDLEWARE_PRIORITIES` / `get_default_middleware_priority`（frozen，经 `crawlo.utils` 亦可导入）

> **P1-B1 待办**：`register_middleware` 尚未落地（2026-08-10 盘点时缺失），见 ROADMAP P1。

### 6.2 内置中间件

| 符号 | 状态 | 职责 |
|---|---|---|
| `RequestIgnoreMiddleware` | frozen | 请求忽略 |
| `DownloadDelayMiddleware` | frozen | 下载延迟/随机化 |
| `DefaultHeaderMiddleware` | frozen | 默认请求头 |
| `DynamicRenderMiddleware` | frozen | 动态渲染分流 |
| `CloudflareBypassMiddleware` | frozen | CF 绕过链 |
| `OffsiteMiddleware` | frozen | 域名白名单 |
| `ProxyMiddleware` | frozen | 静态/动态代理 |
| `RetryMiddleware` | frozen | 重试 |
| `ResponseCodeMiddleware` | frozen | 状态码处理 |
| `ResponseFilterMiddleware` | frozen | 响应过滤 |
| `FileMiddleware` | frozen | 文件下载 |

设置键：`MIDDLEWARES`（有序 dict：类路径 → 优先级）。

## 7. 管道（`crawlo.pipelines`）

### 7.1 基类

- `BasePipeline` / `ResourceManagedPipeline` / `FileBasedPipeline`（frozen）
- `GenericSQLPipeline` / `GenericDocumentPipeline`（frozen）

### 7.2 内置管道

| 符号 | 状态 | 依赖 |
|---|---|---|
| `ConsolePipeline` | frozen | 无 |
| `CsvPipeline` / `CsvDictPipeline` / `JsonLinesPipeline` / `JsonArrayPipeline` / `JsonPipeline`（别名） | frozen | 无 |
| `MemoryDedupPipeline` / `RedisDedupPipeline` | frozen | Redis 版需 redis |
| `MySQLPipeline` / `SQLitePipeline` / `PostgreSQLPipeline` / `ClickHousePipeline` | optional | asyncmy / aiosqlite / asyncpg / clickhouse-connect |
| `MongoPipeline` / `ElasticsearchPipeline` | optional | pymongo / elasticsearch |
| `HBasePipeline` | optional | happybase |
| `BloomDedupPipeline` / `MySQLDedupPipeline` / `DatabaseDedupPipeline` | optional | 依赖对应存储 |

> 延迟加载语义（frozen）：缺依赖时 `from crawlo.pipelines import MySQLPipeline` 抛 ImportError；显式依赖安装后行为不变。

设置键：`PIPELINES`（有序 dict：类路径 → 优先级）。

## 8. 队列（`crawlo.queue`）

### 8.1 管理入口

- `QueueManager`（frozen）：`initialize` / `put` / `get` / `get_blocking` / `size` / `max_size` / `async_empty` / `close` / `get_status` / `get_queue_stats`
- `register_queue_backend(name, backend_cls)` / `unregister_queue_backend(name)`（frozen，P3 落地）
- `QueueConfig` / `QueueType`（frozen）

### 8.2 后端

| 符号 | 状态 | 说明 |
|---|---|---|
| `SpiderPriorityQueue` | frozen | 内存优先级队列 |
| `DiskQueue` | frozen | 磁盘持久化队列 |
| `RedisPriorityQueue` | frozen | Redis ZSET 优先级队列 |
| `RedisStreamQueue` | frozen | Redis Stream 队列（支持 cluster 轮询回退） |

### 8.3 背压（`crawlo.queue.backpressure`）

| 符号 | 状态 |
|---|---|
| `BackpressureController` / `PressureLevel` / `BackpressureMetrics` / `IBackpressureStrategy` / `BackpressureStrategyConfig` | frozen |
| `QueueSizeStrategy` / `AdaptiveStrategy` / `CompositeStrategy` | frozen |
| `BackpressureMetricsCollector` / `QueueMetrics` / `IntelligentBackpressureCalculator` / `BackpressureMonitor` | frozen |

### 8.4 任务追踪

- `TaskTracker` / `TaskResult`（frozen，`crawlo.queue.task_tracker`）

## 9. 去重过滤（`crawlo.filters`）

| 符号 | 状态 | 说明 |
|---|---|---|
| `BaseFilter` | frozen | `requested` / `add_fingerprint` / `__contains__` / `get_stats` |
| `MemoryFilter` / `MemoryFileFilter` | frozen | 单机去重 |
| `AioRedisFilter` | optional | Redis 分布式去重 |
| `FILTER_MAP` / `get_filter_class(name)` | frozen | 名称→类解析 |

设置键：`FILTER_CLASS`（默认 `crawlo.filters.MemoryFilter`）。

## 10. 统计（`crawlo.stats`）

| 符号 | 状态 | 说明 |
|---|---|---|
| `StatsCollector` | frozen | 收集器：`inc_value` / `set_value` / `get_stats` 等 |
| `StatsBackend` / `MemoryStatsBackend` / `RedisStatsBackend` / `FileStatsBackend` | frozen | 后端抽象与实现 |
| `StatsBackendFactory` | frozen | 工厂 |
| `PrometheusStatsBackend` | optional | 需 `crawlo[monitoring]` |

设置键：`STATS_BACKEND` / `STATS_DUMP` / `PROMETHEUS_*`。

## 11. 扩展（`crawlo.extensions`）

| 符号 | 状态 | 说明 |
|---|---|---|
| `ExtensionManager` | frozen | 扩展管理器（按 `EXTENSIONS` 设置加载） |
| `LogIntervalExtension` / `LogStats` / `CustomLoggerExtension` / `HealthCheckExtension` / `RequestRecorderExtension` / `EventloopLagProbe` | frozen | 内置扩展 |
| `MemoryMonitorExtension` / `MySQLMonitorExtension` / `RedisMonitorExtension` | frozen | 监控扩展 |

### 11.1 通知系统（`crawlo.extensions.notifications`，原 `crawlo.bot`）

| 符号 | 状态 | 说明 |
|---|---|---|
| `NotificationMessage` / `NotificationResponse` / `ChannelResponse` / `ChannelType` / `NotificationType` | frozen | 数据模型 |
| `NotificationDispatcher` / `get_notifier` | frozen | 分发器 |
| `CrawlerNotificationHandler` / `get_notification_handler` | frozen | 爬虫事件处理器 |
| `send_crawler_status` / `send_crawler_alert` / `send_crawler_progress` / `send_template_notification` / `list_notification_templates` / `add_custom_notification_template` | frozen | 同步便捷函数 |
| `async_send_crawler_status` / `async_send_crawler_alert` / `async_send_template_notification` | frozen | 异步便捷函数 |
| `MessageTemplateManager` / `get_template_manager` / `render_message` / `list_available_templates` / `get_template_parameters` / `COMMON_VARIABLES` | frozen | 模板系统 |
| `TemplateVariable` / `TemplateVar` / `TemplateName` / `Template` | frozen | 模板枚举 |
| `ResourceMonitorTemplateManager` / `get_resource_monitor_manager` / `render_resource_monitor_template` / `list_resource_monitor_templates` | frozen | 资源监控模板管理 |
| `ResourceTemplate` / `ResourceMonitorVariable` / `ResourceMonitorCategory` | frozen | 资源监控模板枚举 |
| `get_mysql_monitor_templates` / `get_redis_monitor_templates` / `get_mongodb_monitor_templates` / `get_resource_leak_monitor_templates` | frozen | 各资源类型模板函数 |
| `get_mysql_resource_templates` / `get_redis_resource_templates` / `get_mongodb_resource_templates` / `get_resource_leak_templates` | frozen | 各资源类型模板函数（别名） |
| `MessageDeduplicator` / `get_deduplicator` / `reset_deduplicator` / `apply_settings_config` / `ensure_config_loaded` | frozen | 去重与配置 |

渠道（`crawlo.extensions.notifications.channels`）：

| 符号 | 状态 |
|---|---|
| `NotificationChannel`（抽象基类） | frozen |
| `DingTalkChannel` / `FeishuChannel` / `WeComChannel` / `EmailChannel` / `SmsChannel` | frozen |
| `get_dingtalk_channel` / `get_feishu_channel` / `get_wecom_channel` / `get_email_channel` / `get_sms_channel` / `ALL_CHANNELS` | frozen |

设置键：`NOTIFICATION_ENABLED` / `NOTIFICATION_CHANNELS` / `DINGTALK_*` / `FEISHU_*` / `WECOM_*`。

## 12. 集群（`crawlo.cluster`）

| 符号 | 状态 | 说明 |
|---|---|---|
| `WorkerRegistry` | frozen | Worker 注册 |
| `HeartbeatDaemon` | frozen | 心跳 |
| `DistributedLock` | frozen | 分布式锁（含 leader fencing） |
| `FailoverManager` | frozen | 故障转移 |
| `ProgressAggregator` | frozen | 进度聚合 |
| `DistributedRateLimiter` | frozen | 分布式限流 |
| `ClusterMonitor` | frozen | 集群监控 |
| `DynamicConfig` | frozen | 动态配置 |
| `ClusterMessenger` | frozen | 消息通道 |
| `ClusterMixin` / `ClusterState` | frozen | Engine 分布式 Mixin 与状态 |
| `_ack_message` | internal | 内部函数 |

## 13. 检查点（`crawlo.checkpoint`）

- `CheckpointManager`（frozen）：保存/恢复断点，支持 json / sqlite 后端。

设置键：`CHECKPOINT_ENABLED` / `CHECKPOINT_STORAGE` / `CHECKPOINT_DIR` / `CHECKPOINT_SAVE_ON_SIGNAL`。

## 14. 日志（`crawlo.logging`）

| 符号 | 状态 |
|---|---|
| `get_logger(name)` | frozen |
| `configure_logging(settings, **kwargs)` | frozen |
| `is_configured()` | frozen |
| `LogManager` / `LoggerFactory` / `LogConfig` | frozen |

## 15. MCP（`crawlo.mcp`）

| 符号 | 状态 | 说明 |
|---|---|---|
| `mcp` / `main` | frozen | FastMCP 实例与入口（`crawlo-mcp`） |
| `QuickFetcher` / `quick_fetch` / `FetchResult` | frozen | 快速抓取 API |

MCP 工具（`crawlo-mcp` 暴露，frozen）：

| 工具 | 签名摘要 |
|---|---|
| `fetch` | `(url, mode="basic", format="markdown", max_length=0, cookies=None, persist_session=True)` |
| `extract` | `(url, pattern, mode="basic", context_chars=150, cookies=None)` |
| `spider` | `(urls, mode="basic", format="markdown", concurrency=2, delay=0.0, cookies=None)` |
| `evaluate` | `(url, script, mode="stealth")` |
| `screenshot` | `(url, mode="stealth")` |
| `status` | `()` |

## 16. 工具库（`crawlo.utils`）

| 子包 | 符号 | 状态 |
|---|---|---|
| `crawlo.utils`（顶层） | `parse_cookies` / `regex_search` / `regex_findall` / `regex_findone` / `get_header_value` / `FingerprintGenerator` / `RequestSerializer` / `EncodingDetector` / `detect_encoding` / `decode_body` / `BatchProcessor` / `RedisBatchProcessor` / `batch_process` / `process_in_batches` / `MiddlewarePriority` 系列 | frozen |
| `crawlo.utils.text` | `TextCleaner` + 10 个文本清理函数 | frozen |
| `crawlo.utils.text`（完整符号） | `TextCleaner` / `remove_html_tags` / `decode_html_entities` / `remove_extra_whitespace` / `remove_special_chars` / `normalize_unicode` / `clean_text` / `extract_numbers` / `extract_emails` / `extract_urls` / `extract_phones` / `strip_control_chars` / `truncate` | frozen |
| `crawlo.utils.parsing` | `CurlParser` / `SelectorConverter` / `PageActionHandler` / `format_datetime` / `format_duration` / `get_time_until_next` | frozen |
| `crawlo.utils.db` | `MySQLHelper` / `get_mysql_helper` / `check_exists` / `SQLBuilder` / `MySQLConnectionPoolManager` / `get_mysql_pool` / `close_all_mysql_pools` / `is_pool_active` / `get_mysql_pool_stats` / `SQLDialect` / `MySQLDialect` / `PostgreSQLDialect` / `SQLiteDialect` / `ClickHouseDialect` / `BasePoolManager` / `MySQLExistsChecker` | frozen（MySQL 相关 optional） |
| `crawlo.utils.redis` | `RedisConfig` / `generate_redis_url` / `parse_redis_url` / `create_redis_config` / `redis_url_to_config` / `config_to_redis_url` / `RedisConnectionPool` / `get_redis_pool` / `close_all_pools` / `CrawloRedisManager` / `get_isolated_redis_pool` / `get_redis_manager` / `RedisKeyManager` / `RedisKeyValidator` / `validate_redis_key_naming` / `validate_multiple_redis_keys` / `get_redis_key_info` / `print_validation_report` / `create_redis_key_manager` / `get_redis_key_manager_from_settings` | frozen |
| `crawlo.utils.concurrency` | `AsyncRLock` / `AsyncLock` / `AsyncSemaphore` / `AsyncEvent` / `AsyncCondition` / `apply_windows_patches` / `run_with_cleanup` / `ProcessSignalHandler` / `SpiderDiscoveryUtils` / `SettingsUtils` | frozen |
| `crawlo.utils.adaptive_selector` | `ElementFingerprint` / `SimilarityMatcher` / `FingerprintStorage` / `SqliteStorage` / `RedisStorage` | frozen |
| `crawlo.utils.encoding` | `EncodingDetector` / `detect_encoding` / `decode_body` | frozen |
| `crawlo.utils.request` | `set_request` / `request_to_dict` / `request_from_dict` / `FingerprintGenerator` / `parse_cookies` / `regex_search` / `regex_findall` / `regex_findone` / `get_header_value` | frozen |
| `crawlo.utils.errors` | `ErrorHandler` / `handle_exception` / `_get_global_error_handler` / `ErrorContext` / `DetailedException` | frozen（`_get_global_error_handler` 为 internal） |
| `crawlo.utils._compat` | `HAS_SUBINTERPRETERS` / `InterpreterPoolExecutor` / `get_executor` / `get_task_info` / `render_template` | internal（Python 版本兼容层，不承诺） |

`crawlo.settings` 模块（frozen，配置加载）：`default_settings`（默认值字典）/ `setting_manager`（`EnvConfigManager`）。

## 17. 设置项（settings keys）

完整清单见 `crawlo/settings/default_settings.py`（盘点基线：**344 个设置键**）。

本文档不逐一复制，但以下分组的**命名与语义**属于 frozen：

| 分组 | 前缀/示例 | 说明 |
|---|---|---|
| 爬虫与加载 | `SPIDER_MODULES` / `SPIDER_LOADER_WARN_ONLY` | 爬虫发现 |
| 下载器 | `DOWNLOADER` / `DOWNLOAD_TIMEOUT` / `VERIFY_SSL` / `CONNECTION_POOL_*` / `DOWNLOAD_MAXSIZE` / `DOWNLOAD_STATS` | 下载行为 |
| 调度与并发 | `CONCURRENCY` / `DOWNLOAD_DELAY` / `RANDOMNESS` / `RANDOM_RANGE` / `DEPTH_PRIORITY` / `SCHEDULER_MAX_QUEUE_SIZE` 系列 | 调度 |
| 背压 | `BACKPRESSURE_*` / `MEMORY_BACKPRESSURE_*` / `REDIS_BACKPRESSURE_*` | 背压策略 |
| 队列 | `QUEUE_TYPE` / `QUEUE_MAX_RETRIES` / `QUEUE_TIMEOUT` / `QUEUE_SERIALIZATION_FORMAT` / `STREAM_*` / `ENQUEUE_*` | 队列后端 |
| Redis/分布式 | `REDIS_*` / `REDIS_SENTINEL_*` / `REDIS_CLUSTER_*` / `DISTRIBUTED_*` / `CLUSTER_*` / `PROGRESS_REPORT_INTERVAL` | 分布式 |
| 重试 | `MAX_RETRY_TIMES` / `RETRY_*` / `IGNORE_HTTP_CODES` | 重试语义 |
| 浏览器 | `BROWSER_*` / `PLAYWRIGHT_*` / `DRISSIONPAGE_*` / `CAMOUFOX_*` / `CLOAKBROWSER_*` | 动态渲染 |
| 中间件/管道 | `MIDDLEWARES` / `PIPELINES` / `FILTER_CLASS` / `DEFAULT_DEDUP_PIPELINE` / `PROXY_*` / `ALLOWED_DOMAINS` / `DYNAMIC_RENDER_*` / `CLOUDFLARE_BYPASS_*` | 组件装配 |
| 存储 | `MYSQL_*` / `SQLITE_*` / `PG_*` / `CLICKHOUSE_*` / `MONGO_*` / `ELASTICSEARCH_*` / `HBASE_*` / `CSV_*` / `JSON_*` / `DB_*` / `BLOOM_*` | 管道存储 |
| 扩展/监控 | `EXTENSIONS` / `HEALTH_CHECK_*` / `LOG_*` / `STATS_*` / `PROMETHEUS_*` / `INTERVAL` / `MEMORY_MONITOR_*` / `MYSQL_MONITOR_*` / `REDIS_MONITOR_*` / `EVENTLOOP_LAG_*` | 运维 |
| 通知 | `NOTIFICATION_*` / `DINGTALK_*` / `FEISHU_*` / `WECOM_*` | 通知 |
| 调度器 | `SCHEDULER_*` | 定时任务 |
| 自适应/检查点 | `ADAPTIVE_*` / `CHECKPOINT_*` | 高级能力 |

## 18. CLI（`crawlo <command>`）

| 命令 | 模块 | 状态 | 说明 |
|---|---|---|---|
| `crawlo startproject` | `crawlo.commands.startproject` | frozen | 创建项目（模板：default / simple / minimal） |
| `crawlo genspider` | `crawlo.commands.genspider` | frozen | 生成爬虫模板 |
| `crawlo run` | `crawlo.commands.run` | frozen | 运行爬虫（-L / -s / -a / --mode / --fresh / --clean-checkpoint） |
| `crawlo check` | `crawlo.commands.check` | frozen | 校验项目与依赖 |
| `crawlo list` | `crawlo.commands.list` | frozen | 列出爬虫 |
| `crawlo stats` | `crawlo.commands.stats` | frozen | 统计信息 |
| `crawlo shell` | `crawlo.commands.shell` | frozen | 交互式终端 |
| `crawlo schedule` | `crawlo.commands.schedule` | frozen | 定时任务入口 |
| `crawlo dead-letter` | `crawlo.commands.dead_letter` | frozen | 死信管理（list / retry / stats） |
| `crawlo cluster` | `crawlo.commands.cluster` | frozen | 集群管理（state / reset / pause / resume / shutdown） |
| `crawlo help` / `-h` / `--help` / `-v` / `--version` | `crawlo.cli` | frozen | 帮助与版本 |
| `crawlo-mcp` | `crawlo.mcp.server` | frozen | MCP Server（--host / --port / --transport） |

CLI 模块内部公共函数：`get_commands()`（frozen，命令注册表，插件可读取）。

## 19. 废弃兼容路径（deprecated shims）

以下路径**当前可用且必须保持可用直到移除计划执行**（见 DEPRECATION.md）：

| 旧路径 | 新路径 | 状态 |
|---|---|---|
| `crawlo.bot` 及其子包（channels / core / monitoring / templates / utils） | `crawlo.extensions.notifications.*` | deprecated，v2.0 前保留 |
| `crawlo.crawler_process` | `crawlo.crawler.CrawlerProcess` | deprecated |
| `crawlo.framework` | `crawlo.crawler.CrawloFramework` | deprecated |
| `crawlo.container` | `crawlo.core.application.ApplicationContext` | deprecated |
| `crawlo.crawler` 扁平模块（`crawlo/crawler.py`） | `crawlo.crawler` 子包 | deprecated（re-export，调用方无感） |

## 20. 覆盖统计（盘点基线 2026-08-10）

```text
顶层 crawlo.*            31 个符号
crawlo.crawler           14 个符号
核心组件（engine/context/processor/scheduler/init/config）  ≈ 60 个符号
下载器                   12 个符号（含 8 个实现 + 注册 API）
中间件                   13 个符号
管道                     13 个符号（直接导出）+ 10 个 optional
队列 + 背压 + 任务追踪   23 个符号
过滤 / 统计 / 日志       16 个符号
扩展 + 通知              58 个符号
集群                     12 个符号
检查点                    1 个符号
MCP                       5 个符号 + 6 个工具
工具库                   ≈ 90 个符号
设置键                  344 个
CLI                      12 个命令入口
```

> 覆盖目标：本文档应覆盖 ≥ 95% 公开符号（以各模块 `__all__` 为准）。
> 验收脚本（P0-A3）将遍历所有 `crawlo.*` 公共导出并与本文档比对。

## 21. 变更流程（frozen 符号触碰规则）

1. **改名/删除/签名变更**：先写 DEPRECATION.md 计划 → 发版宣布 → 至少 2 个 minor 后移除；
2. **新增符号**：允许，但必须补进本文档并标注状态；
3. **状态变更**（frozen ↔ experimental）：必须在本文件"变更记录"登记；
4. **任何 PR**：若触碰本文档符号，需同步更新 `tests/arch/test_public_api_signatures.py` 或新增守护测试。

## 22. 变更记录

| 日期 | 变更 | 说明 |
|---|---|---|
| 2026-08-10 | 首次盘点 | P0-A1 初稿：覆盖全部 `__all__` 导出 + CLI + MCP + settings + deprecated shims |
