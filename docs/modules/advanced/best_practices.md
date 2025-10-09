# 最佳实践

本文档总结了使用 Crawlo 框架开发和部署爬虫项目时的最佳实践，帮助开发者编写高质量、可维护和高性能的爬虫代码。

## 项目结构

### 推荐的项目结构

```bash
my_crawler_project/
├── crawlo.cfg              # 主配置文件
├── settings.py             # 配置模块
├── items.py                # 数据项定义
├── pipelines.py            # 数据管道
├── middlewares.py          # 中间件
├── extensions.py           # 扩展
├── spiders/                # 爬虫模块
│   ├── __init__.py
│   ├── base_spider.py      # 基础爬虫类
│   └── my_spider.py        # 具体爬虫实现
├── utils/                  # 工具模块
│   ├── __init__.py
│   ├── parsers.py          # 解析工具
│   └── helpers.py          # 辅助函数
├── tests/                  # 测试代码
│   ├── __init__.py
│   ├── test_spiders.py
│   └── test_pipelines.py
├── docs/                   # 文档
└── requirements.txt        # 依赖列表
```

### 模块化设计

```python
# base_spider.py - 基础爬虫类
from crawlo.spider import Spider

class BaseSpider(Spider):
    """所有爬虫的基类"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setup_logging()
        self.setup_metrics()
    
    def setup_logging(self):
        """设置日志"""
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
    
    def setup_metrics(self):
        """设置指标监控"""
        self.metrics = {
            'requests': 0,
            'items': 0,
            'errors': 0
        }
    
    def closed(self, reason):
        """爬虫关闭时的清理工作"""
        self.logger.info(f"爬虫 {self.name} 已关闭，原因: {reason}")
        self.report_metrics()
    
    def report_metrics(self):
        """报告指标"""
        self.logger.info(f"统计信息: {self.metrics}")
```

## 爬虫开发

### 数据项设计

```python
# items.py
from crawlo.items import Item

class ProductItem(Item):
    """产品数据项"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.required_fields = ['name', 'price']
        self.field_types = {
            'name': str,
            'price': float,
            'description': str,
            'images': list,
            'category': str
        }
    
    def validate(self):
        """数据验证"""
        # 检查必需字段
        for field in self.required_fields:
            if not self.get(field):
                self.logger.warning(f"缺少必需字段: {field}")
                return False
        
        # 检查字段类型
        for field, expected_type in self.field_types.items():
            if field in self and not isinstance(self[field], expected_type):
                self.logger.warning(f"字段 {field} 类型错误")
                return False
        
        # 业务逻辑验证
        if self.get('price', 0) < 0:
            self.logger.warning("价格不能为负数")
            return False
        
        return True
    
    def clean(self):
        """数据清洗"""
        # 清理字符串字段
        for field in ['name', 'description']:
            if field in self:
                self[field] = self[field].strip()
        
        # 格式化价格
        if 'price' in self:
            self['price'] = round(float(self['price']), 2)
        
        return self
```

### 爬虫实现

```python
# my_spider.py
from .base_spider import BaseSpider
from .items import ProductItem

class MySpider(BaseSpider):
    name = 'my_spider'
    start_urls = ['https://example.com/products']
    
    def parse(self, response):
        """解析产品列表页"""
        try:
            # 提取产品链接
            product_links = response.extract_attrs('.product-link', 'href')
            
            for link in product_links:
                absolute_url = response.urljoin(link)
                yield Request(
                    url=absolute_url,
                    callback=self.parse_product,
                    meta={'list_page': response.url}
                )
            
            # 处理分页
            next_page = response.extract_attr('.next-page', 'href')
            if next_page:
                yield Request(
                    url=response.urljoin(next_page),
                    callback=self.parse
                )
                
        except Exception as e:
            self.metrics['errors'] += 1
            self.logger.error(f"解析列表页失败: {e}")
    
    def parse_product(self, response):
        """解析产品详情页"""
        try:
            item = ProductItem(
                name=response.extract_text('h1.product-title'),
                price=response.extract_text('.price'),
                description=response.extract_text('.description'),
                images=response.extract_attrs('.product-images img', 'src'),
                category=response.extract_text('.category')
            )
            
            # 数据清洗和验证
            item.clean()
            if item.validate():
                self.metrics['items'] += 1
                yield item
            else:
                self.metrics['errors'] += 1
                self.logger.warning(f"数据验证失败: {response.url}")
                
        except Exception as e:
            self.metrics['errors'] += 1
            self.logger.error(f"解析产品页失败 {response.url}: {e}")
```

