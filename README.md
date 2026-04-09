<p align="center">
  <img src="assets/logo.svg" alt="Crawlo Logo" width="150"/>
</p>

<h1 align="center">Crawlo</h1>

<p align="center">
  <strong>一个基于 asyncio 的现代化、高性能 Python 异步爬虫框架。</strong>
</p>

<p align="center">
  <a href="#核心特性">核心特性</a> •
  <a href="#项目架构">架构</a> •
  <a href="#安装">安装</a> •
  <a href="#配置模式详解">配置模式</a> •
  <a href="https://github.com/crawl-coder/Crawlo">文档</a>
</p>

## 核心特性

- 🚀 **高性能异步架构**：基于 asyncio 和 aiohttp，充分利用异步 I/O 提升爬取效率
- 🎯 **智能调度系统**：优先级队列、并发控制、自动重试、智能限速
- 🛡️ **强大的反反爬虫能力**：
  - **智能混合下载器 (HybridDownloader)**：根据请求特性、URL 正则模式或域名自动切换协议/浏览器引擎，实现性能与通过率的完美平衡
  - **Cloudflare 自动绕过**：内置多种绕过策略（403/503 检测、Turnstile 挑战识别），默认集成，无需复杂配置
  - **隐身浏览器集成**：支持 camoufox (最强反检测)、playwright、drissionpage，内置全链路指纹伪造 (Stealth Scripts)
  - **资源管理优化**：Playwright 页面池复用与信号量并发控制，彻底杜绝高并发下的资源泄露
- 🤖 **AI 集成（MCP Server）**：
  - **标准化协议**：让 Claude/Cursor 直接调用 Crawlo 抓取能力，支持 `fetch`、`extract`、`spider` 等工具
  - **智能抓取模式**：提供 basic/stealth/max-stealth 三级降级策略，自适应不同难度的网站
  - **会话持久化**：支持 Cookie 保持与 Session 传递，方便 AI 执行多步有状态抓取任务
  - **结构化输出**：自动转换 Markdown/Text，支持内容截断与标准化错误码返回
- 🧠 **自适应选择器 (Adaptive Selector)**：
  - **元素自愈能力**：当网站改版导致选择器失效时，利用多维元素指纹（Tag, Text, Attributes, DOM Path, Context）自动找回目标元素
  - **智能匹配算法**：基于加权平均相似度匹配，支持自定义维度权重，确保定位的高准确性
  - **高性能存储**：支持 SQLite/Redis 双后端，内置 LRU 内存缓存层，毫秒级自愈响应
- 🔄 **灵活的配置模式**：
  - **Standalone 模式**：单机开发测试，使用内存队列
  - **Distributed 模式**：多节点分布式部署，严格要求 Redis（不允许降级）
  - **Auto 模式**：智能检测 Redis 可用性，自动选择最佳配置（推荐）
- 📦 **丰富的组件生态**：
  - 内置 Redis 和 MongoDB 支持
  - MySQL 异步连接池（基于 asyncmy 驱动）
  - 连接池健康检查与自动修复机制
  - 多种过滤器和去重管道（Memory/Redis）
  - 代理中间件支持（简单代理/动态代理）
  - 多种下载器（aiohttp、httpx、curl-cffi、Playwright）
  - 多平台通知系统（钉钉/飞书/企业微信/邮件/短信）
- 🛠 **开发友好**：
  - 类 Scrapy 的项目结构和 API 设计
  - 配置工厂模式（`CrawloConfig.auto()`）
  - 自动爬虫发现机制
  - 完善的日志系统

## 项目架构

Crawlo 框架采用模块化设计，核心组件包括：

![Crawlo 框架架构图](assets/Crawlo%20框架架构图.png)

- **Engine**：核心引擎，协调各个组件工作
- **Scheduler**：调度器，管理请求队列和去重
- **Downloader**：下载器，支持多种 HTTP 客户端
- **Spider**：爬虫基类，定义数据提取逻辑
- **Pipeline**：数据管道，处理和存储数据
- **Middleware**：中间件，处理请求和响应

![Crawlo 数据流图](assets/Crawlo%20数据流图.png)

## 示例项目

查看 [`examples/`](examples/) 目录下的完整示例项目：

- **ofweek_standalone** - Auto 模式示例（智能检测）
- **ofweek_spider** - Auto 模式示例
- **ofweek_distributed** - Distributed 模式示例（严格分布式）

## 安装

```
# 基础安装
pip install crawlo
```

## 配置模式详解

> ⚠️ **重要**：配置模式的选择直接影响爬虫的运行方式、性能和可靠性，请仔细阅读本节内容。

Crawlo 提供三种配置模式，满足不同场景需求：

### 三种模式对比

| 配置项 | Standalone | Distributed | Auto |
|--------|-----------|-------------|------|
| **RUN_MODE** | `standalone` | `distributed` | `auto` |
| **队列类型** | 内存队列 | Redis 队列 | 自动检测 |
| **Redis 要求** | 不需要 | **必需** | 可选 |
| **Redis 不可用时** | N/A | 🚫 **报错退出** | ✅ 降级到内存 |
| **配置自动更新** | ❌ 否 | ❌ 否 | ✅ 是 |
| **过滤器** | Memory | Redis | Redis/Memory |
| **去重管道** | Memory | Redis | Redis/Memory |
| **适用场景** | 开发测试 | 多节点部署 | 生产环境 |
| **并发数默认值** | 8 | 16 | 12 |
| **推荐指数** | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

### 1. Auto 模式（推荐）

**智能检测，自动适配，推荐用于生产环境。**

``python
from crawlo.config import CrawloConfig

config = CrawloConfig.auto(
    project_name='myproject',
    concurrency=12,
    download_delay=1.0
)
locals().update(config.to_dict())
```

**运行机制**：
- 配置阶段不依赖 Redis
- 运行时才检测 Redis 可用性
- Redis 可用 → 使用 `RedisPriorityQueue` + `AioRedisFilter`
- Redis 不可用 → 降级到 `MemoryQueue` + `MemoryFilter`
- 自动更新配置（`QUEUE_TYPE`、`FILTER_CLASS`、`DEFAULT_DEDUP_PIPELINE`）

**优势**：
- ✅ 开发环境无需配置 Redis，直接启动
- ✅ 生产环境 Redis 故障时自动降级，保证系统可用性
- ✅ 同一份代码可在不同环境运行，无需修改配置
- ✅ 最佳的灵活性和可靠性

**适用场景**：
- 生产环境部署（首选）
- 需要在多种环境运行的项目
- 希望系统具备容错能力

### 2. Standalone 模式

**单机模式，适合开发测试和中小规模爬取。**

``python
config = CrawloConfig.standalone(
    project_name='myproject',
    concurrency=8
)
locals().update(config.to_dict())
```

**运行机制**：
- 固定使用 `MemoryQueue`（内存队列）
- 固定使用 `MemoryFilter`（内存过滤器）
- 固定使用 `MemoryDedupPipeline`（内存去重）
- 不进行 Redis 检测
- 配置不会自动更新

**优势**：
- ✅ 无需任何外部依赖
- ✅ 启动速度快
- ✅ 适合快速开发调试

**限制**：
- ❌ 不支持分布式部署
- ❌ 重启后队列数据丢失
- ❌ 不适合大规模数据采集

**适用场景**：
- 本地开发调试
- 学习框架特性
- 中小规模数据采集（< 10万条）
- 单机运行的简单爬虫

### 3. Distributed 模式

**分布式模式，严格要求 Redis 可用，适合多节点协同工作。**

