```markdown
# crawlo 命令行使用说明

`crawlo` 框架提供了强大的命令行工具，用于快速创建和管理爬虫项目，其使用方式与 Scrapy 高度相似。

## 可用命令

在任意目录下运行 `crawlo` 可以查看所有可用命令：

```bash
crawlo
```

输出：
```
Usage: crawlo <command> [options]
Available commands: startproject, genspider
```

---

### 1. `crawlo startproject`

创建一个新的爬虫项目。

**语法**：
```bash
crawlo startproject <project_name>
```

**示例**：
```bash
crawlo startproject my_project
```

此命令会创建一个名为 `my_project` 的目录，其结构如下：
```
my_project/
├── crawlo.cfg
├── logs/
├── my_project/
│   ├── __init__.py
│   ├── items.py
│   ├── middlewares.py
│   ├── pipelines.py
│   ├── settings.py
│   └── spiders/
│       └── __init__.py
```

---

### 2. `crawlo genspider`

在已创建的项目中生成一个爬虫模板。

**语法**：
```bash
crawlo genspider <spider_name> <domain>
```

**示例**：
```bash
cd my_project
crawlo genspider baidu baidu.com
```

此命令会在 `my_project/spiders/` 目录下创建一个名为 `baidu.py` 的爬虫文件，并自动填充基本的类名、域名和起始 URL。

---

### 常用工作流

一个典型的 `crawlo` 项目开发流程如下：

```bash
# 1. 创建项目
crawlo startproject my_project

# 2. 进入项目目录
cd my_project

# 3. 生成一个爬虫
crawlo genspider example example.com

# 4. 编辑爬虫文件 (my_project/spiders/example.py) 以添加解析逻辑
# 5. 运行爬虫 (需要实现 CrawlerProcess)
```
```