# Crawlo 高级工具爬虫使用场景说明

本文档详细说明了 `examples/advanced_tools_example/advanced_tools_example/spiders/` 目录下每个爬虫的具体使用场景，并以 `OfweekSpider.py` 作为实际案例进行说明。

## 1. FactoryExampleSpider (factory_example.py)

### 使用场景
适用于需要统一管理组件创建和依赖注入的爬虫项目。当你的爬虫需要创建多种类型的处理器、服务或工具类实例，并希望实现单例模式或依赖注入时，可以使用工厂模式。

### 典型应用场景
- 需要创建多个数据处理器实例
- 需要依赖注入功能
- 需要单例组件实例
- 复杂的组件依赖关系管理

### 与OfweekSpider的对比案例
在OfweekSpider中，我们可以使用工厂模式来创建不同的数据处理器：

```python
# OfweekSpider中原本的数据处理方式
item = NewsItem()
item['title'] = title.strip() if title else ''
item['publish_time'] = publish_time if publish_time else ''
item['url'] = response.url
item['source'] = source if source else ''
item['content'] = content

# 使用工厂模式重构后
# 注册不同的数据处理器
def create_news_processor(**kwargs):
    return NewsDataProcessor(**kwargs)

registry.register(ComponentSpec(
    name='news_processor',
    component_type=NewsDataProcessor,
    factory_func=create_news_processor,
    singleton=True
))

# 在parse_detail方法中使用
processor = create_component('news_processor')
item = processor.process(title, publish_time, response.url, source, content)
```

### 优势
- 统一的组件创建和管理机制
- 支持依赖注入和单例模式
- 易于测试和维护
- 组件之间的解耦

## 2. BatchExampleSpider (batch_example.py)

### 使用场景
适用于需要处理大量数据的爬虫项目，特别是当数据量超过内存限制或需要控制并发处理数量时。

### 典型应用场景
- 处理大量数据项
- 需要控制并发数量
- 内存敏感的数据处理任务
- 需要批量存储数据到数据库

### 与OfweekSpider的对比案例
在OfweekSpider中，我们可以使用批处理来优化数据存储：

```python
# OfweekSpider中原本的数据处理方式
yield item  # 逐个处理数据项

# 使用批处理重构后
# 在爬虫初始化时创建批处理器
self.batch_processor = BatchProcessor(batch_size=100, max_concurrent_batches=5)

# 在parse_detail方法中收集数据
self.data_items.append({
    'title': title,
    'publish_time': publish_time,
    'url': response.url,
    'source': source,
    'content': content
})

# 定期批量处理数据
if len(self.data_items) >= 100:
    await self.batch_processor.process_in_batches(
        items=self.data_items,
        processor_func=self.batch_save_items
    )
    self.data_items.clear()
```

### 优势
- 控制内存使用，避免一次性处理大量数据
- 支持并发处理提高效率
- 自动错误处理和恢复
- 可配置的批处理大小和并发数

## 3. ControlledExampleSpider (controlled_example.py)

### 使用场景
适用于需要生成大量请求的爬虫项目，特别是当起始URL数量庞大时，可以防止内存溢出并控制并发数量。

### 典型应用场景
- 需要生成大量请求的爬虫
- 内存受限的环境
- 需要精确控制并发的场景
- 处理大规模网站的分页URL

### 与OfweekSpider的对比案例
在OfweekSpider中，我们可以使用受控爬虫来优化起始请求的生成：

```python
# OfweekSpider中原本的起始请求生成方式
max_page = 1851
start_urls = []
for page in range(1, max_page + 1):
    url = f'https://ee.ofweek.com/CATList-2800-8100-ee-{page}.html'
    start_urls.append(url)

# 使用受控爬虫重构后
class OfweekControlledSpider(OfweekSpider, ControlledRequestMixin):
    def __init__(self):
        OfweekSpider.__init__(self)
        ControlledRequestMixin.__init__(self)
        
        # 配置受控生成参数
        self.max_pending_requests = 100
        self.batch_size = 50
        self.generation_interval = 0.01
    
    def _original_start_requests(self):
        """提供原始的大量请求"""
        max_page = 1851  # 处理1851页
        for page in range(1, max_page + 1):
            url = f'https://ee.ofweek.com/CATList-2800-8100-ee-{page}.html'
            yield Request(
                url=url,
                callback=self.parse,
                headers=self.headers,
                cookies=self.cookies
            )
```

