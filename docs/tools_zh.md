# 工具包

Crawlo框架提供了一个全面的工具包，封装了在网页抓取场景中常用的各类工具。该包包括日期处理、数据清洗、数据验证、请求处理、反爬虫措施和分布式协调工具。

## 包结构

工具包包含以下模块：

1. **日期工具** - 日期解析和格式化工具
2. **数据清洗工具** - 文本清洗、数据提取和格式化工具
3. **数据验证工具** - 常见格式的数据验证工具
4. **请求处理工具** - URL构建和请求准备工具
5. **反爬虫工具** - 处理反爬虫机制的工具
6. **分布式协调工具** - 分布式爬取协调工具

## 使用方法

### 导入工具

```python
from crawlo.tools import (
    # 日期工具
    TimeUtils,
    parse_time,
    format_time,
    time_diff,
    
    # 数据清洗工具
    TextCleaner,
    DataFormatter,
    clean_text,
    format_currency,
    extract_emails,
    
    # 数据验证工具
    DataValidator,
    validate_email,
    validate_url,
    validate_phone,
    
    # 请求处理工具
    RequestHandler,
    build_url,
    add_query_params,
    merge_headers,
    
    # 反爬虫工具
    AntiCrawler,
    get_random_user_agent,
    rotate_proxy,
    
    # 分布式协调工具
    DistributedCoordinator,
    generate_task_id,
    get_cluster_info
)
```

### 日期工具

```python
from crawlo.tools import parse_time, format_time, time_diff

# 解析时间
time_str = "2025-09-10 14:30:00"
parsed_time = parse_time(time_str)

# 格式化时间
formatted_time = format_time(parsed_time, "%Y-%m-%d")

# 计算时间差
time_str2 = "2025-09-11 14:30:00"
parsed_time2 = parse_time(time_str2)
diff = time_diff(parsed_time2, parsed_time)  # 返回差值（秒）
```

### 数据清洗工具

```python
from crawlo.tools import clean_text, format_currency, extract_emails

# 清洗文本
dirty_text = "<p>这是一个&nbsp;<b>测试</b>&amp;文本</p>"
clean_result = clean_text(dirty_text)

# 格式化货币
price = 1234.567
formatted_price = format_currency(price, "¥", 2)

# 提取邮箱
text_with_email = "联系邮箱: test@example.com"
emails = extract_emails(text_with_email)
```

### 数据验证工具

```python
from crawlo.tools import validate_email, validate_url, validate_phone

# 验证邮箱
is_valid = validate_email("test@example.com")

# 验证URL
is_valid = validate_url("https://example.com")

# 验证电话
is_valid = validate_phone("13812345678")
```

### 请求处理工具

```python
from crawlo.tools import build_url, add_query_params, merge_headers

# 构建URL
base_url = "https://api.example.com"
path = "/v1/users"
query_params = {"page": 1, "limit": 10}
full_url = build_url(base_url, path, query_params)

# 添加查询参数
existing_url = "https://api.example.com/v1/users?page=1"
new_params = {"sort": "name"}
updated_url = add_query_params(existing_url, new_params)

# 合并请求头
base_headers = {"Content-Type": "application/json"}
additional_headers = {"Authorization": "Bearer token123"}
merged_headers = merge_headers(base_headers, additional_headers)
```

### 反爬虫工具

```python
from crawlo.tools import get_random_user_agent, rotate_proxy

# 获取随机User-Agent
user_agent = get_random_user_agent()

# 轮换代理
proxy = rotate_proxy()
```

### 分布式协调工具

```python
from crawlo.tools import generate_task_id, get_cluster_info

# 生成任务ID
task_id = generate_task_id("https://example.com", "example_spider")

# 获取集群信息
cluster_info = get_cluster_info()
```

## 在爬虫中使用

```python
from crawlo import Spider, Request
from crawlo.tools import (
    clean_text, 
    validate_email, 
    get_random_user_agent,
    build_url
)

class ExampleSpider(Spider):
    def start_requests(self):
        headers = {"User-Agent": get_random_user_agent()}
        yield Request("https://example.com", headers=headers)
    
    def parse(self, response):
        # 提取数据
        title = response.css('h1::text').get()
        email = response.css('.email::text').get()
        
        # 清洗和验证数据
        clean_title = clean_text(title) if title else None
        is_valid_email = validate_email(email) if email else False
        
        # 构建下一页URL
        next_page_url = build_url("https://example.com", "/page/2")
        
        # 处理数据...
```

## 模块API

### 日期工具
- `parse_time()`: 将时间字符串解析为datetime对象
- `format_time()`: 将datetime对象格式化为字符串
- `time_diff()`: 计算时间差（秒）

### 数据清洗工具
- `TextCleaner`: 文本清洗工具
- `DataFormatter`: 数据格式化工具
- `clean_text()`: 清洗文本中的HTML标签和实体
- `format_currency()`: 将数字格式化为货币
- `extract_emails()`: 从文本中提取邮箱地址

### 数据验证工具
- `DataValidator`: 数据验证工具
- `validate_email()`: 验证邮箱地址格式
- `validate_url()`: 验证URL格式
- `validate_phone()`: 验证电话号码格式

### 请求处理工具
- `RequestHandler`: 请求处理工具
- `build_url()`: 构建完整URL
- `add_query_params()`: 向URL添加查询参数
- `merge_headers()`: 合并HTTP请求头

### 反爬虫工具
- `AntiCrawler`: 反爬虫工具
- `get_random_user_agent()`: 获取随机User-Agent字符串
- `rotate_proxy()`: 轮换代理设置

### 分布式协调工具
- `DistributedCoordinator`: 分布式协调工具
- `generate_task_id()`: 生成唯一任务ID
- `get_cluster_info()`: 获取集群信息

这个工具包使得处理网页抓取项目中的常见任务变得简单，为各种场景提供了可靠且可重用的工具。