## 配置管理

### 环境隔离配置

```python
# settings.py
import os

class BaseConfig:
    """基础配置"""
    # 并发配置
    CONCURRENCY = 16
    DOWNLOAD_DELAY = 0.5
    DOWNLOAD_TIMEOUT = 30
    
    # 队列配置
    SCHEDULER_MAX_QUEUE_SIZE = 10000
    
    # 日志配置
    LOG_LEVEL = 'INFO'
    LOG_FILE = None

class DevelopmentConfig(BaseConfig):
    """开发环境配置"""
    CONCURRENCY = 5
    DOWNLOAD_DELAY = 1.0
    LOG_LEVEL = 'DEBUG'
    LOG_FILE = 'logs/dev.log'

class ProductionConfig(BaseConfig):
    """生产环境配置"""
    CONCURRENCY = 50
    DOWNLOAD_DELAY = 0.1
    LOG_LEVEL = 'WARNING'
    LOG_FILE = 'logs/prod.log'
    LOG_MAX_BYTES = 100 * 1024 * 1024  # 100MB
    LOG_BACKUP_COUNT = 10

class TestingConfig(BaseConfig):
    """测试环境配置"""
    CONCURRENCY = 1
    DOWNLOAD_DELAY = 0.0
    LOG_LEVEL = 'DEBUG'

# 根据环境变量选择配置
config_map = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig
}

def get_config():
    env = os.getenv('CRAWLO_ENV', 'development')
    return config_map.get(env, DevelopmentConfig)()
```

### 配置验证

```python
# config_validator.py
from crawlo.config_validator import ConfigValidator

class CustomConfigValidator(ConfigValidator):
    """自定义配置验证器"""
    
    def validate(self, config):
        """验证配置"""
        is_valid, errors, warnings = super().validate(config)
        
        # 添加自定义验证规则
        custom_errors = self._validate_custom_rules(config)
        errors.extend(custom_errors)
        
        return is_valid and len(custom_errors) == 0, errors, warnings
    
    def _validate_custom_rules(self, config):
        """自定义验证规则"""
        errors = []
        
        # 验证价格字段配置
        if hasattr(config, 'PRICE_FIELDS'):
            if not isinstance(config.PRICE_FIELDS, list):
                errors.append("PRICE_FIELDS 必须是列表类型")
        
        # 验证自定义中间件
        if hasattr(config, 'CUSTOM_MIDDLEWARES'):
            for middleware in config.CUSTOM_MIDDLEWARES:
                if not self._is_valid_middleware(middleware):
                    errors.append(f"无效的中间件: {middleware}")
        
        return errors
    
    def _is_valid_middleware(self, middleware):
        """验证中间件有效性"""
        # 实现中间件验证逻辑
        return True
```

## 错误处理

### 异常处理策略

```python
# error_handlers.py
import asyncio
import logging
from functools import wraps

def retry_on_failure(max_retries=3, delay=1.0):
    """重试装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    if asyncio.iscoroutinefunction(func):
                        return await func(*args, **kwargs)
                    else:
                        return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        logging.warning(f"函数 {func.__name__} 执行失败 (尝试 {attempt + 1}/{max_retries + 1}): {e}")
                        await asyncio.sleep(delay * (2 ** attempt))  # 指数退避
                    else:
                        logging.error(f"函数 {func.__name__} 执行失败，已达到最大重试次数: {e}")
                        raise last_exception
            
            return None
        return wrapper
    return decorator

class ErrorHandler:
    """错误处理器"""
    
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)
    
    def handle_parsing_error(self, response, exception):
        """处理解析错误"""
        self.logger.error(f"解析页面失败 {response.url}: {exception}")
        
        # 记录错误详情
        error_info = {
            'url': response.url,
            'status_code': response.status_code,
            'exception': str(exception),
            'timestamp': datetime.now().isoformat()
        }
        
        # 可以将错误信息存储到数据库或文件中
        self._log_error(error_info)
        
        # 根据错误类型决定是否重试
        if self._should_retry(exception):
            return self._retry_request(response.request)
        
        return None
    
    def _log_error(self, error_info):
        """记录错误信息"""
        # 实现错误日志记录逻辑
        pass
    
    def _should_retry(self, exception):
        """判断是否应该重试"""
        # 实现重试逻辑
        return True
    
    def _retry_request(self, request):
        """重试请求"""
        # 实现请求重试逻辑
        request.retry_times += 1
        return request
```

