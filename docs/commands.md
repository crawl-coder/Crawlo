---

# 🐞 `crawlo` 命令行工具使用说明

> 本指南介绍如何使用 `crawlo` 框架提供的命令行工具，帮助你快速管理爬虫项目。

## 🔧 安装与初始化

首先确保已安装 `crawlo` 框架，并进入项目根目录。

```bash
pip install crawlo
cd your_project_root
```

---

## ✅ 可用命令列表

| 命令 | 功能 | 说明 |
|------|------|------|
| `crawlo startproject <project_name>` | 创建新项目 | 初始化项目结构 |
| `crawlo genspider <spider_name>` | 生成新爬虫模板 | 快速创建 Spider 类 |
| `crawlo list` | 列出所有爬虫 | 显示已注册的爬虫名称和类名 |
| `crawlo check` | 检查爬虫定义合规性 | 验证 `name`、`start_requests` 等是否完整 |
| `crawlo run <spider_name>` | 运行指定爬虫 | 启动单个爬虫 |
| `crawlo stats` | 查看爬虫统计信息 | 显示最近运行的统计结果 |

---

## 📂 项目结构示例

```text
myproject/
├── crawlo.cfg
├── myproject/
│   ├── __init__.py
│   └── spiders/
│       ├── __init__.py
│       └── baidu.py
└── ...
```

`crawlo.cfg` 示例：

```ini
[settings]
default = myproject.settings
```

---

## 🚀 使用方法详解

### 1. 创建新项目

```bash
crawlo startproject myproject
```

> 创建一个名为 `myproject` 的新项目，包含基本配置和目录结构。

---

### 2. 生成爬虫模板

```bash
crawlo genspider baidu
```

> 自动生成 `spiders/baidu.py` 文件，内容如下：

```python
from crawlo.spider import Spider

class BaiduSpider(Spider):
    name = "baidu"
    start_urls = ["https://www.baidu.com"]

    def parse(self, response):
        # 在这里编写解析逻辑
        pass
```

---

### 3. 列出所有爬虫

```bash
crawlo list
```

> 输出所有已注册的爬虫：

```text
📋 Found 2 spider(s):
--------------------------------------------------
🕷️  baidu                BaiduSpider               (spiders.baidu)
🕷️  news                 NewsSpider                (spiders.news)
--------------------------------------------------
```

---

### 4. 检查爬虫定义

```bash
crawlo check
```

> 检查所有爬虫是否满足基本要求：

```text
🔍 Checking 2 spider(s)...
--------------------------------------------------
✅ baidu                BaiduSpider               (OK)
❌ news                 NewsSpider                • missing 'start_requests' method
--------------------------------------------------
⚠️  Some spiders have issues. Please fix them.
```

---

### 5. 运行爬虫

```bash
crawlo run baidu
```

> 启动名为 `baidu` 的爬虫：

```text
🚀 Starting spider: baidu
📁 Project: myproject
📦 Module: myproject.spiders.baidu
🕷️  Class: BaiduSpider
--------------------------------------------------
[1/1] 启动爬虫: BaiduSpider
[1/1] 爬虫完成: BaiduSpider
✅ Spider completed successfully!
```

---

### 6. 查看统计信息

```bash
crawlo stats
```

> 查看最近运行的爬虫统计：

```text
📊 Recent Spider Statistics:
--------------------------------------------------
🕷️  baidu
    requests_count             5
    responses_count            5
    items_scraped              3
    failed_requests            0
    download_latency           0.2s
--------------------------------------------------
```

或查看特定爬虫：

```bash
crawlo stats baidu
```

---

## 💡 提示与建议

- ✅ 所有命令都支持 `--help` 查看详细帮助；
- ✅ 爬虫必须继承 `Spider` 并定义 `name` 属性；
- ✅ `start_requests` 方法是必需的（即使为空）；
- ✅ 支持通过 `crawlo.cfg` 配置项目包名；
- ✅ 自动发现 `spiders/` 目录下的所有模块；

---

## 📚 附录：命令源码位置

| 命令 | 源码文件 |
|------|----------|
| `startproject` | `crawlo/commands/startproject.py` |
| `genspider` | `crawlo/commands/genspider.py` |
| `list` | `crawlo/commands/list.py` |
| `check` | `crawlo/commands/check.py` |
| `run` | `crawlo/commands/run.py` |
| `stats` | `crawlo/commands/stats.py` |

---

## 🛠️ 未来扩展计划

- `crawlo shell` —— 交互式调试环境；
- `crawlo deploy` —— 部署到远程服务器；
- `crawlo monitor` —— 实时监控运行状态；
- `crawlo export` —— 导出数据为 JSON/CSV；

---

> 🚀 `crawlo` 是一个现代化、可扩展的 Python 爬虫框架，致力于提供类似 Scrapy 的体验，但更轻量、更易用。

欢迎反馈！