``python
config = CrawloConfig.distributed(
    project_name='myproject',
    redis_host='redis.example.com',
    redis_port=6379,
    redis_password='your_password',
    concurrency=16
)
locals().update(config.to_dict())
```

**运行机制**：
- 必须使用 `RedisPriorityQueue`
- 必须使用 `AioRedisFilter`
- 必须使用 `RedisDedupPipeline`
- 启动时强制检查 Redis 连接
- **Redis 不可用时抛出 `RuntimeError` 并退出（不允许降级）**

**为什么要严格要求 Redis？**

1. **数据一致性**：防止不同节点使用不同的队列类型
2. **去重有效性**：确保多节点间的去重功能正常工作
3. **任务分配**：防止任务被重复执行
4. **问题早发现**：启动失败比运行时失败更容易发现和修复
5. **明确的意图**：分布式模式就应该是分布式的，不应该静默降级

**Redis 不可用时的错误信息**：

```
$ crawlo run my_spider

2025-10-25 22:00:00 - [queue_manager] - ERROR: 
Distributed 模式要求 Redis 可用，但无法连接到 Redis 服务器。
错误信息: Connection refused
Redis URL: redis://127.0.0.1:6379/0
请检查：
  1. Redis 服务是否正在运行
  2. Redis 连接配置是否正确
  3. 网络连接是否正常

RuntimeError: Distributed 模式要求 Redis 可用，但无法连接到 Redis 服务器。
```

**优势**：
- ✅ 支持多节点协同爬取
- ✅ 数据持久化，重启后可继续
- ✅ 严格的分布式一致性保证
- ✅ 适合大规模数据采集

**适用场景**：
- 多服务器协同采集
- 大规模数据采集（> 百万条）
- 需要严格保证分布式一致性
- 生产环境多节点部署

### 模式选择建议

| 场景 | 推荐模式 | 原因 |
|------|---------|------|
| 生产环境（单节点或多节点） | **Auto** | 自动适配，容错能力强 |
| 开发环境 | **Standalone** 或 **Auto** | 无需配置 Redis |
| 严格的多节点分布式部署 | **Distributed** | 保证分布式一致性 |
| 学习和测试 | **Standalone** | 最简单，无依赖 |
| 中小规模爬取 | **Standalone** 或 **Auto** | 简单高效 |
| 大规模爬取 | **Auto** 或 **Distributed** | 性能和可靠性 |

> 📖 **完整文档**：更多详细信息请参考 [配置模式完全指南](docs/tutorials/configuration_modes.md)

## Redis 数据结构说明

在使用 Distributed 模式或 Auto 模式且 Redis 可用时，Crawlo 框架会在 Redis 中创建以下数据结构用于管理和跟踪爬虫状态：

### 核心 Redis Keys

1. **`{project_name}:filter:fingerprint`** - 请求去重过滤器
   - 类型：Redis Set
   - 用途：存储已处理请求的指纹，避免重复抓取相同URL
   - 示例：`crawlo:ofweek_standalone:filter:fingerprint`

2. **`{project_name}:item:fingerprint`** - 数据项去重集合
   - 类型：Redis Set
   - 用途：存储已处理数据项的指纹，避免重复处理相同的数据
   - 示例：`crawlo:ofweek_standalone:item:fingerprint`

3. **`{project_name}:queue:requests`** - 主请求队列
   - 类型：Redis Sorted Set
   - 用途：存储待处理的爬虫请求，按优先级排序
   - 示例：`crawlo:ofweek_standalone:queue:requests`

4. **`{project_name}:queue:requests:data`** - 主请求队列数据
   - 类型：Redis Hash
   - 用途：保存请求队列中每个请求的详细序列化数据
   - 示例：`crawlo:ofweek_standalone:queue:requests:data`

### 数据核验方法

在爬虫采集完成后，您可以使用这些 Redis key 来核验数据和监控爬虫状态：

```bash
# 连接到 Redis
redis-cli

# 查看请求去重数量（已处理的唯一URL数）
SCARD crawlo:ofweek_standalone:filter:fingerprint

# 查看数据项去重数量（已处理的唯一数据项数）
SCARD crawlo:ofweek_standalone:item:fingerprint

# 查看待处理队列长度
ZCARD crawlo:ofweek_standalone:queue:requests

# 获取部分指纹数据进行检查
SMEMBERS crawlo:ofweek_standalone:filter:fingerprint LIMIT 10

# 获取队列中的请求信息
ZRANGE crawlo:ofweek_standalone:queue:requests 0 -1 WITHSCORES LIMIT 10
```

### 注意事项

1. **数据清理**：爬虫任务完成后，建议清理这些 Redis keys 以释放内存：
   ```bash
   DEL crawlo:ofweek_standalone:filter:fingerprint
   DEL crawlo:ofweek_standalone:item:fingerprint
   DEL crawlo:ofweek_standalone:queue:requests
   DEL crawlo:ofweek_standalone:queue:requests:data
   ```

2. **命名空间隔离**：不同项目使用不同的 `{project_name}` 前缀，确保数据隔离。对于同一项目下的不同爬虫，还可以通过 `{spider_name}` 进一步区分，确保更细粒度的数据隔离。

3. **持久化考虑**：如果需要持久化这些数据，确保 Redis 配置了合适的持久化策略

## 配置优先级

Crawlo 框架支持多层级的配置系统，了解配置优先级对于正确使用框架至关重要。

### 配置来源与优先级

从**低到高**的优先级顺序：

```
1. default_settings.py (框架默认配置)                    ⭐
   ↓
2. 环境变量 (CRAWLO_*)                                   ⭐⭐
   (在 default_settings.py 中通过 EnvConfigManager 读取)
   ↓
3. 用户 settings.py (项目配置文件)                       ⭐⭐⭐
   ↓
4. Spider.custom_settings (Spider 自定义配置)            ⭐⭐⭐⭐
   ↓
5. 运行时 settings 参数 (crawl() 传入的配置)             ⭐⭐⭐⭐⭐
```

### 环境变量配置

所有环境变量都使用 `CRAWLO_` 前缀：

```bash
# 基础配置
export CRAWLO_MODE=auto                    # 运行模式
export CRAWLO_PROJECT_NAME=myproject       # 项目名称
export CRAWLO_CONCURRENCY=16               # 并发数

# Redis 配置
export CRAWLO_REDIS_HOST=127.0.0.1         # Redis 主机
export CRAWLO_REDIS_PORT=6379              # Redis 端口
export CRAWLO_REDIS_PASSWORD=your_password # Redis 密码
export CRAWLO_REDIS_DB=0                   # Redis 数据库
```

### 配置合并策略

**普通配置**（如 `CONCURRENCY`）：采用**覆盖策略**
```python
# 假设各处都有定义
default_settings.py:  8   →
环境变量:  12  →
settings.py:  16  →
Spider.custom_settings:  24  →
crawl(settings={...}):  32  ✅ 最终值 = 32
```

**列表配置**（如 `MIDDLEWARES`、`PIPELINES`、`EXTENSIONS`）：采用**合并策略**
```python
# default_settings.py
PIPELINES = {
    'crawlo.pipelines.console_pipeline.ConsolePipeline': 500,
}

# settings.py
PIPELINES = {
    'myproject.pipelines.MySQLPipeline': 600,
}

# 最终结果（合并）
PIPELINES = {
    'crawlo.pipelines.console_pipeline.ConsolePipeline': 500,  # 保留默认
    'myproject.pipelines.MySQLPipeline': 600,                   # 追加用户
}
```

### Spider 级别配置

在 Spider 类中可以覆盖项目配置：

```python
class MySpider(Spider):
    name = 'myspider'
    
    custom_settings = {
        'CONCURRENCY': 32,           # 覆盖项目配置
        'DOWNLOAD_DELAY': 2.0,       # 覆盖项目配置
        'PIPELINES': [               # 会与默认管道合并
            'myproject.pipelines.SpecialPipeline',
        ]
    }
