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

### 2.1 简单配置（推荐小型项目）

| 参数 | 默认值 | 说明 |
| :--- | :--- | :--- |
| `DOWNLOAD_DELAY` | `0.5` | 每个请求之间的间隔延迟（秒）。 |
| `RANDOMNESS` | `True` | 是否开启随机延迟/智能调节。 |
| `RANDOM_RANGE` | `[0.5, 1.5]` | 随机延迟范围倍数（仅用于日志显示）。 |

**示例**：
```python
# 固定延迟 2 秒
DOWNLOAD_DELAY = 2.0
RANDOMNESS = False

# 或随机延迟 1-3 秒
DOWNLOAD_DELAY = 2.0
RANDOMNESS = True
RANDOM_RANGE = [0.5, 1.5]
```

### 2.2 域名级配置（可选）

| 参数 | 默认值 | 说明 |
| :--- | :--- | :--- |
| `DOWNLOAD_DELAY_OVERRIDES` | `{}` | 域名级特定配置，支持不同域名不同延迟。 |

> ⚠️ **注意**：早期版本的 `THROTTLE_*` 参数已移除，统一使用 `DOWNLOAD_DELAY` 相关参数。

**示例**：
```python
# 全局默认
DOWNLOAD_DELAY = 1.0

# 域名级控制
DOWNLOAD_DELAY_OVERRIDES = {
    'example.com': {'delay': 2.0},  # 慢速网站
    'api.example.com': {'delay': 0.1},  # API 快速
}
```

### 2.3 其他下载配置

| 参数 | 默认值 | 说明 |
| :--- | :--- | :--- |
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

## 5. CloakBrowser（隐身浏览器）配置

CloakBrowser 是源码级修补的 Chromium，用于高强度反爬站点。安装：`pip install crawlo[stealth]`

### 场景化配置

**基础使用**：
```python
DOWNLOADER = 'crawlo.downloader.cloakbrowser_downloader.CloakBrowserDownloader'
CLOAKBROWSER_HEADLESS = True
CLOAKBROWSER_BLOCK_RESOURCES = ['image', 'font', 'media']
```

**高对抗站点**（Cloudflare / reCAPTCHA）：
```python
CLOAKBROWSER_HEADLESS = False       # 有头模式
CLOAKBROWSER_HUMANIZE = True        # 类人行为
CLOAKBROWSER_GEOIP = True           # 时区自动匹配
CLOAKBROWSER_PROXY = 'socks5://user:pass@proxy:1080'
```

### 核心参数

| 参数 | 默认值 | 说明 |
| :--- | :--- | :--- |
| `CLOAKBROWSER_HEADLESS` | `True` | 无头模式。高强度站点建议 `False` |
| `CLOAKBROWSER_HUMANIZE` | `False` | 类人行为模拟（鼠标/键盘/滚动） |
| `CLOAKBROWSER_HUMAN_PRESET` | `"default"` | 预设：`"default"` 或 `"careful"` |
| `CLOAKBROWSER_GEOIP` | `False` | 从代理 IP 自动检测时区和语言 |
| `CLOAKBROWSER_STEALTH_ARGS` | `True` | 启用默认隐身参数 |
| `CLOAKBROWSER_FINGERPRINT` | `None` | 固定指纹种子（int/str），用于会话持久化 |
| `CLOAKBROWSER_PROXY` | `None` | 代理地址，支持 HTTP/SOCKS5 |
| `CLOAKBROWSER_TIMEOUT` | `30000` | 总超时（毫秒） |
| `CLOAKBROWSER_MAX_PAGES` | `10` | 最大标签页数 |
| `CLOAKBROWSER_BLOCK_RESOURCES` | `["image","font","media"]` | 屏蔽的资源类型 |
| `CLOAKBROWSER_AUTO_SCROLL` | `False` | 自动滚动 |
| `CLOAKBROWSER_WAIT_STRATEGY` | `"auto"` | 等待策略：`auto` / `networkidle` / `domcontentloaded` |
| `CLOAKBROWSER_PERSISTENT_CONTEXT` | `False` | 使用持久化浏览器上下文 |
| `CLOAKBROWSER_USER_DATA_DIR` | `None` | 持久化数据目录 |

> 完整配置项和示例详见 [CloakBrowser 使用指南](../cloakbrowser-guide.md)。

---

## 6. 数据存储 (Pipeline) 配置

| 参数 | 默认值 | 说明 |
| :--- | :--- | :--- |
| `PIPELINES` | `{}` | 启用的管道列表。键为管道类路径，值为优先级（0-1000）。 |
| `MYSQL_HOST` | `"127.0.0.1"` | MySQL 数据库地址。 |
| `MYSQL_BATCH_SIZE` | `200` | 批量插入的数据量，大幅提升入库速度。 |
| `MONGO_URI` | `""` | MongoDB 连接字符串。 |

