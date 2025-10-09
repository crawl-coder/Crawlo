# list 命令

`list` 命令用于列出项目中所有可用的爬虫，帮助用户了解项目结构和可用的爬虫。

## 命令语法

```bash
crawlo list [options]
```

### 参数说明

- `options` - 可选参数

## 使用示例

### 基本使用

```bash
# 列出所有爬虫
crawlo list

# 指定项目目录
crawlo list --project-dir /path/to/project

# 以 JSON 格式输出
crawlo list --format json
```

### 高级用法

```bash
# 详细信息
crawlo list --verbose

# 只显示爬虫名称
crawlo list --names-only

# 过滤爬虫
crawlo list --filter "news_*"
```

## 配置选项

`list` 命令支持以下选项：

| 选项 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| --project-dir | string | 当前目录 | 项目目录路径 |
| --format | string | 'table' | 输出格式 (table, json, csv) |
| --verbose | flag | - | 显示详细信息 |
| --names-only | flag | - | 只显示爬虫名称 |
| --filter | string | None | 爬虫名称过滤器 |
| --sort | string | 'name' | 排序方式 (name, created) |

## 输出格式

### 表格格式（默认）

```bash
$ crawlo list
+----+-------------+------------------+------------+
| 序号 | 爬虫名称     | 描述             | 创建时间   |
+----+-------------+------------------+------------+
| 1  | news_spider | 新闻网站爬虫      | 2023-01-01 |
| 2  | product_spider | 商品信息爬虫    | 2023-01-02 |
+----+-------------+------------------+------------+
```

### JSON 格式

```bash
$ crawlo list --format json
[
  {
    "name": "news_spider",
    "description": "新闻网站爬虫",
    "created": "2023-01-01",
    "file": "spiders/news_spider.py"
  },
  {
    "name": "product_spider",
    "description": "商品信息爬虫",
    "created": "2023-01-02",
    "file": "spiders/product_spider.py"
  }
]
```

### CSV 格式

```bash
$ crawlo list --format csv
序号,爬虫名称,描述,创建时间,文件路径
1,news_spider,新闻网站爬虫,2023-01-01,spiders/news_spider.py
2,product_spider,商品信息爬虫,2023-01-02,spiders/product_spider.py
```

## 爬虫发现机制

### 自动发现

```python
# settings.py 中配置爬虫模块
SPIDER_MODULES = [
    'myproject.spiders',
    'myproject.custom_spiders',
]

# 爬虫必须继承 Spider 基类
class MySpider(Spider):
    name = 'my_spider'
```

### 命名约定

```bash
# 推荐的爬虫文件命名
spiders/
├── news_spider.py          # 新闻爬虫
├── product_spider.py       # 商品爬虫
├── user_spider.py          # 用户爬虫
└── api_data_spider.py      # API 数据爬虫
```

## 详细信息显示

### 使用 --verbose 选项

```bash
$ crawlo list --verbose
爬虫列表:
  1. news_spider
     文件: spiders/news_spider.py
     类名: NewsSpider
     描述: 新闻网站爬虫
     创建时间: 2023-01-01
     最后修改: 2023-01-15

  2. product_spider
     文件: spiders/product_spider.py
     类名: ProductSpider
     描述: 商品信息爬虫
     创建时间: 2023-01-02
     最后修改: 2023-01-10
```

## 过滤和排序

### 名称过滤

```bash
# 过滤包含特定字符串的爬虫
crawlo list --filter "news"

# 使用通配符过滤
crawlo list --filter "news_*"

# 正则表达式过滤
crawlo list --filter "^news.*spider$"
```

### 排序选项

```bash
# 按名称排序（默认）
crawlo list --sort name

# 按创建时间排序
crawlo list --sort created
```

## 最佳实践

### 1. 项目结构管理

```bash
# 按功能组织爬虫
spiders/
├── news/
│   ├── cnn_spider.py
│   ├── bbc_spider.py
│   └── reuters_spider.py
├── ecommerce/
│   ├── amazon_spider.py
│   ├── ebay_spider.py
│   └── aliexpress_spider.py
└── social/
    ├── twitter_spider.py
    └── facebook_spider.py
```

### 2. 爬虫命名规范

```python
# 使用描述性的爬虫名称
class NewsSpider(Spider):           # ✅ 好
    name = 'news_spider'

class ProductSpider(Spider):        # ✅ 好
    name = 'product_spider'

class Spider1(Spider):              # ❌ 不好
    name = 'spider1'
```

### 3. 文档化爬虫

```python
class NewsSpider(Spider):
    """新闻网站爬虫
    
    用于爬取新闻网站的文章内容，包括标题、正文、发布时间等信息。
    
    支持的网站:
    - news.example.com
    - blog.example.com
    """
    name = 'news_spider'
```

## 故障排除

### 常见问题

1. **未发现爬虫**
   ```bash
   # 问题: No spiders found
   # 解决: 检查爬虫模块配置和文件结构
   # 确保 settings.py 中配置了 SPIDER_MODULES
   ```

2. **爬虫名称冲突**
   ```bash
   # 问题: Duplicate spider names found
   # 解决: 确保每个爬虫有唯一的名称
   # 检查所有爬虫文件中的 name 属性
   ```

3. **权限问题**
   ```bash
   # 问题: Permission denied
   # 解决: 检查目录和文件权限
   ls -la spiders/
   ```

### 调试技巧

```bash
# 显示详细信息以调试问题
crawlo list --verbose

# 检查特定项目目录
crawlo list --project-dir /path/to/project --verbose

# 以不同格式输出便于分析
crawlo list --format json | jq '.[] | .name'
```