```

### 运行时动态配置

```
from crawlo import CrawlerProcess

process = CrawlerProcess()
await process.crawl(
    MySpider,
    settings={
        'CONCURRENCY': 64,        # 最高优先级
        'DOWNLOAD_DELAY': 0.1,
    }
)
```

### ⚠️ 常见陷阱

**陷阱1：环境变量被项目配置覆盖**
```python
# 环境变量
export CRAWLO_REDIS_HOST=192.168.1.100

# settings.py（这会覆盖环境变量！）
REDIS_HOST = 'localhost'  # ❌ 会覆盖环境变量

# 解决方案：不在 settings.py 中重复设置，或使用 CrawloConfig.auto()
```

**陷阱2：误以为字典配置会被清空**
```python
# settings.py
PIPELINES = {
    'myproject.pipelines.MySQLPipeline': 600,
}

# 实际结果（默认管道会被保留并合并）
PIPELINES = {
    'crawlo.pipelines.console_pipeline.ConsolePipeline': 500,  # 默认保留
    'myproject.pipelines.MySQLPipeline': 600,                   # 用户追加
}

# 如果想完全替换，需要先清空
PIPELINES = {}  # 清空
PIPELINES['myproject.pipelines.MySQLPipeline'] = 600
```

> 📖 **详细文档**：完整的配置优先级说明请参考 [配置优先级详解](docs/配置优先级详解.md)

## 中间件优先级策略

在 Crawlo 框架中，中间件的执行顺序由优先级数值决定。**请求阶段**按数值从小到大执行，**响应阶段**按数值从大到小执行（LIFO 模式）。

### 1. 优先级设计原则

采用**双向对称设计**：
- **请求阶段**（process_request）：数值越小，越先执行
- **响应阶段**（process_response）：数值越大，越先执行

这种设计确保：
- 请求处理最早执行的中间件，在响应处理时最后执行（类似洋葱模型）
- 符合中间件的天然依赖关系（如：先添加请求头，后处理响应）

### 2. 默认中间件优先级

```python
MIDDLEWARES = {
    # 请求阶段（小 → 大）
    'crawlo.middleware.request_ignore.RequestIgnoreMiddleware': 100,  # 1. 忽略无效请求
    'crawlo.middleware.download_delay.DownloadDelayMiddleware': 200,  # 2. 下载延迟控制
    'crawlo.middleware.default_header.DefaultHeaderMiddleware': 300,  # 3. 添加默认请求头
    'crawlo.middleware.offsite.OffsiteMiddleware': 400,               # 4. 站外请求过滤
    
    # 响应阶段（大 → 小）
    'crawlo.middleware.response_filter.ResponseFilterMiddleware': 700, # 5. 响应过滤
    'crawlo.middleware.response_code.ResponseCodeMiddleware': 650,     # 6. 状态码处理
    'crawlo.middleware.retry.RetryMiddleware': 600,                    # 7. 请求重试
}
```

### 3. 内置优先级常量

框架提供了语义化常量供用户使用：

```python
from crawlo.utils.priority import MiddlewarePriority

# 可用常量
MiddlewarePriority.CUSTOM = 500          # 自定义中间件默认优先级
MiddlewarePriority.CUSTOM_REQUEST = 450  # 自定义请求处理中间件
MiddlewarePriority.CUSTOM_RESPONSE = 550 # 自定义响应处理中间件
```

### 4. 用户自定义中间件优先级建议

- **请求处理类**：
  - 安全/认证：100-200
  - 请求过滤/验证：200-300
  - 请求头/代理设置：300-400
  - 通用请求处理：400-500

- **响应处理类**：
  - 通用响应处理：500-600
  - 重试/恢复：600-650
  - 响应验证/解析：650-700
  - 响应后处理：700-800

### 5. 使用示例

```python
from crawlo.utils.priority import MiddlewarePriority

MIDDLEWARES = {
    # 使用语义化常量
    'myproject.middleware.AuthMiddleware': MiddlewarePriority.CUSTOM_REQUEST,
    'myproject.middleware.DataParseMiddleware': MiddlewarePriority.CUSTOM_RESPONSE,
    
    # 或直接使用数值
    'myproject.middleware.CustomMiddleware': 500,
}
```

### 6. 优先级设置原则

1. **过滤器优先**：能快速拒绝无效请求的中间件应具有较小数值（请求阶段先执行）
2. **依赖关系**：如果中间件 A 的输出是 B 的输入，A 的数值应小于 B
3. **对称性**：请求阶段数值小的中间件，在响应阶段会最后执行
4. **间隔预留**：建议以 50-100 为间隔，方便后续插入新中间件

> 💡 **提示**：`OffsiteMiddleware` 只有在配置了 `ALLOWED_DOMAINS` 时才会启用，否则会因 `NotConfiguredError` 而被禁用

## 快速开始

### 1. 创建项目

```
# 创建新项目
crawlo startproject myproject
cd myproject

# 创建爬虫
crawlo genspider example example.com
```

### 2. 配置项目（推荐使用 Auto 模式）

```
# myproject/settings.py
from crawlo.config import CrawloConfig

# 使用 Auto 模式：智能检测 Redis，自动选择最佳配置
config = CrawloConfig.auto(
    project_name='myproject',
    concurrency=12,          # 并发数
    download_delay=1.0       # 下载延迟（秒）
)

# 将配置应用到当前模块
locals().update(config.to_dict())

# 爬虫模块配置
SPIDER_MODULES = ['myproject.spiders']

# 日志配置
LOG_LEVEL = 'INFO'
LOG_FILE = 'logs/myproject.log'

# 可选：添加数据管道（注意：现在是字典格式）
# PIPELINES = {
#     'crawlo.pipelines.mysql_pipeline.MySQLPipeline': 500,
# }

# 可选：Redis 配置（Auto 模式会自动检测）
# REDIS_HOST = '127.0.0.1'
# REDIS_PORT = 6379
```

**其他配置模式：**

```python
# Standalone 模式：单机开发测试
config = CrawloConfig.standalone(
    project_name='myproject',
    concurrency=8
)

# Distributed 模式：多节点分布式（必须配置 Redis）
config = CrawloConfig.distributed(
    project_name='myproject',
    redis_host='redis.example.com',
    redis_port=6379,
    redis_password='your_password',
    concurrency=16
)
```

### 3. 编写爬虫

```
# myproject/spiders/example.py
from crawlo import Spider
from crawlo.http import Request

class ExampleSpider(Spider):
    name = 'example'
    start_urls = ['https://example.com']
    
    async def parse(self, response):
        # 提取数据
        title = response.css('h1::text').get()
        
        # 返回数据
        yield {
            'title': title,
            'url': response.url
        }
        
        # 跟进链接
        for href in response.css('a::attr(href)').getall():
            yield Request(
                url=response.urljoin(href),
                callback=self.parse
            )
```

### 4. 运行爬虫

```
# 运行指定爬虫
crawlo run example

# 指定日志级别
crawlo run example --log-level DEBUG
```

## 通知系统

Crawlo 提供了完善的多平台通知系统，支持钉钉、飞书、企业微信、邮件和短信通知。

### 📋 配置说明

在 `settings.py` 中配置通知系统：

```python
# 启用通知系统
NOTIFICATION_ENABLED = True
NOTIFICATION_CHANNELS = ['dingtalk']  # 可选: dingtalk, feishu, wecom, email, sms

