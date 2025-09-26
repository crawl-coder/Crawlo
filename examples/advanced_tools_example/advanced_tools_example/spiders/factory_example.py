#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工厂模式使用示例
演示如何使用 Crawlo 的组件工厂系统创建和管理组件

使用场景：
适用于需要统一管理组件创建和依赖注入的爬虫项目。当你的爬虫需要创建多种类型的处理器、
服务或工具类实例，并希望实现单例模式或依赖注入时，可以使用工厂模式。

典型应用场景：
- 需要创建多个数据处理器实例
- 需要依赖注入功能
- 需要单例组件实例
- 复杂的组件依赖关系管理

与OfweekSpider的对比案例：
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

优势：
- 统一的组件创建和管理机制
- 支持依赖注入和单例模式
- 易于测试和维护
- 组件之间的解耦
"""

from crawlo.spider import Spider
from crawlo.network import Request
from crawlo.factories import (
    ComponentRegistry, 
    ComponentSpec, 
    CrawlerComponentFactory,
    get_component_registry,
    create_component
)
from crawlo.utils.log import get_logger


class FactoryExampleSpider(Spider):
    """工厂模式示例爬虫"""
    name = 'factory_example'
    
    def __init__(self):
        super().__init__()
        # self.logger = get_logger(self.__class__.__name__)
        
        # 初始化组件工厂系统
        self._setup_factory_components()
    
    def _setup_factory_components(self):
        """设置工厂组件"""
        # 获取全局组件注册表
        registry = get_component_registry()
        
        # 注册自定义组件
        def create_custom_processor(**kwargs):
            return CustomDataProcessor(**kwargs)
        
        # 注册自定义数据处理器组件
        registry.register(ComponentSpec(
            name='custom_processor',
            component_type=CustomDataProcessor,
            factory_func=create_custom_processor,
            dependencies=[],
            singleton=True  # 单例模式
        ))
        
        # 注册自定义服务组件
        def create_custom_service(**kwargs):
            return CustomService(**kwargs)
        
        registry.register(ComponentSpec(
            name='custom_service',
            component_type=CustomService,
            factory_func=create_custom_service,
            dependencies=[]
        ))
    
    def start_requests(self):
        """生成起始请求"""
        urls = [
            'https://httpbin.org/get',
            'https://httpbin.org/json',
            'https://httpbin.org/headers'
        ]
        
        for url in urls:
            yield Request(url=url, callback=self.parse)
    
    def parse(self, response):
        """解析响应"""
        # self.logger.info(f"处理响应: {response.url}")
        
        # 使用工厂创建组件实例
        processor = create_component('custom_processor', name="数据处理器1")
        service = create_component('custom_service', api_key="test_key")
        
        # 处理数据
        processed_data = processor.process(response.text)
        result = service.process_data(processed_data)
        
        yield {
            'url': response.url,
            'title': response.css('title::text').get() or 'N/A',
            'data': result
        }


class CustomDataProcessor:
    """自定义数据处理器"""
    
    def __init__(self, name="默认处理器"):
        self.name = name
        # self.logger = get_logger(self.__class__.__name__)
        # self.logger.info(f"创建数据处理器: {self.name}")
    
    def process(self, data):
        """处理数据"""
        # self.logger.debug(f"{self.name} 正在处理数据，长度: {len(data)}")
        # 简单的数据处理示例
        return {
            'processed': True,
            'length': len(data),
            'summary': data[:100] + "..." if len(data) > 100 else data
        }


class CustomService:
    """自定义服务"""
    
    def __init__(self, api_key=None):
        self.api_key = api_key
        # self.logger = get_logger(self.__class__.__name__)
        # self.logger.info(f"创建服务实例，API密钥: {'*' * len(api_key) if api_key else 'None'}")
    
    def process_data(self, data):
        """处理数据"""
        # self.logger.debug("服务正在处理数据")
        # 模拟服务处理
        return {
            'service_processed': True,
            'timestamp': __import__('time').time(),
            'data': data,
            'api_key_used': self.api_key is not None
        }


# 使用示例说明
USAGE_EXAMPLE = """
工厂模式使用说明
==============

1. 组件注册:
   - 通过 ComponentSpec 定义组件规范
   - 指定工厂函数、依赖关系和单例模式
   - 使用 register_component 注册组件

2. 组件创建:
   - 使用 create_component(name, **kwargs) 创建组件实例
   - 支持单例模式和依赖注入

3. 优势:
   - 统一的组件创建和管理机制
   - 支持依赖注入和单例模式
   - 易于测试和维护
"""

if __name__ == '__main__':
    print(USAGE_EXAMPLE)