## 性能优化

### 异步处理

```python
# async_utils.py
import asyncio
import aiofiles
from concurrent.futures import ThreadPoolExecutor

class AsyncProcessor:
    """异步处理器"""
    
    def __init__(self, max_workers=4):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.semaphore = asyncio.Semaphore(max_workers * 2)
    
    async def process_batch(self, items, processor_func):
        """批量异步处理"""
        tasks = []
        async with self.semaphore:
            for item in items:
                task = asyncio.create_task(
                    self._process_item(item, processor_func)
                )
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            return [r for r in results if not isinstance(r, Exception)]
    
    async def _process_item(self, item, processor_func):
        """处理单个项目"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, processor_func, item)
    
    async def write_to_file(self, filename, data):
        """异步写入文件"""
        async with aiofiles.open(filename, 'w', encoding='utf-8') as f:
            await f.write(data)

# 使用示例
async def main():
    processor = AsyncProcessor(max_workers=8)
    
    # 批量处理数据
    items = [f"item_{i}" for i in range(1000)]
    results = await processor.process_batch(items, lambda x: x.upper())
    
    # 异步写入结果
    await processor.write_to_file('output.txt', '\n'.join(results))
```

### 缓存策略

```python
# cache.py
import hashlib
import json
import time
from functools import wraps

class CacheManager:
    """缓存管理器"""
    
    def __init__(self, redis_client=None, default_ttl=3600):
        self.redis_client = redis_client
        self.default_ttl = default_ttl
        self.local_cache = {}
    
    def cache_result(self, ttl=None):
        """缓存装饰器"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # 生成缓存键
                cache_key = self._generate_cache_key(func.__name__, args, kwargs)
                
                # 尝试从缓存获取
                cached_result = self._get_from_cache(cache_key)
                if cached_result is not None:
                    return cached_result
                
                # 执行函数并缓存结果
                result = func(*args, **kwargs)
                self._set_cache(cache_key, result, ttl or self.default_ttl)
                return result
            
            return wrapper
        return decorator
    
    def _generate_cache_key(self, func_name, args, kwargs):
        """生成缓存键"""
        key_data = f"{func_name}:{str(args)}:{str(sorted(kwargs.items()))}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _get_from_cache(self, key):
        """从缓存获取"""
        # 先检查本地缓存
        if key in self.local_cache:
            value, expire_time = self.local_cache[key]
            if time.time() < expire_time:
                return value
            else:
                del self.local_cache[key]
        
        # 再检查 Redis 缓存
        if self.redis_client:
            cached_value = self.redis_client.get(key)
            if cached_value:
                return json.loads(cached_value)
        
        return None
    
    def _set_cache(self, key, value, ttl):
        """设置缓存"""
        # 设置本地缓存
        expire_time = time.time() + ttl
        self.local_cache[key] = (value, expire_time)
        
        # 设置 Redis 缓存
        if self.redis_client:
            self.redis_client.setex(key, ttl, json.dumps(value))
```

## 测试策略

### 单元测试

```python
# test_spiders.py
import unittest
from unittest.mock import Mock, patch
from crawlo.spider import Spider
from crawlo.network import Response, Request

class TestMySpider(unittest.TestCase):
    """爬虫单元测试"""
    
    def setUp(self):
        """测试初始化"""
        self.spider = MySpider(name='test_spider')
    
    def test_parse_product(self):
        """测试产品页面解析"""
        # 创建模拟响应
        mock_response = Mock(spec=Response)
        mock_response.url = 'https://example.com/product/123'
        mock_response.extract_text.return_value = 'Test Product'
        mock_response.extract_attrs.return_value = ['image1.jpg', 'image2.jpg']
        
        # 执行解析
        items = list(self.spider.parse_product(mock_response))
        
        # 验证结果
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['name'], 'Test Product')
        self.assertEqual(len(items[0]['images']), 2)
    
    def test_parse_with_pagination(self):
        """测试分页解析"""
        mock_response = Mock(spec=Response)
        mock_response.url = 'https://example.com/products'
        mock_response.extract_attrs.return_value = ['/product/1', '/product/2']
        mock_response.extract_attr.return_value = '/products?page=2'
        
        requests = list(self.spider.parse(mock_response))
        
        # 验证生成的请求数量
        self.assertEqual(len(requests), 3)  # 2个产品请求 + 1个分页请求

# test_pipelines.py
class TestProductPipeline(unittest.TestCase):
    """管道单元测试"""
    
    def setUp(self):
        self.pipeline = ProductPipeline()
    
    def test_process_item_valid(self):
        """测试有效数据项处理"""
        item = ProductItem(name='Test Product', price=99.99)
        result = self.pipeline.process_item(item, Mock())
        
        self.assertEqual(result['name'], 'Test Product')
        self.assertEqual(result['price'], 99.99)
    
    def test_process_item_invalid(self):
        """测试无效数据项处理"""
        item = ProductItem(name='', price=-10)  # 无效数据
        result = self.pipeline.process_item(item, Mock())
        
        self.assertIsNone(result)  # 无效数据应该被丢弃
```