# 钉钉通知配置
DINGTALK_WEBHOOK = "https://oapi.dingtalk.com/robot/send?access_token=YOUR_TOKEN"
DINGTALK_SECRET = "YOUR_SECRET"
DINGTALK_KEYWORDS = ["爬虫"]  # 关键词验证
DINGTALK_AT_MOBILES = ["15361276730"]  # @特定手机号
DINGTALK_IS_AT_ALL = False  # 是否@所有人

# 飞书/企业微信配置（类似）
FEISHU_WEBHOOK = "YOUR_FEISHU_WEBHOOK"
WECOM_WEBHOOK = "YOUR_WECOM_WEBHOOK"
```

### 🚀 基础使用

```python
from crawlo.bot.handlers import send_crawler_status, send_crawler_alert, send_crawler_progress
from crawlo.bot.models import ChannelType

# 发送状态通知
await send_crawler_status(
    title="【状态】爬虫启动",
    content="爬虫任务已启动，开始抓取数据...",
    channel=ChannelType.DINGTALK
)

# 发送进度通知
await send_crawler_progress(
    title="【进度】数据抓取",
    content="已完成 50% 的数据抓取任务",
    channel=ChannelType.DINGTALK
)

# 发送告警通知
await send_crawler_alert(
    title="【告警】网络异常",
    content="检测到网络连接不稳定，部分请求失败",
    channel=ChannelType.DINGTALK
)
```

### 📊 使用建议

**推荐通知节点：**
- 爬虫启动时 - 发送状态通知
- 关键里程碑 - 发送进度通知（如每100条数据）
- 异常情况 - 立即发送告警通知
- 任务完成时 - 发送总结通知

**@ 功能使用：**
```python
# @ 特定手机号
DINGTALK_AT_MOBILES = ["15361276730"]

# @ 所有人
DINGTALK_IS_AT_ALL = True
```

**重试机制：**
```python
NOTIFICATION_RETRY_ENABLED = True
NOTIFICATION_RETRY_TIMES = 3
NOTIFICATION_RETRY_DELAY = 5  # 秒
```

> 💡 详细使用指南请参考 [docs/notification_guide.md](docs/notification_guide.md)

## 核心功能

### Response 对象

Crawlo 的 [`Response`](crawlo/http/response.py) 对象提供了强大的网页处理能力：

**1. 智能编码检测**

```
# 自动检测并正确解码页面内容
# 优先级：Content-Type → HTML meta → chardet → utf-8
response.text      # 已正确解码的文本
response.encoding  # 检测到的编码
```

**2. CSS/XPath 选择器**

```
# CSS 选择器（推荐）
title = response.css('h1::text').get()
links = response.css('a::attr(href)').getall()

# XPath 选择器
title = response.xpath('//title/text()').get()
links = response.xpath('//a/@href').getall()

# 支持默认值
title = response.css('h1::text').get(default='无标题')
```

**3. URL 处理**

```
response.url          # 自动规范化（移除 fragment）
response.original_url # 保留原始 URL

# 智能 URL 拼接
response.urljoin('/path')           # 绝对路径
response.urljoin('../path')         # 相对路径
response.urljoin('//cdn.com/img')   # 协议相对路径
```

**4. 便捷提取方法**

```
# 提取单个/多个元素文本
title = response.extract_text('h1')
paragraphs = response.extract_texts('.content p')

# 提取单个/多个元素属性
link = response.extract_attr('a', 'href')
all_links = response.extract_attrs('a', 'href')
```

### MySQLHelper 数据库操作工具

Crawlo 提供了 `MySQLHelper` 工具类，用于在 Spider 中进行数据库操作（如数据去重检查）。

#### 1. 基本用法

```python
from crawlo.utils.mysql_helper import get_mysql_helper

class MySpider(Spider):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.db_helper = None
    
    async def parse_detail(self, response):
        # 首次使用时初始化 MySQLHelper
        if self.db_helper is None:
            # 方式1: 直接传入 spider，自动获取配置（推荐）
            self.db_helper = await get_mysql_helper(spider=self)
            # 方式2: 手动传入 settings
            # self.db_helper = await get_mysql_helper(self.crawler.settings)
        
        # 检查数据是否存在
        table_name = self.crawler.settings.get('MYSQL_TABLE', 'my_table')
        exists = await self.db_helper.exists(table_name, {"url": response.url})
        
        if exists:
            self.logger.info(f"数据已存在，跳过：{response.url}")
            return
        
        # 继续处理...
```

#### 2. 配置说明

**方式一：通过 custom_settings 配置（推荐）**

```python
class MySpider(Spider):
    name = 'my_spider'
    
    # 在 spider 中配置表名
    custom_settings = {
        'MYSQL_TABLE': 'my_table',  # 数据表名
    }
```

**方式二：通过 settings.py 全局配置**

```python
# settings.py
MYSQL_TABLE = 'my_table'
```

#### 3. 配置优先级

```
spider.custom_settings > settings.py > 默认值
```

#### 4. 连接池复用

- `MySQLHelper` 每次调用会创建新实例
- 但连接池由 `MySQLConnectionPoolManager` 统一管理
- 相同配置（host:port:db）的请求会复用同一个连接池

#### 5. API 参考

| 方法 | 说明 |
|------|------|
| `get_mysql_helper(spider=self)` | 获取 MySQLHelper 实例 |
| `helper.exists(table, conditions)` | 检查数据是否存在 |
| `helper.insert(table, data)` | 插入单条数据 |
| `helper.batch_insert(table, data_list)` | 批量插入数据 |

### 协议下载器 (默认行为)

Crawlo 默认使用协议下载器处理所有请求，无需额外配置。协议下载器基于 httpx/aiohttp/curl_cffi 实现，适用于常规的 HTTP/HTTPS 请求。

#### 1. 默认行为

```python
# 默认配置（无需设置）
# DOWNLOADER = "crawlo.downloader.hybrid_downloader.HybridDownloader"
# HYBRID_DEFAULT_PROTOCOL_DOWNLOADER = "httpx"

# 所有请求默认使用协议下载器
class MySpider(Spider):
    name = 'protocol_spider'
    start_urls = ['https://example.com']
    
    async def parse(self, response):
        # 直接解析静态页面内容
        title = response.css('h1::text').get()
        yield {'title': title}
```

#### 2. 选择协议下载器类型

```python
# settings.py

# 可选：指定默认的协议下载器
HYBRID_DEFAULT_PROTOCOL_DOWNLOADER = "httpx"  # 推荐，功能最全
# HYBRID_DEFAULT_PROTOCOL_DOWNLOADER = "aiohttp"  # 性能最好
# HYBRID_DEFAULT_PROTOCOL_DOWNLOADER = "curl_cffi"  # 模拟浏览器TLS指纹
```

#### 3. 协议下载器的优势

- **高性能**：基于异步 HTTP 客户端，支持高并发
- **低资源**：无需启动浏览器，内存占用小
- **稳定可靠**：成熟稳定，适合大规模爬取
- **支持丰富**：支持代理、cookie、自定义请求头等

#### 4. 重要说明

从 v1.6.1 开始，框架**不再自动检测**以下情况并强制使用动态下载器：
- ❌ POST 请求
- ❌ URL 包含 ajax/api/dynamic 等关键词

**只有明确配置时才会使用动态下载器**，避免误判和性能浪费。

### 动态下载器 (PlaywrightDownloader)

动态下载器基于 Playwright 实现，专门用于处理需要 JavaScript 渲染的动态页面。**注意：默认情况下不会使用动态下载器，必须显式配置。**

#### 1. 何时使用动态下载器？

只有以下场景需要使用动态下载器：
- ✅ 页面内容由 JavaScript 动态加载（AJAX/SPA）
- ✅ 需要执行 JavaScript 交互（点击、滚动等）
- ✅ 页面内容在浏览器中可见，但 HTTP 请求无法获取

#### 2. 启用动态下载器的方法

**方法一：全局配置域名（推荐）**

```python
# settings.py