### 优势
- 防止内存溢出
- 控制并发数量
- 动态负载调节
- 提高系统稳定性
- 背压控制，根据系统负载动态调节

## 4. LargeScaleConfigExampleSpider (large_scale_config_example.py)

### 使用场景
适用于不同规模和性能要求的爬虫项目，可以根据环境资源选择合适的配置。

### 典型应用场景
- 资源受限环境（使用保守配置）
- 一般生产环境（使用平衡配置）
- 高性能服务器（使用激进配置）
- 内存受限但要处理大量请求（使用内存优化配置）

### 与OfweekSpider的对比案例
在OfweekSpider中，我们可以根据不同的运行环境应用不同的配置：

```python
# OfweekSpider中原本的配置方式
custom_settings = {
    'DOWNLOAD_DELAY': 1.0,
    'CONCURRENCY': 16,
    'MAX_RETRY_TIMES': 5
}

# 使用大规模配置工具重构后
# 在settings.py中
from crawlo.utils.large_scale_config import apply_large_scale_config

# 根据环境变量选择配置类型
import os
config_type = os.getenv('CONFIG_TYPE', 'balanced')
concurrency = int(os.getenv('CONCURRENCY', '16'))

settings = {}
apply_large_scale_config(settings, config_type, concurrency)

# 应用到配置中
for key, value in settings.items():
    locals()[key] = value
```

### 优势
- 针对不同场景优化的配置
- 简化配置过程
- 提高爬取效率和稳定性
- 减少配置错误
- 快速适配不同性能环境

## 5. LargeScaleHelperExampleSpider (large_scale_helper_example.py)

### 使用场景
适用于处理大规模数据的爬虫项目，特别是需要断点续传、进度管理和内存优化的场景。

### 典型应用场景
- 处理数万+ URL的爬虫
- 需要断点续传的功能
- 内存敏感的大规模处理任务
- 需要进度跟踪和恢复的爬虫

### 与OfweekSpider的对比案例
在OfweekSpider中，我们可以使用大规模爬虫辅助工具来增强功能：

```python
# OfweekSpider中原本的处理方式
# 直接处理所有页面，没有进度管理

# 使用大规模爬虫辅助工具重构后
class OfweekLargeScaleSpider(OfweekSpider):
    def __init__(self):
        super().__init__()
        # 初始化辅助工具
        self.large_scale_helper = LargeScaleHelper(batch_size=100, checkpoint_interval=500)
        self.progress_manager = ProgressManager(progress_file="ofweek_progress.json")
        self.memory_optimizer = MemoryOptimizer(max_memory_mb=500)
    
    def start_requests(self):
        """使用批处理生成大量请求并支持断点续传"""
        # 模拟大量数据源
        max_page = 1851
        data_source = [f'https://ee.ofweek.com/CATList-2800-8100-ee-{page}.html' for page in range(1, max_page + 1)]
        
        # 加载进度
        progress = self.progress_manager.load_progress()
        start_offset = progress.get('processed_count', 0)
        
        self.logger.info(f"从偏移量 {start_offset} 开始处理")
        
        # 使用批处理迭代器处理数据
        processed_count = start_offset
        for batch in self.large_scale_helper.batch_iterator(data_source, start_offset):
            # 内存检查和优化
            if self.memory_optimizer.should_pause_for_memory():
                self.logger.warning("内存使用过高，执行垃圾回收")
                self.memory_optimizer.force_garbage_collection()
            
            for url in batch:
                processed_count += 1
                yield Request(
                    url=url,
                    callback=self.parse,
                    headers=self.headers,
                    cookies=self.cookies,
                    meta={'page': processed_count}
                )
                
                # 保存进度
                if processed_count % 100 == 0:
                    self.progress_manager.save_progress({
                        'processed_count': processed_count,
                        'timestamp': time.time()
                    })
```

### 优势
- 处理大量数据时的内存管理
- 断点续传支持
- 进度跟踪和恢复
- 内存使用优化
- 批量数据处理

## 总结

这些高级工具爬虫示例展示了如何在实际项目中应用Crawlo框架的高级功能。通过使用这些工具，可以：

1. **提高代码质量**：通过工厂模式实现组件的统一管理和依赖注入
2. **优化性能**：通过批处理工具和受控爬虫混入类提高处理效率
3. **增强可扩展性**：通过大规模配置工具适配不同环境
4. **提升稳定性**：通过大规模爬虫辅助工具实现断点续传和内存优化

在实际项目中，可以根据具体需求选择合适的工具组合使用，以达到最佳的爬取效果。