---

## 7. 通知系统配置

开启后可在抓取完成或出错时发送通知。

| 参数 | 默认值 | 说明 |
| :--- | :--- | :--- |
| `NOTIFICATION_ENABLED` | `False` | 是否全局开启通知系统。 |
| `NOTIFICATION_CHANNELS` | `[]` | 启用的渠道列表：`feishu`, `dingtalk`, `email`, `wecom`, `sms`。 |

---

## 8. 定时任务配置

| 参数 | 默认值 | 说明 |
| :--- | :--- | :--- |
| `SCHEDULER_ENABLED` | `False` | 是否开启内置定时任务调度器。 |
| `SCHEDULER_JOBS` | `[]` | 任务列表。支持 Cron 表达式。 |

---

## 9. 调度策略配置

调度策略控制请求的出队顺序，影响爬虫是"先详后列"还是"先列后详"。

| 参数 | 默认值 | 说明 |
| :--- | :--- | :--- |
| `DEPTH_PRIORITY` | `1` | 深度优先级调整系数，控制优先级如何随请求深度变化。 |

**配置值含义**：

| 配置值 | 策略 | 效果 | 适用场景 |
|--------|------|------|---------|
| `1`（默认） | 深度优先 | 深度越深优先级越高 → 详情页先出队 | 列表→详情型爬虫，解决"先列后详"问题 |
| `-1` | 广度优先 | 深度越深优先级越低 → 列表页先出队 | 逐层抓取，确保层级完整 |
| `0` | 不调整 | 不按深度调整优先级 | 完全自定义优先级 |

**示例**：

```python
# settings.py

# 深度优先（详情页优先出队，解决"先列后详"问题）—— 默认值
DEPTH_PRIORITY = 1

# 广度优先（列表页优先出队，同层级先处理完）
DEPTH_PRIORITY = -1

# 不按深度调整优先级
DEPTH_PRIORITY = 0
```

**原理说明**：

Crawlo 使用优先级队列（min-heap），内部 priority 值越小越先出队。用户设置 `priority` 时数值越大越优先，框架自动取反存储。

```
优先级计算公式：内部 priority = -用户priority - depth × DEPTH_PRIORITY

示例（DEPTH_PRIORITY = 1，用户 priority = 0）：
  列表页 (depth=1) → 内部 priority = 0 - 1×1 = -1
  详情页 (depth=2) → 内部 priority = 0 - 2×1 = -2
  -2 < -1 → 详情页先出队 ✅ 深度优先
```

> **注意**：`depth` 由框架自动传播，无需在 Spider 中手动设置。`start_requests` 的 depth 默认为 1，Spider 回调产生的子请求 depth 自动为 `parent.depth + 1`。

---

## 10. 监控与日志配置

### 9.1 间隔日志监控（LogIntervalExtension）

Crawlo 默认启用间隔日志监控，每 60 秒输出一次爬虫运行状态，包括抓取页数、Item 数量、队列大小和背压状态。

| 参数 | 默认值 | 说明 |
| :--- | :--- | :--- |
| `INTERVAL` | `60` | 间隔日志的输出频率（秒）。生产环境建议 60 秒，调试时可设置为 10 秒。 |

**示例**：
```python
# 生产环境（默认）
INTERVAL = 60  # 每分钟输出一次监控日志

# 调试环境
INTERVAL = 10  # 每 10 秒输出一次监控日志
```

**日志输出示例**：
```
2026-04-18 22:39:11 - Crawled 82 pages (at 82 pages/10s), Got 31 items (at 31 items/10s), Queue: 166 pending, BP: off (6%)
2026-04-18 22:39:21 - Crawled 152 pages (at 70 pages/10s), Got 66 items (at 35 items/10s), Queue: 131 pending, BP: off (4%)
```

**智能检测**：
- ✅ 爬虫运行时：按 INTERVAL 间隔正常输出监控日志
- ✅ 爬虫空闲时：自动跳过，不输出无意义的日志
- ✅ 定时任务模式：正常工作，不受 `SCHEDULER_ENABLED` 影响

---

## 11. 自适应选择器配置

| 参数 | 默认值 | 说明 |
| :--- | :--- | :--- |
| `ADAPTIVE_STORAGE_BACKEND` | `"sqlite"` | 元素指纹存储后端。`sqlite` 或 `redis`。 |
| `ADAPTIVE_SIMILARITY_THRESHOLD` | `0.0` | 相似度阈值（0-100）。设置后低于该分数的匹配将不予采纳。 |

---

## 📖 小贴士
- **优先加载顺序**：项目中的 `settings.py` 会覆盖框架默认配置。
- **命令行覆盖**：可以使用 `crawlo run myspider -s CONCURRENCY=20` 这种方式临时修改配置。