# 指定需要动态渲染的域名
DYNAMIC_RENDER_DOMAINS = ['spa.example.com', 'react-app.com']

# 或使用 URL 模式（正则表达式）
DYNAMIC_RENDER_URL_PATTERNS = [
    r'.*\.spa\.example\.com.*',
    r'.*/dynamic/.*'
]
```

**方法二：单个请求启用**

```python
from crawlo import Spider
from crawlo.http import Request

class DynamicSpider(Spider):
    name = 'dynamic_spider'
    
    async def parse(self, response):
        # 为单个请求启用动态渲染
        yield Request(
            url='https://spa.example.com/page',
            callback=self.parse_spa,
            meta={'use_dynamic_loader': True}  # 显式指定
        )
    
    async def parse_spa(self, response):
        # 此页面通过 Playwright 渲染
        title = response.css('h1::text').get()
        yield {'title': title}
```

#### 3. Playwright 配置

启用动态下载器后，需要配置 Playwright 参数：

```python
# settings.py

# 浏览器配置
PLAYWRIGHT_BROWSER_TYPE = 'chromium'  # 浏览器类型：chromium/firefox/webkit
PLAYWRIGHT_HEADLESS = True  # True=无头模式，False=显示浏览器窗口
PLAYWRIGHT_TIMEOUT = 30000  # 超时时间（毫秒）

# 窗口大小
PLAYWRIGHT_VIEWPORT_WIDTH = 1280   # 窗口宽度
PLAYWRIGHT_VIEWPORT_HEIGHT = 720   # 窗口高度

# 页面池配置
PLAYWRIGHT_SINGLE_BROWSER_MODE = True  # 单浏览器多标签页模式
PLAYWRIGHT_MAX_PAGES_PER_BROWSER = 10  # 最大并发标签页数
```

#### 4. 智能滚动加载

自动处理懒加载页面，滚动到底部触发新内容加载：

```python
async def parse(self, response):
    # 请求时添加滚动配置
    yield Request(
        url='https://example.com/infinite-scroll',
        callback=self.parse_content,
        meta={
            'use_dynamic_loader': True,  # 必须启用动态渲染
            'playwright_actions': [
                {
                    'type': 'scroll_to_bottom',
                    'params': {
                        'scroll_delay': 500,      # 每次滚动间隔（毫秒）
                        'max_no_content': 2        # 连续N次无新内容则认为到底
                    }
                }
            ]
        }
    )

async def parse_content(self, response):
    # 提取滚动加载后的所有内容
    items = response.css('.item').getall()
    self.logger.info(f"加载了 {len(items)} 个条目")
```

#### 5. 点击翻页

处理"加载更多"、"下一页"等点击交互：

```python
async def parse(self, response):
    current_page = response.meta.get('page', 1)
    max_pages = response.meta.get('max_pages', 3)
    
    # 提取当前页数据
    articles = response.css('.article').getall()
    self.logger.info(f"第 {current_page} 页: {len(articles)} 篇文章")
    
    # 如果还有下一页，点击加载
    if current_page < max_pages:
        yield Request(
            url=response.url,
            callback=self.parse,
            dont_filter=True,  # 允许重复URL
            meta={
                'page': current_page + 1,
                'max_pages': max_pages,
                'use_dynamic_loader': True,  # 必须启用动态渲染
                'playwright_actions': [
                    # 先滚动到底部，让按钮可见
                    {
                        'type': 'scroll_to_bottom',
                        'params': {
                            'scroll_delay': 500,
                            'max_no_content': 2
                        }
                    },
                    # 等待按钮渲染
                    {
                        'type': 'wait',
                        'params': {'timeout': 1000}
                    },
                    # 点击"加载更多"按钮
                    {
                        'type': 'click_and_wait',
                        'params': {
                            'selector': '//div[contains(@class, "more-button")]',  # XPath
                            'wait_timeout': 3000,  # 等待超时
                            'wait_for': 'networkidle'  # 等待网络空闲
                        }
                    }
                ]
            }
        )
```

#### 6. 复杂交互操作

支持多种页面操作类型：

```python
meta={
    'use_dynamic_loader': True,  # 必须启用动态渲染
    'playwright_actions': [
        # 1. 智能滚动到底部
        {
            'type': 'scroll_to_bottom',
            'params': {'scroll_delay': 500, 'max_no_content': 2}
        },
        
        # 2. 等待固定时间
        {
            'type': 'wait',
            'params': {'timeout': 2000}
        },
        
        # 3. 点击元素并等待
        {
            'type': 'click_and_wait',
            'params': {
                'selector': '.load-more-btn',  # CSS选择器
                'wait_timeout': 5000,
                'wait_for': 'selector:.new-content'  # 等待新元素出现
            }
        },
        
        # 4. 自定义 JavaScript 执行
        {
            'type': 'evaluate',
            'params': {
                'script': '() => document.querySelectorAll(".item").length'
            }
        },
        
        # 5. 等待元素出现
        {
            'type': 'wait_for_selector',
            'params': {
                'selector': '#dynamic-content',
                'timeout': 10000
            }
        }
    ]
}
```

#### 7. 并发控制

Playwright 使用单浏览器多标签页模式，自动管理页面池：

```python
# settings.py

# 最大并发标签页数（默认10）
PLAYWRIGHT_MAX_PAGES_PER_BROWSER = 10

# 说明：
# - 只启动一个浏览器窗口
# - 创建多个标签页（tab）复用
# - 标签页使用完毕后回到池中，不关闭
# - 支持并发处理多个请求（如10个详情页同时渲染）
```

#### 8. 完整示例 - InfoQ 动态页面爬取

```python
from crawlo import Spider
from crawlo.http import Request
from crawlo.items import Item, Field

class InfoqArticle(Item):
    """InfoQ 文章数据项"""
    url = Field()
    title = Field()
    author = Field()
    date = Field()
    content = Field()

class InfoqSpider(Spider):
    name = 'infoq_spider'
    start_urls = ['https://www.infoq.cn/zones/harmonyos/latest']
    
    async def parse(self, response):
        current_page = response.meta.get('page', 1)
        max_pages = response.meta.get('max_pages', 3)
        
        self.logger.info(f"# 当前页码: {current_page}")
        
        # 提取文章列表
        articles = response.css('.article-item')
        self.logger.info(f"找到文章容器: {len(articles)} 个")
        
        for article in articles:
            yield InfoqArticle(
                url=article.css('a::attr(href)').get(),
                title=article.css('h3::text').get(),
                author=article.css('.author::text').get(),
                date=article.css('.date::text').get(),
            )
        
        # 点击"加载更多"
        if current_page < max_pages:
            self.logger.info(f"点击'更多'按钮加载第 {current_page + 1} 页...")
            yield Request(
                url=response.url,
                callback=self.parse,
                dont_filter=True,
                meta={
                    'page': current_page + 1,
                    'max_pages': max_pages,
                    'playwright_actions': [
                        # 滚动到底部
                        {
                            'type': 'scroll_to_bottom',
                            'params': {'scroll_delay': 500, 'max_no_content': 2}
                        },
                        # 等待
                        {'type': 'wait', 'params': {'timeout': 1000}},
                        # 点击按钮
                        {
                            'type': 'click_and_wait',
                            'params': {
                                'selector': '//div[contains(@class, "more-button")]',
                                'wait_timeout': 3000,
                                'wait_for': 'networkidle'
                            }
                        }
                    ]
                }
            )
        else:
            self.logger.info(f"已达到最大页数限制 ({max_pages} 页)，停止翻页")