### 集成测试

```python
# test_integration.py
import asyncio
import pytest
from crawlo.crawler import Crawler
from crawlo.config import CrawloConfig

class TestIntegration:
    """集成测试"""
    
    @pytest.fixture
    def config(self):
        """测试配置"""
        return CrawloConfig.standalone(
            concurrency=2,
            download_delay=0.1,
            log_level='WARNING'
        )
    
    @pytest.mark.asyncio
    async def test_crawler_execution(self, config):
        """测试爬虫执行"""
        crawler = Crawler(config)
        
        # 创建测试爬虫
        spider = MySpider(name='test_spider')
        
        # 执行爬虫
        stats = await crawler.start_spider(spider)
        
        # 验证统计信息
        assert stats['requests'] > 0
        assert stats['items'] >= 0
        assert stats['errors'] == 0

# conftest.py - pytest 配置
import pytest
import tempfile
import os

@pytest.fixture(scope='session')
def temp_dir():
    """临时目录"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir

@pytest.fixture(scope='session')
def test_config(temp_dir):
    """测试配置"""
    config_file = os.path.join(temp_dir, 'test_config.py')
    with open(config_file, 'w') as f:
        f.write("""
CONCURRENCY = 1
DOWNLOAD_DELAY = 0.01
LOG_LEVEL = 'ERROR'
""")
    return config_file
```

## 部署和运维

### Docker 部署

```dockerfile
# Dockerfile
FROM python:3.9-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建日志目录
RUN mkdir -p logs

# 暴露端口（如果需要）
EXPOSE 8000

# 运行命令
CMD ["crawlo", "run", "my_spider"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  crawler:
    build: .
    environment:
      - CRAWLO_ENV=production
      - REDIS_HOST=redis
    volumes:
      - ./logs:/app/logs
      - ./data:/app/data
    depends_on:
      - redis
    restart: unless-stopped

  redis:
    image: redis:6-alpine
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"

volumes:
  redis_data:
```

### 监控和告警

```python
# monitoring.py
import psutil
import time
from datetime import datetime

class SystemMonitor:
    """系统监控"""
    
    def __init__(self, alert_manager):
        self.alert_manager = alert_manager
        self.metrics = {}
    
    def collect_metrics(self):
        """收集系统指标"""
        process = psutil.Process()
        
        self.metrics = {
            'timestamp': datetime.now().isoformat(),
            'cpu_percent': psutil.cpu_percent(),
            'memory_percent': process.memory_percent(),
            'memory_rss': process.memory_info().rss / 1024 / 1024,  # MB
            'disk_usage': psutil.disk_usage('/').percent,
            'network_sent': psutil.net_io_counters().bytes_sent,
            'network_recv': psutil.net_io_counters().bytes_recv
        }
        
        return self.metrics
    
    def check_thresholds(self):
        """检查阈值"""
        metrics = self.collect_metrics()
        
        # CPU 使用率告警
        if metrics['cpu_percent'] > 90:
            self.alert_manager.send_alert('cpu_usage', metrics['cpu_percent'], 90)
        
        # 内存使用告警
        if metrics['memory_percent'] > 80:
            self.alert_manager.send_alert('memory_usage', metrics['memory_percent'], 80)
        
        # 磁盘使用告警
        if metrics['disk_usage'] > 95:
            self.alert_manager.send_alert('disk_usage', metrics['disk_usage'], 95)
    
    def export_metrics(self, exporter):
        """导出指标"""
        exporter.export(self.metrics)
```

通过遵循这些最佳实践，可以开发出高质量、可维护和高性能的 Crawlo 爬虫项目。建议根据具体项目需求选择合适的实践方法，并在实际开发中不断优化和完善。