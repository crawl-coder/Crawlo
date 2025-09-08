#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
Crawlo Spider Module
==================
提供爬虫基类和相关功能。

核心功能:
- Spider基类：所有爬虫的基础类
- 自动注册机制：通过元类自动注册爬虫
- 配置管理：支持自定义设置和链式调用
- 生命周期管理：开启/关闭钩子函数
- 分布式支持：智能检测运行模式

使用示例:
    class MySpider(Spider):
        name = 'my_spider'
        start_urls = ['http://example.com']
        
        # 自定义配置
        custom_settings = {
            'DOWNLOADER_TYPE': 'httpx',
            'CONCURRENCY': 10
        }
        
        def parse(self, response):
            # 解析逻辑
            yield Item(data=response.json())
"""
from __future__ import annotations
from typing import Type, Any, Optional, List, Dict, Union, Iterator, AsyncIterator
from ..network.request import Request
from ..utils.log import get_logger


# 全局爬虫注册表
_DEFAULT_SPIDER_REGISTRY: dict[str, Type[Spider]] = {}


class SpiderMeta(type):
    """
    爬虫元类，提供自动注册功能
    
    功能:
    - 自动注册爬虫到全局注册表
    - 验证爬虫名称的唯一性
    - 提供完整的错误提示
    """
    
    def __new__(mcs, name: str, bases: tuple[type], namespace: dict[str, Any], **kwargs):
        cls = super().__new__(mcs, name, bases, namespace)

        # 检查是否为Spider子类
        is_spider_subclass = any(
            base is Spider or (isinstance(base, type) and issubclass(base, Spider))
            for base in bases
        )
        if not is_spider_subclass:
            return cls

        # 验证爬虫名称
        spider_name = namespace.get('name')
        if not isinstance(spider_name, str):
            raise AttributeError(
                f"爬虫类 '{cls.__name__}' 必须定义字符串类型的 'name' 属性。\n"
                f"示例: name = 'my_spider'"
            )

        # 检查名称唯一性
        if spider_name in _DEFAULT_SPIDER_REGISTRY:
            existing_class = _DEFAULT_SPIDER_REGISTRY[spider_name]
            raise ValueError(
                f"爬虫名称 '{spider_name}' 已被 {existing_class.__name__} 占用。\n"
                f"请确保每个爬虫的 name 属性全局唯一。\n"
                f"建议使用格式: 'project_module_function'"
            )

        # 注册爬虫
        _DEFAULT_SPIDER_REGISTRY[spider_name] = cls
        get_logger(__name__).debug(f"自动注册爬虫: {spider_name} -> {cls.__name__}")

        return cls


class Spider(metaclass=SpiderMeta):
    """
    爬虫基类 - 所有爬虫实现的基础
    
    必须定义的属性:
    - name: 爬虫名称，必须全局唯一
    
    可选配置:
    - start_urls: 起始 URL 列表
    - custom_settings: 自定义设置字典
    - allowed_domains: 允许的域名列表
    
    必须实现的方法:
    - parse(response): 解析响应的主方法
    
    可选实现的方法:
    - spider_opened(): 爬虫开启时调用
    - spider_closed(): 爬虫关闭时调用
    - start_requests(): 生成初始请求（默认使用start_urls）
    
    示例:
        class MySpider(Spider):
            name = 'example_spider'
            start_urls = ['https://example.com']
            
            custom_settings = {
                'DOWNLOADER_TYPE': 'httpx',
                'CONCURRENCY': 5,
                'DOWNLOAD_DELAY': 1.0
            }
            
            def parse(self, response):
                # 提取数据
                data = response.css('title::text').get()
                yield {'title': data}
                
                # 生成新请求
                for link in response.css('a::attr(href)').getall():
                    yield Request(url=link, callback=self.parse_detail)
    """
    
    # 必须定义的属性
    name: str = None
    
    # 可选属性
    start_urls: List[str] = None
    custom_settings: Dict[str, Any] = None
    allowed_domains: List[str] = None

    def __init__(self, name: str = None, **kwargs):
        """
        初始化爬虫实例
        
        :param name: 爬虫名称（可选，默认使用类属性）
        :param kwargs: 其他初始化参数
        """
        # 初始化基本属性
        if not hasattr(self, 'start_urls') or self.start_urls is None:
            self.start_urls = []
        if not hasattr(self, 'custom_settings') or self.custom_settings is None:
            self.custom_settings = {}
        if not hasattr(self, 'allowed_domains') or self.allowed_domains is None:
            self.allowed_domains = []
            
        # 设置爬虫名称
        self.name = name or self.name
        if not self.name:
            raise ValueError(f"爬虫 {self.__class__.__name__} 必须指定 name 属性")
        
        # 初始化其他属性
        self.crawler = None
        self.logger = get_logger(self.name)
        self.stats = None
        
        # 应用额外参数
        for key, value in kwargs.items():
            setattr(self, key, value)

    @classmethod
    def create_instance(cls, crawler) -> 'Spider':
        """
        创建爬虫实例并绑定 crawler
        
        :param crawler: Crawler 实例
        :return: 爬虫实例
        """
        spider = cls()
        spider.crawler = crawler
        spider.stats = getattr(crawler, 'stats', None)
        
        # 合并自定义设置
        if hasattr(spider, 'custom_settings') and spider.custom_settings:
            for key, value in spider.custom_settings.items():
                crawler.settings.set(key, value)
                spider.logger.debug(f"应用自定义设置: {key} = {value}")
        
        return spider

    def start_requests(self) -> Iterator[Request]:
        """
        生成初始请求
        
        默认行为:
        - 使用 start_urls 生成请求
        - 智能检测分布式模式决定是否去重
        - 支持单个 start_url 属性（兼容性）
        - 支持批量生成优化（大规模URL场景）
        
        :return: Request 迭代器
        """
        # 检测是否为分布式模式
        is_distributed = self._is_distributed_mode()
        
        # 获取批量处理配置
        batch_size = self._get_batch_size()
        
        # 从 start_urls 生成请求
        if self.start_urls:
            generated_count = 0
            for url in self.start_urls:
                if self._is_allowed_domain(url):
                    yield Request(
                        url=url, 
                        callback=self.parse,
                        dont_filter=not is_distributed,
                        meta={'spider_name': self.name}
                    )
                    generated_count += 1
                    
                    # 大规模URL时进行批量控制
                    if batch_size > 0 and generated_count % batch_size == 0:
                        self.logger.debug(f"已生成 {generated_count} 个请求（批量大小: {batch_size}）")
                else:
                    self.logger.warning(f"跳过不允许的域名: {url}")
        
        # 兼容单个 start_url 属性
        elif hasattr(self, 'start_url') and isinstance(getattr(self, 'start_url'), str):
            url = getattr(self, 'start_url')
            if self._is_allowed_domain(url):
                yield Request(
                    url=url, 
                    callback=self.parse,
                    dont_filter=not is_distributed,
                    meta={'spider_name': self.name}
                )
            else:
                self.logger.warning(f"跳过不允许的域名: {url}")
        
        else:
            self.logger.warning(
                f"爬虫 {self.name} 没有定义 start_urls 或 start_url。\n"
                f"请在爬虫类中定义或重写 start_requests() 方法。"
            )
    
    def _get_batch_size(self) -> int:
        """
        获取批量处理大小配置
        
        用于大规模URL场景的性能优化
        
        :return: 批量大小（0表示无限制）
        """
        if not self.crawler:
            return 0
            
        # 从设置中获取批量大小
        batch_size = self.crawler.settings.get_int('SPIDER_BATCH_SIZE', 0)
        
        # 如果start_urls超过一定数量，自动启用批量模式
        if batch_size == 0 and self.start_urls and len(self.start_urls) > 1000:
            batch_size = 500  # 默认批量大小
            self.logger.info(f"检测到大量start_urls ({len(self.start_urls)})，启用批量模式 (批量大小: {batch_size})")
            
        return batch_size
    
    def _is_distributed_mode(self) -> bool:
        """
        智能检测是否为分布式模式
        
        检测条件:
        - QUEUE_TYPE = 'redis'
        - FILTER_CLASS 包含 'aioredis_filter' 
        - RUN_MODE = 'distributed'
        
        :return: 是否为分布式模式
        """
        if not self.crawler:
            return False
            
        settings = self.crawler.settings
        
        # 检查多个条件来判断是否为分布式模式
        queue_type = settings.get('QUEUE_TYPE', 'memory')
        filter_class = settings.get('FILTER_CLASS', '')
        run_mode = settings.get('RUN_MODE', 'standalone')
        
        # 分布式模式的标志
        is_redis_queue = queue_type == 'redis'
        is_redis_filter = 'aioredis_filter' in filter_class.lower()
        is_distributed_run_mode = run_mode == 'distributed'
        
        distributed = is_redis_queue or is_redis_filter or is_distributed_run_mode
        
        if distributed:
            self.logger.debug("检测到分布式模式，启用请求去重")
        else:
            self.logger.debug("检测到单机模式，禁用请求去重")
            
        return distributed
    
    def _is_allowed_domain(self, url: str) -> bool:
        """
        检查URL是否在允许的域名列表中
        
        :param url: 要检查的URL
        :return: 是否允许
        """
        if not self.allowed_domains:
            return True
            
        from urllib.parse import urlparse
        try:
            domain = urlparse(url).netloc.lower()
            return any(
                domain == allowed.lower() or domain.endswith('.' + allowed.lower())
                for allowed in self.allowed_domains
            )
        except Exception as e:
            self.logger.warning(f"URL解析失败: {url} - {e}")
            return False

    def parse(self, response):
        """
        解析响应的主方法（必须实现）
        
        :param response: 响应对象
        :return: 生成的 Item 或 Request
        """
        raise NotImplementedError(
            f"爬虫 {self.__class__.__name__} 必须实现 parse() 方法\n"
            f"示例:\n"
            f"def parse(self, response):\n"
            f"    # 提取数据\n"
            f"    yield {{'title': response.css('title::text').get()}}\n"
            f"    # 生成新请求\n"
            f"    for link in response.css('a::attr(href)').getall():\n"
            f"        yield Request(url=link)"
        )
    
    async def spider_opened(self):
        """
        爬虫开启时调用的钩子函数
        
        可用于:
        - 初始化资源
        - 连接数据库
        - 设置初始状态
        """
        self.logger.info(f"爬虫 {self.name} 已开启")
    
    async def spider_closed(self):
        """
        爬虫关闭时调用的钩子函数
        
        可用于:
        - 清理资源
        - 关闭数据库连接
        - 输出统计信息
        """
        if self.stats:
            stats_summary = {
                'total_requests': self.stats.get('total_requests', 0),
                'total_items': self.stats.get('total_items', 0),
                'success_rate': self.stats.get('success_rate', 'N/A')
            }
            self.logger.info(f"爬虫 {self.name} 已关闭，统计信息: {stats_summary}")
        else:
            self.logger.info(f"爬虫 {self.name} 已关闭")

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}')"
    
    def __repr__(self) -> str:
        return self.__str__()
    
    def set_custom_setting(self, key: str, value: Any) -> 'Spider':
        """
        设置自定义配置（链式调用）
        
        :param key: 配置键名
        :param value: 配置值
        :return: self（支持链式调用）
        
        示例:
            spider.set_custom_setting('CONCURRENCY', 10)\
                  .set_custom_setting('DOWNLOAD_DELAY', 1.0)
        """
        if not hasattr(self, 'custom_settings') or self.custom_settings is None:
            self.custom_settings = {}
        
        self.custom_settings[key] = value
        self.logger.debug(f"设置自定义配置: {key} = {value}")
        
        # 如果已绑定crawler，立即应用设置
        if self.crawler:
            self.crawler.settings.set(key, value)
            
        return self
    
    def get_custom_setting(self, key: str, default: Any = None) -> Any:
        """
        获取自定义配置值
        
        :param key: 配置键名 
        :param default: 默认值
        :return: 配置值
        """
        if hasattr(self, 'custom_settings') and self.custom_settings:
            return self.custom_settings.get(key, default)
        return default
    
    def get_spider_info(self) -> Dict[str, Any]:
        """
        获取爬虫详细信息
        
        :return: 爬虫信息字典
        """
        info = {
            'name': self.name,
            'class_name': self.__class__.__name__,
            'module': self.__module__,
            'start_urls_count': len(self.start_urls) if self.start_urls else 0,
            'allowed_domains_count': len(self.allowed_domains) if self.allowed_domains else 0,
            'custom_settings_count': len(self.custom_settings) if self.custom_settings else 0,
            'is_distributed': self._is_distributed_mode() if self.crawler else None,
            'has_crawler': self.crawler is not None,
            'logger_name': self.logger.name if hasattr(self, 'logger') else None
        }
        
        # 添加方法检查
        info['methods'] = {
            'has_parse': callable(getattr(self, 'parse', None)),
            'has_spider_opened': callable(getattr(self, 'spider_opened', None)),
            'has_spider_closed': callable(getattr(self, 'spider_closed', None)),
            'has_start_requests': callable(getattr(self, 'start_requests', None))
        }
        
        return info
    
    def make_request(self, url: str, callback=None, **kwargs) -> Request:
        """
        便捷方法：创建 Request 对象
        
        :param url: 请求URL
        :param callback: 回调函数（默认为parse）
        :param kwargs: 其他Request参数
        :return: Request对象
        """
        return Request(
            url=url,
            callback=callback or self.parse,
            meta={'spider_name': self.name},
            **kwargs
        )


# === 高级爬虫功能扩展 ===

class SpiderStatsTracker:
    """
    爬虫统计跟踪器
    提供详细的性能监控功能
    """
    
    def __init__(self, spider_name: str):
        self.spider_name = spider_name
        self.start_time = None
        self.end_time = None
        self.request_count = 0
        self.response_count = 0
        self.item_count = 0
        self.error_count = 0
        self.domain_stats = {}
        
    def start_tracking(self):
        """开始统计"""
        import time
        self.start_time = time.time()
        
    def stop_tracking(self):
        """停止统计"""
        import time
        self.end_time = time.time()
        
    def record_request(self, url: str):
        """记录请求"""
        self.request_count += 1
        from urllib.parse import urlparse
        domain = urlparse(url).netloc
        self.domain_stats[domain] = self.domain_stats.get(domain, 0) + 1
        
    def record_response(self):
        """记录响应"""
        self.response_count += 1
        
    def record_item(self):
        """记录Item"""
        self.item_count += 1
        
    def record_error(self):
        """记录错误"""
        self.error_count += 1
        
    def get_summary(self) -> Dict[str, Any]:
        """获取统计摘要"""
        duration = (self.end_time - self.start_time) if (self.start_time and self.end_time) else 0
        
        return {
            'spider_name': self.spider_name,
            'duration_seconds': round(duration, 2),
            'requests': self.request_count,
            'responses': self.response_count,
            'items': self.item_count,
            'errors': self.error_count,
            'success_rate': round((self.response_count / max(1, self.request_count)) * 100, 2),
            'requests_per_second': round(self.request_count / max(1, duration), 2),
            'top_domains': sorted(
                self.domain_stats.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:5]
        }


def create_spider_from_template(name: str, start_urls: List[str], **options) -> Type[Spider]:
    """
    从模板快速创建爬虫类
    
    :param name: 爬虫名称
    :param start_urls: 起始URL列表
    :param options: 其他选项
    :return: 新创建的爬虫类
    
    示例:
        MySpider = create_spider_from_template(
            name='quick_spider',
            start_urls=['http://example.com'],
            allowed_domains=['example.com'],
            custom_settings={'CONCURRENCY': 5}
        )
    """
    
    # 动态创建爬虫类
    class_attrs = {
        'name': name,
        'start_urls': start_urls,
        'allowed_domains': options.get('allowed_domains', []),
        'custom_settings': options.get('custom_settings', {})
    }
    
    # 添加自定义parse方法
    if 'parse_function' in options:
        class_attrs['parse'] = options['parse_function']
    else:
        def default_parse(self, response):
            """默认解析方法"""
            yield {'url': response.url, 'title': getattr(response, 'title', 'N/A')}
        class_attrs['parse'] = default_parse
    
    # 创建类名
    class_name = options.get('class_name', f"Generated{name.replace('_', '').title()}Spider")
    
    # 动态创建类
    spider_class = type(class_name, (Spider,), class_attrs)
    
    get_logger(__name__).info(f"动态创建爬虫类: {class_name} (name='{name}')")
    
    return spider_class


# === 公共只读接口 ===
def get_global_spider_registry() -> dict[str, Type[Spider]]:
    """
    获取全局爬虫注册表的副本
    
    :return: 爬虫注册表的副本
    """
    return _DEFAULT_SPIDER_REGISTRY.copy()


def get_spider_by_name(name: str) -> Optional[Type[Spider]]:
    """
    根据名称获取爬虫类
    
    :param name: 爬虫名称
    :return: 爬虫类或None
    """
    return _DEFAULT_SPIDER_REGISTRY.get(name)


def get_all_spider_classes() -> List[Type[Spider]]:
    """
    获取所有注册的爬虫类
    
    :return: 爬虫类列表
    """
    return list(set(_DEFAULT_SPIDER_REGISTRY.values()))


def get_spider_names() -> List[str]:
    """
    获取所有爬虫名称
    
    :return: 爬虫名称列表
    """
    return list(_DEFAULT_SPIDER_REGISTRY.keys())


def is_spider_registered(name: str) -> bool:
    """
    检查爬虫是否已注册
    
    :param name: 爬虫名称
    :return: 是否已注册
    """
    return name in _DEFAULT_SPIDER_REGISTRY


def unregister_spider(name: str) -> bool:
    """
    取消注册爬虫（仅用于测试）
    
    :param name: 爬虫名称
    :return: 是否成功取消注册
    """
    if name in _DEFAULT_SPIDER_REGISTRY:
        del _DEFAULT_SPIDER_REGISTRY[name]
        return True
    return False


# 导出的公共接口
__all__ = [
    'Spider',
    'SpiderMeta', 
    'SpiderStatsTracker',
    'create_spider_from_template',
    'get_global_spider_registry',
    'get_spider_by_name',
    'get_all_spider_classes',
    'get_spider_names',
    'is_spider_registered',
    'unregister_spider'
]