```

#### 9. 常见问题

**Q: 如何调试动态页面？**

A: 设置 `PLAYWRIGHT_HEADLESS = False` 显示浏览器窗口，观察页面交互过程。

**Q: 页面池满了怎么办？**

A: 当并发请求数超过 `PLAYWRIGHT_MAX_PAGES_PER_BROWSER` 时，会创建临时页面。建议根据实际需求调整并发数。

**Q: 如何选择合适的选择器？**

A: 优先使用 CSS 选择器（性能更好），复杂场景使用 XPath。可在浏览器开发者工具中测试选择器。

### 配置工厂模式

Crawlo 提供了便捷的配置工厂方法，无需手动配置繁琐的参数：

```
from crawlo.config import CrawloConfig

# Auto 模式（推荐）：智能检测，自动适配
config = CrawloConfig.auto(
    project_name='myproject',
    concurrency=12,
    download_delay=1.0
)

# Standalone 模式：单机开发
config = CrawloConfig.standalone(
    project_name='myproject',
    concurrency=8
)

# Distributed 模式：严格分布式
config = CrawloConfig.distributed(
    project_name='myproject',
    redis_host='localhost',
    redis_port=6379,
    concurrency=16
)

# 应用到 settings.py
locals().update(config.to_dict())
```

**三种模式的核心区别**：

- **Auto**：智能检测 Redis，自动选择最佳配置，**推荐用于生产环境**
- **Standalone**：固定使用内存队列，适合开发测试，无外部依赖
- **Distributed**：严格要求 Redis，不允许降级，保证分布式一致性

> 💡 详细配置说明请查看前面的 [配置模式详解](#配置模式详解) 章节

### 定时任务功能

Crawlo 提供了内置的定时任务调度功能，支持灵活的周期性爬虫执行：

**1. 启用定时任务**

在项目配置文件中启用并配置定时任务：

```
# settings.py

# 启用定时任务 - 默认关闭
SCHEDULER_ENABLED = True

# 定时任务配置
SCHEDULER_JOBS = [
    {
        'spider': 'myproject.spiders.my_spider',  # 爬虫名称（对应spider的name属性）
        'cron': '*/30 * * * *',       # 每30分钟执行一次
        'enabled': True,              # 任务启用状态
        'priority': 10,               # 任务优先级
        'max_retries': 3,             # 最大重试次数
        'retry_delay': 60,            # 重试延迟（秒）
        'args': {},                  # 传递给爬虫的参数
        'kwargs': {}                  # 传递给爬虫的额外参数
    },
    {
        'spider': 'myproject.spiders.another_spider',  # 另一个爬虫
        'cron': '0 2 * * *',         # 每天凌晨2点执行
        'enabled': True,              # 任务启用状态
        'priority': 20,               # 任务优先级
        'max_retries': 2,             # 最大重试次数
        'retry_delay': 120,           # 重试延迟（秒）
        'args': {'daily': True},      # 传递给爬虫的参数
        'kwargs': {}                  # 传递给爬虫的额外参数
    }
]

# 关键配置参数（用户可能需要调整）
SCHEDULER_CHECK_INTERVAL = 1           # 调度器检查间隔（秒）
SCHEDULER_MAX_CONCURRENT = 3           # 最大并发任务数
SCHEDULER_JOB_TIMEOUT = 3600           # 单个任务超时时间（秒）
SCHEDULER_RESOURCE_MONITOR_ENABLED = True  # 是否启用资源监控
SCHEDULER_RESOURCE_CHECK_INTERVAL = 300    # 资源检查间隔（秒）
SCHEDULER_RESOURCE_LEAK_THRESHOLD = 3600   # 资源泄露检测阈值（秒）
```

**2. 运行定时任务**

有两种方式运行定时任务：

方法一：使用命令行
```
# 启动定时任务调度器（在项目目录下运行）
crawlo schedule
```

方法二：使用项目模板生成的 run.py 文件
```
# 启动定时任务模式
python run.py --schedule

# 正常运行单次爬虫
python run.py
```

**3. Cron 表达式说明**

定时任务使用标准的 Cron 表达式格式：`分钟 小时 日 月 星期`

常见表达式示例：
- `*/5 * * * *` - 每5分钟执行一次
- `0 */2 * * *` - 每2小时执行一次
- `30 9 * * *` - 每天上午9:30执行
- `0 2 * * 0` - 每周日凌晨2点执行
- `0 1 1 * *` - 每月1号凌晨1点执行

**4. 资源监控与管理**

定时任务系统集成了资源监控功能，可自动检测和管理资源泄露，确保长时间稳定运行。调度器还支持并发控制和任务超时管理，防止任务堆积和资源耗尽。

### 日志系统

Crawlo 提供了完善的日志系统，支持控制台和文件双输出：

```
from crawlo.logging import get_logger

logger = get_logger(__name__)

logger.debug('调试信息')
logger.info('普通信息')
logger.warning('警告信息')
logger.error('错误信息')
```

**日志配置：**

```
# settings.py
LOG_LEVEL = 'INFO'          # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FILE = 'logs/spider.log'
LOG_ENCODING = 'utf-8'      # 明确指定日志文件编码
STATS_DUMP = True           # 是否输出统计信息
```

**高级功能：**

```
from crawlo.logging import configure_logging

# 分别配置控制台和文件日志级别
configure_logging(
    LOG_LEVEL='INFO',
    LOG_CONSOLE_LEVEL='WARNING',  # 控制台只显示 WARNING 及以上
    LOG_FILE_LEVEL='DEBUG',       # 文件记录 DEBUG 及以上
    LOG_FILE='logs/app.log',
    LOG_MAX_BYTES=10*1024*1024,   # 10MB
    LOG_BACKUP_COUNT=5
)
```

### 爬虫自动发现

Crawlo 支持自动发现爬虫，无需手动导入：

```
# 自动发现并运行（推荐）
crawlo run spider_name

