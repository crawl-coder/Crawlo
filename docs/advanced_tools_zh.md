# 高级工具

Crawlo框架提供了一套全面的高级工具，用于处理网页抓取场景中的常见挑战。这些工具包括数据处理、请求处理、反爬虫措施和分布式协调工具。

## 工具分类

### 1. 数据处理工具

#### 数据清洗工具
- HTML标签清理器：自动去除HTML标签，提取纯文本
- 数据格式化工具：统一日期、数字、货币等格式
- 编码转换工具：处理不同字符编码的数据

#### 数据验证工具
- 字段验证器：验证邮箱、电话、身份证等常见字段格式
- 数据完整性检查：确保关键字段不为空

### 2. 请求处理工具

#### 重试机制封装
- 智能重试：根据HTTP状态码和异常类型决定是否重试
- 指数退避：自动增加重试间隔时间

### 3. 反爬虫应对工具

#### IP代理工具
- 代理池管理：自动切换代理IP
- 代理有效性检测：定期检查代理是否可用

#### 验证码处理工具
- 验证码识别接口：集成第三方验证码识别服务
- 手动验证码处理：提供人工输入验证码的接口

### 4. 分布式协调工具

#### 任务分发工具
- 分页任务生成器：自动将大量页面分发给不同节点
- 任务进度跟踪：实时监控各节点任务执行情况

#### 数据去重工具
- 多级去重：结合布隆过滤器和精确去重
- 去重策略配置：根据不同数据类型选择去重策略

## 使用示例

### 数据处理工具

```python
from crawlo.tools import clean_text, format_currency, validate_email, check_data_integrity

# 数据清洗
dirty_text = "<p>这是一个&nbsp;<b>测试</b>&amp;文本</p>"
clean_result = clean_text(dirty_text)

# 数据格式化
price = 1234.567
formatted_price = format_currency(price, "¥", 2)

# 字段验证
email = "test@example.com"
is_valid_email = validate_email(email)

# 数据完整性检查
data = {
    "name": "张三",
    "email": "test@example.com",
    "phone": "13812345678"
}
required_fields = ["name", "email", "phone", "address"]
integrity_result = check_data_integrity(data, required_fields)
```

### 重试机制

```python
from crawlo.tools import retry, exponential_backoff

# 指数退避
for attempt in range(5):
    delay = exponential_backoff(attempt)
    print(f"重试次数 {attempt}: 延迟 {delay:.2f} 秒")

# 重试装饰器
@retry(max_retries=3)
def unreliable_function():
    import random
    if random.random() < 0.7:  # 70%概率失败
        raise ConnectionError("网络连接失败")
    return "成功执行"
```

### 反爬虫应对工具

```python
from crawlo.tools import AntiCrawler, rotate_proxy, handle_captcha, detect_rate_limiting

# 反爬虫工具
anti_crawler = AntiCrawler()

# 获取随机User-Agent
user_agent = anti_crawler.get_random_user_agent()

# 轮换代理
proxy = anti_crawler.rotate_proxy()

# 检测验证码
response_with_captcha = "请输入验证码进行验证"
has_captcha = anti_crawler.handle_captcha(response_with_captcha)

# 检测频率限制
status_code = 429  # 请求过多
response_headers = {"Retry-After": "60"}
is_rate_limited = anti_crawler.detect_rate_limiting(status_code, response_headers)
```

### 分布式协调工具

```python
from crawlo.tools import generate_pagination_tasks, distribute_tasks, DistributedCoordinator

# 生成分页任务
base_url = "https://example.com/products"
pagination_tasks = generate_pagination_tasks(base_url, 1, 100)

# 任务分发
tasks = list(range(1, 21))  # 20个任务
distributed = distribute_tasks(tasks, 4)  # 分发给4个工作节点

# 分布式协调器
coordinator = DistributedCoordinator()
cluster_info = coordinator.get_cluster_info()
```

## 在爬虫中使用

```python
import asyncio
from crawlo import Spider, Request
from crawlo.tools import (
    clean_text,
    validate_email,
    AntiCrawler,
    DistributedCoordinator,
    retry
)

class AdvancedSpider(Spider):
    def __init__(self):
        super().__init__()
        self.anti_crawler = AntiCrawler()
        self.coordinator = DistributedCoordinator()
        
    def start_requests(self):
        # 生成分页任务
        base_url = "https://api.example.com/products"
        pagination_tasks = self.coordinator.generate_pagination_tasks(base_url, 1, 100)
        
        for url in pagination_tasks:
            yield Request(url)
    
    @retry(max_retries=3)
    async def parse(self, response):
        # 检查是否遇到验证码
        if self.anti_crawler.handle_captcha(response.text):
            # 处理验证码逻辑
            print("遇到验证码，需要处理")
            return
            
        # 提取数据
        products = response.css('.product-item')
        for product in products:
            name = product.css('.product-name::text').get()
            price_text = product.css('.price::text').get()
            email = product.css('.contact-email::text').get()
            
            # 数据清洗和验证
            clean_name = clean_text(name) if name else None
            clean_price = clean_text(price_text) if price_text else None
            is_valid_email = validate_email(email) if email else False
            
            # 检查数据是否重复
            if not await self.coordinator.is_duplicate({"name": clean_name, "price": clean_price}):
                # 添加到去重集合
                await self.coordinator.add_to_dedup({"name": clean_name, "price": clean_price})
                
                # 处理产品数据...
                pass
```

这些高级工具使得在网页抓取项目中处理复杂场景变得简单，为各种挑战提供了可靠且可重用的工具。