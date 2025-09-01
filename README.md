# 🕷️ Crawlo - 轻量级异步爬虫框架

> 一个简洁、易用、可扩展的 Python 异步爬虫框架，灵感源自 Scrapy，但更轻量、更易上手。

🚀 支持命令行操作、爬虫生成、合规检查、运行监控与统计分析，适合快速开发中小型爬虫项目。

---

## 📦 特性

- ✅ **命令行驱动**：`crawlo startproject`, `crawlo genspider` 等
- ✅ **自动发现爬虫**：无需手动注册，自动加载 `spiders/` 模块
- ✅ **异步核心**：基于 `asyncio` 实现高并发抓取
- ✅ **灵活配置**：通过 `crawlo.cfg` 和 `settings.py` 管理项目
- ✅ **爬虫检查**：`crawlo check` 验证爬虫定义是否合规
- ✅ **运行统计**：`crawlo stats` 查看历史运行指标（持久化存储）
- ✅ **批量运行**：支持 `crawlo run all` 启动所有爬虫
- ✅ **日志与调试**：结构化日志输出，便于排查问题

---

## 🚀 快速开始

### 1. 安装 Crawlo

```bash
pip install crawlo
```

> ⚠️ 当前为开发阶段，建议使用源码安装：
>
> ```bash
> git clone https://github.com/yourname/crawlo.git
> pip install -e crawlo
> ```

### 2. 创建项目

```bash
crawlo startproject myproject
cd myproject
```

生成项目结构：

```
myproject/
├── crawlo.cfg
├── myproject/
│   ├── __init__.py
│   ├── settings.py
│   └── spiders/
│       ├── __init__.py
│       └── (你的爬虫将在这里)
```

### 3. 生成爬虫

```bash
crawlo genspider example example.com
```

生成 `spiders/example.py`：

```python
class ExampleSpider(Spider):
    name = "example"
    start_urls = ["https://example.com"]
    
    def parse(self, response):
        # 解析逻辑
        pass
```

### 4. 检查爬虫合规性

```bash
crawlo check
```

输出示例：

```
🔍 Checking 1 spider(s)...
✅ example              ExampleSpider (OK)
🎉 All spiders are compliant!
```

### 5. 运行爬虫

```bash
# 运行单个爬虫
crawlo run example

# 运行所有爬虫
crawlo run all
```

### 6. 查看运行统计

```bash
crawlo stats
```

查看最近一次运行的请求、响应、项目数等指标：

```
📊 Recent Spider Statistics (last run):
🕷️  example
    downloader/request_count           1
    item_scraped_count                 1
    log_count/INFO                     7
```

---

## 🛠️ 命令列表

| 命令 | 说明 |
|------|------|
| `crawlo startproject <name>` | 创建新项目 |
| `crawlo genspider <name> <domain>` | 生成爬虫模板 |
| `crawlo list` | 列出所有已注册的爬虫 |
| `crawlo check` | 检查爬虫定义是否合规 |
| `crawlo run <spider_name>` | 运行指定爬虫 |
| `crawlo run all` | 运行所有爬虫 |
| `crawlo stats` | 查看最近运行的统计信息 |
| `crawlo stats <spider_name>` | 查看指定爬虫的统计 |

---

## 📁 项目结构说明

```ini
# crawlo.cfg
[settings]
default = myproject.settings
```

```python
# settings.py
BOT_NAME = "myproject"
LOG_LEVEL = "DEBUG"
CONCURRENT_REQUESTS = 3
DOWNLOAD_DELAY = 1.0
# 其他配置...
```

---

## 📊 统计持久化

每次爬虫运行结束后，统计信息会自动保存到：

```
logs/stats/<spider_name>_YYYYMMDD_HHMMSS.json
```

可通过 `crawlo stats` 命令读取，支持跨进程查看。

---

## 🧪 开发者提示

- 确保 `spiders/__init__.py` 中导入了你的爬虫类，否则无法被发现
- 使用 `get_project_root()` 自动定位项目根目录（通过查找 `crawlo.cfg`）
- 所有命令行工具均支持直接运行：`python -m crawlo.commands.list`

---

