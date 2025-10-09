# 自定义扩展

扩展是 Crawlo 框架中用于添加额外功能的组件。通过自定义扩展，您可以实现各种功能，如监控、统计、日志记录等。

## 创建自定义扩展

要创建自定义扩展，需要继承 `crawlo.extensions.Extension` 基类并实现相应的方法。

### 基本结构

```python
from crawlo.extensions import Extension

class CustomExtension(Extension):
    def __init__(self, crawler):
        super().__init__(crawler)
        # 初始化扩展
    
    def open(self):
        # 扩展启用时调用
        pass
    
    def close(self):
        # 扩展关闭时调用
        pass
    
    @classmethod
    def from_crawler(cls, crawler):
        # 从爬虫实例创建扩展实例
        return cls(crawler)
```

### 方法说明

#### __init__(self, crawler)

- **作用**: 初始化扩展
- **参数**:
  - `crawler`: 爬虫实例

#### open(self)

- **作用**: 在扩展启用时调用，用于初始化资源
- **返回值**: 无

#### close(self)

- **作用**: 在扩展关闭时调用，用于释放资源
- **返回值**: 无

#### from_crawler(cls, crawler)

- **作用**: 从爬虫实例创建扩展实例的类方法
- **参数**:
  - `crawler`: 爬虫实例
- **返回值**: 扩展实例

## 示例

### 统计扩展

```python
from crawlo.extensions import Extension
from collections import defaultdict

class StatsExtension(Extension):
    def __init__(self, crawler):
        super().__init__(crawler)
        self.stats = defaultdict(int)
    
    def open(self):
        # 注册事件监听器
        self.crawler.signals.connect(self.on_request_sent, signal='request_sent')
        self.crawler.signals.connect(self.on_response_received, signal='response_received')
        self.crawler.signals.connect(self.on_item_scraped, signal='item_scraped')
    
    def close(self):
        # 输出统计信息
        print("Crawling Statistics:")
        for key, value in self.stats.items():
            print(f"  {key}: {value}")
    
    def on_request_sent(self, request):
        self.stats['requests_sent'] += 1
    
    def on_response_received(self, response):
        self.stats['responses_received'] += 1
        self.stats[f'status_{response.status_code}'] += 1
    
    def on_item_scraped(self, item):
        self.stats['items_scraped'] += 1
    
    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler)
```

### 日志扩展

```python
from crawlo.extensions import Extension
import logging

class LoggingExtension(Extension):
    def __init__(self, crawler):
        super().__init__(crawler)
        self.logger = logging.getLogger(__name__)
    
    def open(self):
        # 注册事件监听器
        self.crawler.signals.connect(self.on_spider_opened, signal='spider_opened')
        self.crawler.signals.connect(self.on_spider_closed, signal='spider_closed')
        self.crawler.signals.connect(self.on_request_sent, signal='request_sent')
    
    def on_spider_opened(self, spider):
        self.logger.info(f"Spider {spider.name} opened")
    
    def on_spider_closed(self, spider):
        self.logger.info(f"Spider {spider.name} closed")
    
    def on_request_sent(self, request):
        self.logger.debug(f"Sending request to {request.url}")
    
    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler)
```

### 内存监控扩展

```python
from crawlo.extensions import Extension
import psutil
import threading
import time

class MemoryMonitorExtension(Extension):
    def __init__(self, crawler):
        super().__init__(crawler)
        self.monitoring = False
        self.monitor_thread = None
        self.threshold = 500 * 1024 * 1024  # 500MB
    
    def open(self):
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_memory)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
    
    def close(self):
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join()
    
    def _monitor_memory(self):
        while self.monitoring:
            memory_usage = psutil.Process().memory_info().rss
            if memory_usage > self.threshold:
                self.crawler.logger.warning(f"High memory usage: {memory_usage / 1024 / 1024:.2f} MB")
            time.sleep(10)  # 每10秒检查一次
    
    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler)
```

## 配置扩展

在配置文件中启用自定义扩展：

```python
# settings.py
EXTENSIONS = {
    'myproject.extensions.StatsExtension': 100,
    'myproject.extensions.LoggingExtension': 200,
    'myproject.extensions.MemoryMonitorExtension': 300,
}
```

扩展的数字表示优先级，数字越小优先级越高。

## 最佳实践

1. **单一职责**: 每个扩展应该只负责一个功能
2. **事件驱动**: 利用信号系统监听和响应事件
3. **资源管理**: 正确打开和关闭资源
4. **性能考虑**: 避免在扩展中执行耗时操作
5. **异常处理**: 在扩展中妥善处理异常
6. **测试**: 为扩展编写单元测试