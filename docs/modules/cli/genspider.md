# genspider 命令

`genspider` 命令用于生成新的爬虫模板，快速创建爬虫类的基础结构。

## 命令语法

```bash
crawlo genspider <spider_name> <domain> [options]
```

### 参数说明

- `spider_name` - 爬虫名称（必需）
- `domain` - 目标域名（必需）
- `options` - 可选参数

## 使用示例

### 基本使用

```bash
# 生成基本爬虫
crawlo genspider myspider example.com

# 指定模块目录
crawlo genspider myspider example.com --module mymodule

# 生成爬虫到指定文件
crawlo genspider myspider example.com --output myspider.py
```

## 爬虫模板

### 默认模板

生成的爬虫模板包含基本结构：

```python
import crawlo
from crawlo.spider import Spider
from crawlo.items import Item

class MyspiderSpider(Spider):
    name = 'myspider'
    allowed_domains = ['example.com']
    start_urls = ['http://example.com/']

    def parse(self, response):
        # 解析逻辑
        pass
```

### 自定义模板

```bash
# 使用自定义模板
crawlo genspider myspider example.com --template advanced

# 列出可用模板
crawlo genspider --list-templates
```

## 配置选项

`genspider` 命令支持以下选项：

| 选项 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| --module | string | 'spiders' | 爬虫模块目录 |
| --output | string | - | 输出文件路径 |
| --template | string | 'default' | 使用的模板名称 |
| --list-templates | flag | - | 列出所有可用模板 |
| --force | flag | - | 强制覆盖已存在的文件 |
| --verbose | flag | - | 显示详细输出 |

## 模板类型

### 1. 默认模板 (default)

```python
class SpiderName(Spider):
    name = 'spidername'
    start_urls = ['http://example.com/']
    
    def parse(self, response):
        pass
```

### 2. 高级模板 (advanced)

```python
class SpiderName(Spider):
    name = 'spidername'
    allowed_domains = ['example.com']
    start_urls = ['http://example.com/']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.custom_setting = kwargs.get('custom_setting')
    
    def parse(self, response):
        # 提取数据
        yield Item(data=response.text)
        
        # 跟进链接
        for link in response.extract_attrs('a', 'href'):
            yield Request(url=link, callback=self.parse)
```

### 3. API 模板 (api)

```python
class SpiderName(Spider):
    name = 'spidername'
    api_base_url = 'https://api.example.com'
    
    def start_requests(self):
        yield Request(
            url=f'{self.api_base_url}/data',
            headers={'Authorization': 'Bearer token'}
        )
    
    def parse(self, response):
        data = response.json()
        for item in data['items']:
            yield Item(**item)
```

## 最佳实践

### 1. 爬虫命名

```bash
# 使用描述性的爬虫名称
crawlo genspider product_spider example.com
crawlo genspider news_spider news.example.com
crawlo genspider user_spider social.example.com
```

### 2. 域名配置

```bash
# 正确配置域名
crawlo genspider myspider example.com
crawlo genspider myspider subdomain.example.com
crawlo genspider myspider example.com --allowed-domains example.com,api.example.com
```

### 3. 模板选择

```bash
# 根据需求选择合适的模板
crawlo genspider myspider example.com --template default      # 简单爬虫
crawlo genspider myspider example.com --template advanced     # 复杂爬虫
crawlo genspider myspider api.example.com --template api      # API 爬虫
```

## 故障排除

### 常见问题

1. **文件已存在**
   ```bash
   # 错误: File already exists
   # 解决: 使用 --force 选项或选择其他名称
   crawlo genspider myspider example.com --force
   ```

2. **模板不存在**
   ```bash
   # 错误: Template not found
   # 解决: 检查模板名称或使用默认模板
   crawlo genspider myspider example.com --template default
   ```

3. **模块目录不存在**
   ```bash
   # 错误: Module directory not found
   # 解决: 创建目录或使用现有目录
   mkdir mymodule
   crawlo genspider myspider example.com --module mymodule
   ```

### 调试技巧

```bash
# 使用详细模式查看生成过程
crawlo genspider myspider example.com --verbose

# 检查模板列表
crawlo genspider --list-templates

# 预览生成内容而不创建文件
crawlo genspider myspider example.com --dry-run
```