# 指定文件路径运行
crawlo run -f path/to/spider.py -s SpiderClassName
```

框架会自动在 `SPIDER_MODULES` 配置的模块中查找爬虫。

### 跨平台支持

Crawlo 在 Windows、macOS、Linux 上均可无缝运行：

- **Windows**：自动使用 ProactorEventLoop，正确处理控制台编码
- **macOS/Linux**：使用默认的 SelectorEventLoop
- 兼容不同平台的路径格式

> 💡 **Windows 用户提示**：框架默认已禁用日志轮转功能以避免文件锁定问题。如需启用日志轮转，建议安装 `concurrent-log-handler`：
> ```bash
> pip install concurrent-log-handler
> ```
> 然后在 settings.py 中设置：
> ```python
> LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
> LOG_BACKUP_COUNT = 5
> ```

![Crawlo 核心架构图](assets/Crawlo%20核心架构图.png)

## 文档

完整文档请查看 [`docs/`](docs/) 目录：

### 📚 核心教程

- [配置模式完全指南](docs/tutorials/configuration_modes.md) - **强烈推荐阅读**
- [架构概述](docs/modules/architecture/index.md)
- [运行模式](docs/modules/architecture/modes.md)
- [配置系统](docs/modules/configuration/index.md)

### 🔧 核心模块

- [引擎 (Engine)](docs/modules/core/engine.md)
- [调度器 (Scheduler)](docs/modules/core/scheduler.md)
- [处理器 (Processor)](docs/modules/core/processor.md)
- [爬虫基类 (Spider)](docs/modules/core/spider.md)

### 📦 功能模块

- [下载器 (Downloader)](docs/modules/downloader/index.md)
- [队列 (Queue)](docs/modules/queue/index.md)
- [过滤器 (Filter)](docs/modules/filter/index.md)
- [中间件 (Middleware)](docs/modules/middleware/index.md)
- [中间件优先级策略](docs/middleware_priority_guide.md)
- [管道 (Pipeline)](docs/modules/pipeline/index.md)
- [扩展 (Extension)](docs/modules/extension/index.md)

### 🛠 命令行工具

- [CLI 概述](docs/modules/cli/index.md)
- [startproject](docs/modules/cli/startproject.md) - 项目初始化
- [genspider](docs/modules/cli/genspider.md) - 爬虫生成
- [run](docs/modules/cli/run.md) - 爬虫运行
- [list](docs/modules/cli/list.md) - 查看爬虫列表
- [check](docs/modules/cli/check.md) - 配置检查
- [stats](docs/modules/cli/stats.md) - 统计信息

### 🚀 高级主题

- [分布式部署](docs/modules/advanced/distributed.md)
- [性能优化](docs/modules/advanced/performance.md)
- [故障排除](docs/modules/advanced/troubleshooting.md)
- [最佳实践](docs/modules/advanced/best_practices.md)

### 📝 性能优化报告

- [初始化优化报告](docs/initialization_optimization_report.md)
- [MySQL 连接池优化](docs/mysql_connection_pool_optimization.md)
- [MySQL 连接池健康检查](docs/mysql_connection_pool_optimization.md#健康检查机制)
- [MongoDB 连接池优化](docs/mongo_connection_pool_optimization.md)

### 🎯 中间件指南

- [中间件优先级策略](docs/middleware_priority_guide.md)

### 📖 API 参考

- [完整 API 文档](docs/api/)

---

**在线文档**：
- [中文文档](https://crawlo.readthedocs.io/en/latest/README_zh/)
- [English Documentation](https://crawlo.readthedocs.io/en/latest/)

**本地构建文档**：
```
mkdocs serve
# 浏览器访问 http://localhost:8000
```

## 常见问题

### 1. 如何选择配置模式？

- **开发测试**：使用 `CrawloConfig.standalone()`
- **生产环境**：使用 `CrawloConfig.auto()`（推荐）
- **多节点部署**：使用 `CrawloConfig.distributed()`

### 2. Distributed 模式 Redis 不可用怎么办？

Distributed 模式**严格要求 Redis**，不可用时会抛出 `RuntimeError` 并退出。这是为了保证分布式一致性和数据安全。

如果希望 Redis 不可用时自动降级，请使用 **Auto 模式**。

### 3. Auto 模式如何工作？

Auto 模式在运行时智能检测：
- Redis 可用 → 使用 RedisPriorityQueue + AioRedisFilter
- Redis 不可用 → 降级到 MemoryQueue + MemoryFilter

详见 [配置模式完全指南](docs/tutorials/configuration_modes.md)。

### 4. 如何启用 MySQL 或 MongoDB 支持？

```
# settings.py

PIPELINES = {
    'crawlo.pipelines.mysql_pipeline.MySQLPipeline': 500,  # MySQL
    # 或
    'crawlo.pipelines.mongo_pipeline.MongoDBPipeline': 500,       # MongoDB
}

# MySQL 配置
MYSQL_HOST = '127.0.0.1'
MYSQL_USER = 'root'
MYSQL_PASSWORD = 'password'
MYSQL_DB = 'mydb'
MYSQL_TABLE = 'items'

# MySQL 冲突处理策略（三者互斥，按优先级生效）
MYSQL_UPDATE_COLUMNS = ('updated',)  # 优先级最高：主键冲突时更新指定列，使用 ON DUPLICATE KEY UPDATE
MYSQL_AUTO_UPDATE = False           # 优先级中等：是否使用 REPLACE INTO（完全覆盖已存在记录）
MYSQL_INSERT_IGNORE = False         # 优先级最低：是否使用 INSERT IGNORE（忽略重复数据）

# 批量插入配置
MYSQL_USE_BATCH = True             # 是否使用批量插入提高性能
MYSQL_BATCH_SIZE = 100              # 批量插入大小
MYSQL_BATCH_TIMEOUT = 90            # 批量操作超时时间（秒）

# MySQL 连接池配置
MYSQL_POOL_MIN = 8                  # 最小连接数
MYSQL_POOL_MAX = 30                 # 最大连接数
MYSQL_HEALTH_CHECK_INTERVAL = 300.0 # 连接池健康检查间隔（秒），默认5分钟
MYSQL_POOL_REPAIR_ATTEMPTS = 3      # 连接池修复尝试次数，默认3次

# MongoDB 配置
MONGO_URI = 'mongodb://localhost:27017'
MONGO_DATABASE = 'mydb'
MONGO_COLLECTION = 'items'
```

**MySQL 冲突处理策略说明：**

Crawlo 的 MySQL 管道支持三种冲突处理策略，它们按照以下优先级顺序生效，**高优先级会覆盖低优先级**：

1. **`MYSQL_UPDATE_COLUMNS`（最高优先级）**：
   - 设置此项时，使用 `INSERT ... ON DUPLICATE KEY UPDATE` 语句
   - 当主键或唯一索引冲突时，仅更新指定的列
   - 示例：`MYSQL_UPDATE_COLUMNS = ('updated', 'modified')`

2. **`MYSQL_AUTO_UPDATE`（中等优先级）**：
   - 当 `MYSQL_UPDATE_COLUMNS` 未设置时生效
   - 使用 `REPLACE INTO` 语句，完全替换已存在的记录
   - 设置为 `True` 时启用

3. **`MYSQL_INSERT_IGNORE`（最低优先级）**：
   - 当前两个选项都未设置时生效
   - 使用 `INSERT IGNORE` 语句，遇到冲突时忽略重复数据
   - 设置为 `True` 时启用

**注意**：这三个参数是互斥的，只会应用优先级最高的那个设置。

### 5. 如何使用代理？

```
# settings.py

# 简单代理列表
PROXY_LIST = [
    "http://proxy1:8080",
    "http://proxy2:8080"
]

# 或使用动态代理 API
PROXY_API_URL = "http://your-proxy-api.com/get-proxy"
```

## MCP Server（AI 集成）

Crawlo 提供了 MCP (Model Context Protocol) Server，让 AI 助手（如 Claude、Cursor）可以直接调用 Crawlo 的抓取能力。

### 设计理念

Crawlo MCP 采用**薄适配层**设计：
- ✅ 快速响应（basic 模式 1-3 秒）
- ✅ 无状态请求（不占用内存）
- ✅ 三种抓取模式（basic/stealth/max-stealth）
- ✅ 直接调用 Crawlo 框架能力

### 安装

```bash
pip install crawlo[mcp]
```

### 配置 Claude Desktop

编辑 `claude_desktop_config.json`（Windows: `%APPDATA%/Claude/`，macOS: `~/Library/Application Support/Claude/`）：

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

重启 Claude Desktop 后，即可通过对话让 AI 自动调用 Crawlo。

### 可用工具

| 工具 | 功能 | 示例 |
|------|------|------|
| `fetch` | 抓取单个页面 | "帮我抓取 https://example.com" |
| `extract` | 正则提取内容 | "从页面中提取邮箱地址" |
| `spider` | 多页面并发抓取 | "抓取这 10 个商品页面" |
| `status` | 检查环境状态 | "检查 Crawlo 环境" |

### 三种抓取模式

| 模式 | 技术 | 速度 | 适用场景 |
|------|------|------|----------|
| `basic` | aiohttp | 1-3秒 | 普通网站 |
| `stealth` | DrissionPage | 3-10秒 | 有反爬的网站 |
| `max-stealth` | Camoufox | 10秒+ | Cloudflare 保护 |

### Python 直接使用

```python
import asyncio
from crawlo.mcp import QuickFetcher

