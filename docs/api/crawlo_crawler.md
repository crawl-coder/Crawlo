# crawlo.crawler

Crawlo Crawler Module
====================
提供爬虫进程管理和运行时核心功能。

核心组件:
- Crawler: 单个爬虫运行实例，管理Spider与引擎的生命周期
- CrawlerProcess: 爬虫进程管理器，支持多爬虫并发调度和资源管理

功能特性:
- 智能并发控制和资源管理
- 优雅关闭和信号处理
- 统计监控和性能追踪
- 自动模块发现和注册
- 错误恢复和重试机制
- 大规模爬虫优化支持

示例用法:
    # 单个爬虫运行
    crawler = Crawler(MySpider, settings)
    await crawler.crawl()
    
    # 多爬虫并发管理
    process = CrawlerProcess()
    await process.crawl([Spider1, Spider2])

## 导入的类

- annotations
- Type
- Optional
- Set
- List
- Union
- Dict
- Any
- Spider
- get_global_spider_registry
- Engine
- get_logger
- Subscriber
- ExtensionManager
- StatsCollector
- spider_opened
- spider_closed
- SettingManager
- merge_settings
- get_settings

## 类

### CrawlerContext
爬虫上下文管理器
提供共享状态和资源管理

#### 方法

##### __init__

##### increment_total

##### increment_active

##### decrement_active

##### increment_completed

##### increment_failed

##### get_stats

### Crawler
单个爬虫运行实例，管理 Spider 与引擎的生命周期

提供功能:
- Spider 生命周期管理（初始化、运行、关闭）
- 引擎组件的协调管理
- 配置合并和验证
- 统计数据收集
- 扩展管理
- 异常处理和清理

#### 方法

##### __init__

##### _validate_crawler_state
验证爬虫状态和配置
确保所有必要组件都已正确初始化

##### _get_total_duration
获取总运行时间

##### get_performance_metrics
获取性能指标

##### _create_subscriber
创建事件订阅器

##### _create_spider
创建并验证爬虫实例（增强版）

执行以下验证:
- 爬虫名称必须存在
- start_requests 方法必须可调用
- start_urls 不能是字符串
- parse 方法建议存在

##### _create_engine
创建并初始化引擎

##### _create_stats
创建统计收集器

##### _create_extension
创建扩展管理器

##### _set_spider
设置爬虫配置和事件订阅
将爬虫的生命周期事件与订阅器绑定

### CrawlerProcess
爬虫进程管理器

支持功能:
- 多爬虫并发调度和资源管理
- 自动模块发现和爬虫注册
- 智能并发控制和负载均衡
- 优雅关闭和信号处理
- 实时状态监控和统计
- 错误恢复和重试机制
- 大规模爬虫优化支持

使用示例:
    # 基本用法
    process = CrawlerProcess()
    await process.crawl(MySpider)
    
    # 多爬虫并发
    await process.crawl([Spider1, Spider2, 'spider_name'])
    
    # 自定义并发数
    process = CrawlerProcess(max_concurrency=8)

#### 方法

##### __init__

##### auto_discover
自动导入模块，触发 Spider 类定义和注册（增强版）

支持递归扫描和错误恢复

##### get_spider_names
获取所有已注册的爬虫名称

##### get_spider_class
根据 name 获取爬虫类

##### is_spider_registered
检查某个 name 是否已注册

##### get_process_stats
获取进程统计信息

##### _resolve_spiders_to_run
解析输入为爬虫类列表

支持各种输入格式并验证唯一性

##### _normalize_inputs
标准化输入为列表

支持更多输入类型并提供更好的错误信息

##### _resolve_spider_class
解析单个输入项为爬虫类

提供更好的错误提示和调试信息

##### _shutdown
优雅关闭信号处理

提供更好的关闭体验和资源清理

##### _get_default_settings
加载默认配置

提供更好的错误处理和降级策略

## 函数

### create_crawler_with_optimizations
创建优化的爬虫实例

:param spider_cls: 爬虫类
:param settings: 设置管理器
:param optimization_kwargs: 优化参数
:return: 爬虫实例

### create_process_with_large_scale_config
创建支持大规模优化的进程管理器

:param config_type: 配置类型 ('conservative', 'balanced', 'aggressive', 'memory_optimized')
:param concurrency: 并发数
:param kwargs: 其他参数
:return: 进程管理器
