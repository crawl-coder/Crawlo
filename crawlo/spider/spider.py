#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
Crawlo Spider 核心类
===================
提供爬虫基类和自动注册机制。

核心功能:
- Spider 基类：所有爬虫的基础类
- SpiderMeta 元类：自动注册爬虫
- SpiderStatsTracker：性能统计
- 模板创建工具
- 全局注册表操作函数
"""
from __future__ import annotations

from typing import Type, Any, Optional, List, Dict, Iterator, TYPE_CHECKING, Union, cast
from urllib.parse import urlparse
import warnings

# 延迟导入 Request 和 Response 用于类型注解
if TYPE_CHECKING:
    from crawlo.http.request import Request
    from crawlo.http.response import Response
    from crawlo.crawler import Crawler
    from crawlo.settings.setting_manager import SettingManager

# 运行时导入 Request（避免循环依赖）
from crawlo.http.request import Request as RequestClass
from crawlo.spider.exceptions import SpiderNameConflictWarning
from crawlo.spider.registry import (  # noqa: F401  # 向后兼容 re-export
    _DEFAULT_SPIDER_REGISTRY,
    _SPIDER_CONFLICTS,
    get_global_spider_registry,
    get_spider_by_name,
    get_all_spider_classes,
    get_spider_names,
    is_spider_registered,
    unregister_spider,
    register_spider,
    reset_spider_registry,
)
from crawlo.spider.stats import SpiderStatsTracker  # noqa: F401  # 向后兼容 re-export
from crawlo.spider.discovery import SpiderDiscoveryState  # noqa: F401  # 向后兼容 re-export

# 冲突追踪表：name -> [候选类完整路径列表]
# SpiderMeta 不再在 import 阶段 raise，而是后注册覆盖先注册 + warning，
# 冲突的候选类记入此表，get_spider_by_name 解析时抛 AmbiguousSpiderError。

class SpiderMeta(type):
    """
    爬虫元类，提供自动注册功能

    功能:
    - 自动注册爬虫到全局注册表
    - 名称冲突时不再 raise，改为后注册覆盖先注册 + warnings.warn
    - 冲突候选类记入 _SPIDER_CONFLICTS，解析时抛 AmbiguousSpiderError
    """

    def __new__(mcs, name: str, bases: tuple, namespace: Dict[str, Any], **kwargs):
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

        # 检查名称冲突：不再 raise，改为后注册覆盖 + warning
        full_path = f"{cls.__module__}.{cls.__name__}"
        if spider_name in _DEFAULT_SPIDER_REGISTRY:
            existing_class = _DEFAULT_SPIDER_REGISTRY[spider_name]
            existing_path = f"{existing_class.__module__}.{existing_class.__name__}"
            # 记录冲突候选
            if spider_name not in _SPIDER_CONFLICTS:
                _SPIDER_CONFLICTS[spider_name] = [existing_path]
            if full_path not in _SPIDER_CONFLICTS[spider_name]:
                _SPIDER_CONFLICTS[spider_name].append(full_path)
            # 发出警告（不阻断 import）
            warnings.warn(
                f"爬虫名称 '{spider_name}' 冲突：{full_path} 覆盖了 {existing_path}。"
                f" 使用 get_spider_by_name('{spider_name}') 时将抛出 AmbiguousSpiderError，"
                f" 请使用 register_spider('{spider_name}', cls, override=True) 显式指定。",
                SpiderNameConflictWarning,
                stacklevel=2,
            )

        # 注册爬虫（后注册覆盖先注册）
        _DEFAULT_SPIDER_REGISTRY[spider_name] = cast(Type['Spider'], cls)
        # 延迟初始化logger避免模块级别阻塞
        # 注意：日志系统可能尚未初始化，因此捕获异常但不影响注册流程
        try:
            from crawlo.logging import get_logger
            get_logger(__name__).debug(f"自动注册爬虫: {spider_name} -> {cls.__name__}")
        except Exception as e:
            get_logger(__name__).debug("Suppressed exception: %s", e)

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
    name: str
    
    # 可选属性
    start_urls: Optional[List[str]]
    custom_settings: Optional[Dict[str, Any]]
    allowed_domains: Optional[List[str]]

    def __init__(self, name: Optional[str] = None, **kwargs):
        """
        初始化爬虫实例
        
        Args:
            name: 爬虫名称（可选，默认使用类属性）
            **kwargs: 其他初始化参数
        """
        # 初始化基本属性
        if not hasattr(self, 'start_urls') or self.start_urls is None:
            self.start_urls = []
        if not hasattr(self, 'custom_settings') or self.custom_settings is None:
            self.custom_settings = {}
        if not hasattr(self, 'allowed_domains') or self.allowed_domains is None:
            self.allowed_domains = []
            
        # 设置爬虫名称
        # 注意：name 已由 SpiderMeta 验证为字符串类型且唯一
        # 这里允许运行时覆盖 name（虽然不推荐）
        if name is not None:
            self.name = name
        # 否则使用类属性 name（已由元类验证）
        
        # 初始化其他属性
        self.crawler: Optional['Crawler'] = None
        # 延迟初始化logger避免阻塞
        self._logger = None
        self.stats = None
        self._pending_settings: Optional[Dict[str, Any]] = None
        
        # 应用额外参数
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    @property
    def logger(self):
        """延迟初始化logger
        
        原因：
        - 避免在模块导入时初始化日志系统
        - 日志系统可能依赖其他尚未初始化的组件
        - 延迟到第一次使用时初始化，确保依赖就绪
        """
        if self._logger is None:
            from crawlo.logging import get_logger
            self._logger = get_logger(self.name)
        return self._logger

    @classmethod
    def create_instance(cls, crawler: 'Crawler') -> 'Spider':
        """
        创建爬虫实例并绑定 crawler
        
        Args:
            crawler: Crawler 实例
            
        Returns:
            Spider: 爬虫实例
        """
        spider = cls()
        spider.crawler = crawler
        spider.stats = getattr(crawler, 'stats', None)
        
        # 合并自定义设置 - 使用延迟应用避免初始化时的循环依赖
        if hasattr(spider, 'custom_settings') and spider.custom_settings:
            # 延迟到真正需要时才应用设置
            spider._pending_settings = spider.custom_settings.copy()
            spider.logger.debug(f"准备应用 {len(spider.custom_settings)} 项自定义设置")
        
        return spider
    
    def apply_pending_settings(self) -> None:
        """应用待处理的设置（在初始化完成后调用）"""
        if self._pending_settings:
            for key, value in self._pending_settings.items():
                if self.crawler and self.crawler.settings:
                    self.crawler.settings.set(key, value)
                    self.logger.debug(f"应用自定义设置: {key} = {value}")
            # 清除待处理的设置
            self._pending_settings = None

    def start_requests(self) -> Iterator['Request']:
        """
        生成初始请求
        
        默认行为:
        - 使用 start_urls 生成请求
        - 智能检测分布式模式决定是否去重
        - 支持单个 start_url 属性（兼容性）
        - 支持批量生成优化（大规模URL场景）
        
        Returns:
            Iterator[Request]: 请求迭代器
        """
        # 检测是否为分布式模式
        self._is_distributed_mode()
        
        # 获取批量处理配置
        batch_size = self._get_batch_size()
        
        # 从 start_urls 生成请求
        if self.start_urls:
            generated_count = 0
            for url in self.start_urls:
                if self._is_allowed_domain(url):
                    yield RequestClass(
                        url=url, 
                        callback=self.parse,
                        dont_filter=False,  # 始终经过过滤器，由过滤器决定是否去重
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
                yield RequestClass(
                    url=url, 
                    callback=self.parse,
                    dont_filter=False,  # 始终经过过滤器，由过滤器决定是否去重
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
        
        Returns:
            int: 批量大小（0表示无限制）
        """
        if not self.crawler or not self.crawler.settings:
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
        
        Returns:
            bool: 是否为分布式模式
        """
        if not self.crawler or not self.crawler.settings:
            return False
            
        settings: 'SettingManager' = self.crawler.settings
        
        # 检查多个条件来判断是否为分布式模式
        queue_type = settings.get('QUEUE_TYPE', 'memory') if settings else 'memory'
        filter_class = settings.get('FILTER_CLASS', '') if settings else ''
        run_mode = settings.get('RUN_MODE', 'standalone') if settings else 'standalone'
        
        # 分布式模式的标志
        is_redis_queue = queue_type == 'redis'
        is_redis_filter = 'aioredis_filter' in (filter_class.lower() if filter_class else '')
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
        
        Args:
            url: 要检查的URL
            
        Returns:
            bool: 是否允许
        """
        if not self.allowed_domains:
            return True
            
        # urlparse 已在顶部导入
        try:
            domain = urlparse(url).netloc.lower()
            return any(
                domain == allowed.lower() or domain.endswith('.' + allowed.lower())
                for allowed in self.allowed_domains
            )
        except Exception as e:
            self.logger.warning(f"URL解析失败: {url} - {e}")
            return False

    def parse(self, response: 'Response') -> Iterator[Union[Dict[str, Any], 'Request']]:
        """
        解析响应的主方法（必须实现）
        
        Args:
            response: 响应对象
            
        Returns:
            Iterator[Union[Dict[str, Any], Request]]: 数据字典或请求对象的迭代器
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
    
    async def spider_opened(self) -> None:
        """
        爬虫开启时调用的钩子函数
        
        可用于:
        - 初始化资源
        - 连接数据库
        - 设置初始状态
        """
        self.logger.info(f"Spider {self.name} opened")
    
    async def spider_closed(self) -> None:
        """
        爬虫关闭时调用的钩子函数
        
        可用于:
        - 清理资源
        - 关闭数据库连接
        """
        # 不再输出任何信息，避免与统计信息重复
        # 统计信息由StatsCollector负责输出

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}')"
    
    def __repr__(self) -> str:
        return self.__str__()
    
    def set_custom_setting(self, key: str, value: Any) -> 'Spider':
        """
        设置自定义配置（链式调用）
        
        Args:
            key: 配置键名
            value: 配置值
            
        Returns:
            Spider: 支持链式调用
        """
        if not hasattr(self, 'custom_settings') or self.custom_settings is None:
            self.custom_settings = {}
        
        self.custom_settings[key] = value
        self.logger.debug(f"设置自定义配置: {key} = {value}")
        
        # 如果已绑定crawler，立即应用设置
        if self.crawler and self.crawler.settings:
            self.crawler.settings.set(key, value)
            
        return self
    
    def get_custom_setting(self, key: str, default: Any = None) -> Any:
        """
        获取自定义配置值
        
        Args:
            key: 配置键名 
            default: 默认值
            
        Returns:
            Any: 配置值
        """
        if hasattr(self, 'custom_settings') and self.custom_settings:
            return self.custom_settings.get(key, default)
        return default
    
    def get_spider_info(self) -> Dict[str, Any]:
        """
        获取爬虫详细信息
        
        Returns:
            Dict[str, Any]: 爬虫信息字典
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
    
    def make_request(self, url: str, callback=None, **kwargs) -> 'Request':
        """
        便捷方法：创建 Request 对象
        
        Args:
            url: 请求URL
            callback: 回调函数（默认为parse）
            **kwargs: 其他Request参数
            
        Returns:
            Request: Request对象
        """
        from crawlo.http.request import Request
        return Request(
            url=url,
            callback=callback or self.parse,
            meta={'spider_name': self.name},
            **kwargs
        )


# === 高级爬虫功能扩展 ===

def create_spider_from_template(name: str, start_urls: List[str], **options) -> Type[Spider]:
    """
    从模板快速创建爬虫类
    
    Args:
        name: 爬虫名称
        start_urls: 起始URL列表
        **options: 其他选项
        
    Returns:
        Type[Spider]: 新创建的爬虫类
        
    示例:
        MySpider = create_spider_from_template(
            name='quick_spider',
            start_urls=['http://example.com'],
            allowed_domains=['example.com'],
            custom_settings={'CONCURRENCY': 5}
        )
    """
    from crawlo.logging import get_logger
    
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