async def main():
    fetcher = QuickFetcher()
    
    # 单页面抓取
    result = await fetcher.fetch(
        'https://example.com',
        mode='basic',           # basic/stealth/max-stealth
        format='markdown'       # html/markdown/text
    )
    print(result.content)
    
    # 多页面并发
    results = await fetcher.fetch_multiple(
        ['https://url1.com', 'https://url2.com'],
        concurrency=2
    )
    
    await fetcher.close()

asyncio.run(main())
```

## 反反爬虫功能

Crawlo 内置了强大的反反爬虫能力，自动绕过 Cloudflare 等常见防护。

### Cloudflare 绕过中间件

CloudflareBypassMiddleware 已默认集成到框架中，**无需手动配置即可自动工作**。

#### 自动检测机制

中间件会自动检测以下 Cloudflare 挑战页面：
- HTTP 状态码：403, 503, 520, 521, 522, 523, 524
- 页面特征：包含 `cloudflare`、`Checking your browser`、`DDoS protection` 等关键词

#### 绕过策略

检测到 Cloudflare 挑战后，中间件会：
1. 自动使用隐身浏览器重新请求
2. 支持多种浏览器后端（camoufox/playwright/drissionpage）
3. 智能重试机制

#### 配置方法

```python
# settings.py

# 选择绕过时使用的浏览器（默认 camoufox）
CLOUDFLARE_BYPASS_DOWNLOADER = 'camoufox'  # 推荐
# CLOUDFLARE_BYPASS_DOWNLOADER = 'playwright'
# CLOUDFLARE_BYPASS_DOWNLOADER = 'drissionpage'

# 可选：请求级别覆盖
yield Request(
    url='https://protected-site.com',
    meta={'cloudflare_bypass_downloader': 'camoufox'}
)
```

#### 三种浏览器对比

| 浏览器 | 反检测能力 | 速度 | 推荐场景 |
|--------|-----------|------|----------|
| **camoufox** | ⭐⭐⭐⭐⭐ | 中等 | Cloudflare 最强防护 |
| **playwright** | ⭐⭐⭐ | 快 | 一般反爬 |
| **drissionpage** | ⭐⭐⭐⭐ | 快 | 平衡选择 |

### 使用示例

```python
from crawlo import Spider
from crawlo.http import Request

class ProtectedSpider(Spider):
    name = 'protected_spider'
    start_urls = ['https://cf-protected-site.com']
    
    async def parse(self, response):
        # Cloudflare 绕过由中间件自动处理
        # 无需额外配置
        
        title = response.css('h1::text').get()
        yield {'title': title}
```

### 依赖安装

```bash
# Camoufox（推荐，最强反检测）
pip install camoufox

# Playwright
pip install playwright
playwright install chromium

# DrissionPage
pip install DrissionPage
```

### 注意事项

1. **无需手动启用**：中间件已在框架中默认注册
2. **仅在需要时触发**：只有检测到 Cloudflare 才会使用浏览器
3. **性能影响**：浏览器绕过会增加 3-10 秒延迟
4. **推荐方案**：优先使用 camoufox 获得最佳绕过效果

## 学习路径

如果您是 Crawlo 的新用户，建议按以下顺序学习：

1. **入门** - 阅读快速开始指南，运行第一个示例
2. **配置模式** - 学习三种配置模式，选择适合的模式（[配置模式指南](docs/tutorials/configuration_modes.md)）
3. **核心概念** - 了解框架架构和基本概念
4. **核心模块** - 深入学习引擎、调度器、处理器等核嘿组件
5. **功能模块** - 根据需求学习下载器、队列、过滤器等模块
6. **高级主题** - 掌握分布式部署、性能优化等高级功能

## 贡献

欢迎贡献！如果您想为 Crawlo 做出贡献，请访问我们的 [GitHub 仓库](https://github.com/crawl-coder/Crawlo)：

1. Fork [Crawlo 仓库](https://github.com/crawl-coder/Crawlo)
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交您的更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 发起 Pull Request

## 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

## 变更日志

### v1.6.2 (2026-04-07)

- **MCP Server 架构重构**：采用薄适配层设计
  - 删除冗余的 tools 目录（386+ 行代码）
  - 新建 quick_fetcher.py（152 行），支持三种抓取模式
  - 重写 server.py（202 行），暴露 4 个 MCP 工具
  - 验证通过：https://httpbin.org/get 抓取成功（200，1.10s）

- **反反爬虫功能完善**：
  - CloudflareBypassMiddleware 默认集成，自动工作
  - 支持 camoufox/playwright/drissionpage 三种浏览器
  - 自动检测 Cloudflare 挑战页面（403/503/52x）
  - 智能重试机制

- **文档补充**：
  - 添加 MCP Server 完整使用指南
  - 添加反反爬虫功能说明
  - 配置 Claude Desktop 教程
  - 三种抓取模式对比表

### v1.6.1 (2026-04-07)

- **下载器默认行为调整**：默认使用协议下载器，避免性能浪费
  - 移除自动检测 POST 请求和 URL 关键词的逻辑
  - 只有在明确配置时才使用动态下载器（Playwright）
  - 默认协议下载器改为 httpx（功能最全）

- **文档完善**：添加协议下载器和动态下载器完整使用指南
  - 协议下载器：默认行为，无需配置
  - 动态下载器：明确配置才启用
  - 智能滚动加载（scroll_to_bottom）
  - 点击翻页（click_and_wait）
  - 复杂页面交互操作
  - 单浏览器多标签页并发控制
  - InfoQ 动态页面完整示例

### v1.6.0 (2026-04-07)

- **中间件优先级重构**：采用双向对称设计
  - 请求阶段：数值越小，越先执行
  - 响应阶段：数值越大，越先执行（LIFO 模式）
  - 提供语义化常量：`MiddlewarePriority.CUSTOM`, `CUSTOM_REQUEST`, `CUSTOM_RESPONSE`
  - 详见 [中间件优先级策略](#中间件优先级策略)

- **配置格式统一**：`MIDDLEWARES`、`PIPELINES`、`EXTENSIONS` 统一使用字典格式
  - 旧格式：`PIPELINES = ['pipeline1', 'pipeline2']`
  - 新格式：`PIPELINES = {'pipeline1': 500, 'pipeline2': 600}`
  - 支持配置优先级，更灵活

- **指纹算法优化**：
  - 请求指纹改用 MD5（32字符），性能提升约 40%
  - 数据指纹保持 SHA256（64字符），确保数据准确性
  - 针对不同场景选择最优算法，兼顾性能与准确性

- **模块优化**：
  - 删除未使用的 `hook.py`（钩子系统）
  - 将 `priority.py` 从 `middleware` 移至 `utils`（非中间件功能）
  - `throttle.py` 作为可选中间件，用户可手动启用

- **日志格式优化**：
  - 修复 `enabled filters` 和 `enabled downloader` 日志异常换行
  - 统一组件启用信息的输出格式

- **导入优化**：
  - 将 `safe_get_config` 导入移至文件头部，消除重复导入
  - 优化 `downloader/__init__.py`、`memory_filter.py`、`queue_manager.py` 等文件

- **模板文件更新**：
  - 更新所有 6 个项目模板的配置示例
  - 添加优先级规则说明注释

### v1.2.0

- **Redis Key 重构**：引入 `RedisKeyManager` 统一管理 Redis Key 的生成和验证
  - 支持项目级别和爬虫级别的 Key 命名规范
  - 支持在同一个项目下区分不同的爬虫
  - 集成 `RedisKeyValidator` 确保 Key 命名规范一致性
  - 详细文档请参见 [Redis Key 重构说明](docs/redis_key_refactor.md)

---

<p align="center">
  <i>如有问题或建议，欢迎提交 <a href="https://github.com/crawl-coder/Crawlo/issues">Issue</a></i>
</p>