# ⚙️ 参数配置详解

Crawlo 所有的全局配置都在项目的 `settings.py` 中进行管理。

---

## 1. 运行模式与并发配置

Crawlo 支持根据业务场景灵活配置运行模式，从单机开发测试到分布式大规模生产环境。

### 1.1 场景化配置推荐

| 场景 | 运行模式 | 爬虫数量 | CONCURRENCY | 特点 |
| :--- | :--- | :--- | :--- | :--- |
| **开发测试** | Standalone | 1 个 | 8 | 简单快速，无需 Redis |
| **小规模生产** | Standalone | 3-5 个 | 16 | 单机资源充分利用 |
| **大规模生产** | Distributed | 10+ 个 | 32 | 需要 Redis，水平扩展 |

### 1.2 配置示例

#### 开发测试配置（默认）
```python
from crawlo.config import CrawloConfig

config = CrawloConfig.auto(
    project_name='myproject',
    concurrency=8,              # 单个爬虫并发请求数
    download_delay=1.0,         # 下载延迟（秒）
    max_running_spiders=1       # 最大同时运行爬虫数
)
```

#### 小规模生产配置
```python
config = CrawloConfig.auto(
    project_name='myproject',
    concurrency=16,             # 提高单个爬虫并发
    download_delay=0.5,         # 适当降低延迟
    max_running_spiders=5       # 允许同时运行5个爬虫
)
```

#### 大规模生产配置（分布式）
```python
config = CrawloConfig.distributed(
    redis_host='127.0.0.1',     # Redis主机地址
    redis_port=6379,            # Redis端口
    project_name='myproject',
    concurrency=32,             # 高并发
    download_delay=0.1,         # 低延迟
    max_running_spiders=20      # 大量爬虫并发
)
```

### 1.3 核心参数说明

| 参数 | 默认值 | 说明 |
| :--- | :--- | :--- |
| `PROJECT_NAME` | `""` | 项目唯一标识。用于生成日志文件前缀和 Redis Key。 |
| `CRAWLO_MODE` | `"auto"` | 运行模式。`standalone`（单机）、`distributed`（分布式）、`auto`（自动检测 Redis 并切换模式）。 |
| `CONCURRENCY` | `8` | 单个爬虫的并发请求数。控制同时抓取的网页数量。 |
| `MAX_RUNNING_SPIDERS` | `1` / `10` | 同时运行的最大爬虫数量。Standalone 模式默认 1，Distributed 模式默认 10。 |
| `DOWNLOAD_DELAY` | `1.0` | 每个请求之间的间隔延迟（秒）。根据目标网站反爬强度调整。 |

---

## 2. 下载与频率控制

| 参数 | 默认值 | 说明 |
| :--- | :--- | :--- |
| `DOWNLOAD_DELAY` | `0.5` | 每个请求之间的间隔延迟（秒）。 |
| `RANDOMNESS` | `True` | 是否开启随机延迟抖动。 |
| `RANDOM_RANGE` | `[0.5, 1.5]` | 随机延迟的倍数范围。 |
| `DOWNLOAD_TIMEOUT` | `30` | 网络请求的超时时间（秒）。 |
| `DOWNLOAD_RETRY_TIMES` | `3` | 下载层级的重试次数。 |

---

## 3. 混合下载器 (Hybrid) 配置

这是 Crawlo 的杀手级功能，根据 URL 或域名自动选择是使用 HTTP 库还是浏览器渲染。

| 参数 | 默认值 | 说明 |
| :--- | :--- | :--- |
| `DOWNLOADER` | `"hybrid"` | 默认启用混合下载器。 |
| `HYBRID_DEFAULT_PROTOCOL_DOWNLOADER` | `"httpx"` | 默认使用的协议库 (`httpx`, `aiohttp`, `curl_cffi`)。 |
| `HYBRID_DYNAMIC_DOMAINS` | `[]` | 配置后，列表中的域名将自动使用浏览器渲染。 |
| `HYBRID_DYNAMIC_URL_PATTERNS` | `[]` | 配置后，匹配这些正则表达式的 URL 将使用浏览器渲染。 |

---

## 4. 浏览器渲染 (Playwright) 配置

当触发动态下载器时生效。

| 参数 | 默认值 | 说明 |
| :--- | :--- | :--- |
| `PLAYWRIGHT_HEADLESS` | `True` | 是否开启无头模式（不显示浏览器窗口）。 |
| `PLAYWRIGHT_SINGLE_BROWSER_MODE` | `True` | 是否复用浏览器实例（大幅减少内存消耗，强烈建议开启）。 |
| `PLAYWRIGHT_MAX_PAGES_PER_BROWSER` | `10` | 一个浏览器实例内最多开启的标签页数量。 |
| `PLAYWRIGHT_BLOCK_RESOURCES` | `["image", "font", "media"]` | 屏蔽无关资源以加速加载。 |
| `PLAYWRIGHT_STEALTH_LEVEL` | `"basic"` | 反检测级别：`none`, `basic`, `advanced`（全指纹伪造）。 |

---

## 5. 数据存储 (Pipeline) 配置

| 参数 | 默认值 | 说明 |
| :--- | :--- | :--- |
| `PIPELINES` | `{}` | 启用的管道列表。键为管道类路径，值为优先级（0-1000）。 |
| `MYSQL_HOST` | `"127.0.0.1"` | MySQL 数据库地址。 |
| `MYSQL_BATCH_SIZE` | `200` | 批量插入的数据量，大幅提升入库速度。 |
| `MONGO_URI` | `""` | MongoDB 连接字符串。 |

---

## 6. 通知系统配置

开启后可在抓取完成或出错时发送通知。

| 参数 | 默认值 | 说明 |
| :--- | :--- | :--- |
| `NOTIFICATION_ENABLED` | `False` | 是否全局开启通知系统。 |
| `NOTIFICATION_CHANNELS` | `[]` | 启用的渠道列表：`feishu`, `dingtalk`, `email`, `wecom`, `sms`。 |

---

## 7. 定时任务配置

| 参数 | 默认值 | 说明 |
| :--- | :--- | :--- |
| `SCHEDULER_ENABLED` | `False` | 是否开启内置定时任务调度器。 |
| `SCHEDULER_JOBS` | `[]` | 任务列表。支持 Cron 表达式。 |

---

## 8. 自适应选择器配置

| 参数 | 默认值 | 说明 |
| :--- | :--- | :--- |
| `ADAPTIVE_STORAGE_BACKEND` | `"sqlite"` | 元素指纹存储后端。`sqlite` 或 `redis`。 |
| `ADAPTIVE_SIMILARITY_THRESHOLD` | `0.0` | 相似度阈值（0-100）。设置后低于该分数的匹配将不予采纳。 |

---

## 📖 小贴士
- **优先加载顺序**：项目中的 `settings.py` 会覆盖框架默认配置。
- **命令行覆盖**：可以使用 `crawlo run myspider -s CONCURRENCY=20` 这种方式临时修改配置。
