#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
重构的Crawler模块
解决冗余、提升健壮性
"""
import asyncio
import signal
import time
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Type, Optional, Set, List, Union, Dict, Any
from contextlib import asynccontextmanager

from .spider import Spider
from .core.engine import Engine
from .subscriber import Subscriber
from .extension import ExtensionManager
from .stats_collector import StatsCollector
from .settings.setting_manager import SettingManager
from crawlo.utils.log import get_logger

logger = get_logger(__name__)


class CrawlerState(Enum):
    """Crawler状态枚举"""
    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    READY = "ready"
    RUNNING = "running"
    CLOSING = "closing"
    CLOSED = "closed"
    ERROR = "error"


@dataclass
class CrawlerMetrics:
    """统一的性能指标数据类"""
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    initialization_time: float = 0
    crawl_duration: float = 0
    request_count: int = 0
    error_count: int = 0
    memory_peak: float = 0
    
    def get_total_duration(self) -> float:
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0.0
    
    def get_stats_dict(self) -> Dict[str, Any]:
        return {
            'total_duration': self.get_total_duration(),
            'initialization_time': self.initialization_time,
            'crawl_duration': self.crawl_duration,
            'request_count': self.request_count,
            'error_count': self.error_count,
            'memory_peak': self.memory_peak,
        }


class ComponentFactory:
    """组件工厂 - 统一创建和配置组件"""
    
    @staticmethod
    def create_spider(spider_cls: Type[Spider], crawler) -> Spider:
        """创建和验证Spider实例"""
        spider = spider_cls.create_instance(crawler)
        ComponentFactory._validate_spider(spider)
        return spider
    
    @staticmethod
    def _validate_spider(spider: Spider):
        """Spider验证逻辑"""
        if not getattr(spider, 'name', None):
            raise AttributeError(f"Spider '{spider.__class__.__name__}' must define 'name' attribute")
        
        if not callable(getattr(spider, 'start_requests', None)):
            raise AttributeError(f"Spider '{spider.name}' must implement 'start_requests' method")
        
        start_urls = getattr(spider, 'start_urls', [])
        if isinstance(start_urls, str):
            raise TypeError(f"Spider '{spider.name}' start_urls must be list/tuple, not string")
        
        if not callable(getattr(spider, 'parse', None)):
            logger.warning(f"Spider '{spider.name}' missing 'parse' method")
    
    @staticmethod
    def create_engine(crawler) -> Engine:
        """创建Engine"""
        engine = Engine(crawler)
        engine.engine_start()
        return engine
    
    @staticmethod
    def create_stats(crawler) -> StatsCollector:
        """创建统计收集器"""
        return StatsCollector(crawler)
    
    @staticmethod
    def create_subscriber() -> Subscriber:
        """创建事件订阅器"""
        return Subscriber()
    
    @staticmethod
    def create_extension(crawler) -> ExtensionManager:
        """创建扩展管理器"""
        return ExtensionManager.create_instance(crawler)


class RefactoredCrawler:
    """
    重构的Crawler类
    
    改进要点：
    1. 状态机管理
    2. 统一的组件工厂
    3. 简化的初始化流程
    4. 更好的错误处理
    """
    
    def __init__(self, spider_cls: Type[Spider], settings: SettingManager, context=None):
        # 基础属性
        self.spider_cls = spider_cls
        self.settings = settings.copy()
        self.context = context
        
        # 状态管理
        self._state = CrawlerState.UNINITIALIZED
        self._state_lock = asyncio.Lock()
        
        # 组件
        self.spider: Optional[Spider] = None
        self.engine: Optional[Engine] = None
        self.stats: Optional[StatsCollector] = None
        self.subscriber: Optional[Subscriber] = None
        self.extension: Optional[ExtensionManager] = None
        
        # 性能指标
        self.metrics = CrawlerMetrics()
        
        # 确保框架初始化
        self._ensure_framework_ready()
    
    def _ensure_framework_ready(self):
        """确保框架就绪 - 单一职责"""
        from crawlo.core.framework_initializer import get_framework_initializer, initialize_framework
        
        init_manager = get_framework_initializer()
        if not init_manager.is_ready:
            initialize_framework()
    
    async def crawl(self):
        """主要的爬取流程"""
        async with self._state_context(CrawlerState.RUNNING):
            init_start = time.time()
            self.metrics.start_time = init_start
            
            try:
                # 阶段1：初始化组件
                await self._initialize_components()
                self.metrics.initialization_time = time.time() - init_start
                
                # 阶段2：验证状态
                self._validate_state()
                
                # 阶段3：执行爬取
                crawl_start = time.time()
                await self.engine.start_spider(self.spider)
                self.metrics.crawl_duration = time.time() - crawl_start
                
                # 阶段4：记录成功
                self.metrics.end_time = time.time()
                self._log_completion()
                
            except Exception as e:
                self.metrics.error_count += 1
                self._log_error(e)
                raise
            finally:
                await self._ensure_cleanup()
    
    @asynccontextmanager
    async def _state_context(self, target_state: CrawlerState):
        """状态上下文管理器"""
        async with self._state_lock:
            if self._state == CrawlerState.CLOSED:
                raise RuntimeError("Crawler已关闭，无法重新使用")
            
            previous_state = self._state
            self._state = target_state
            
        try:
            yield
        except Exception:
            async with self._state_lock:
                self._state = CrawlerState.ERROR
            raise
        finally:
            async with self._state_lock:
                if self._state == target_state:
                    if target_state == CrawlerState.RUNNING:
                        self._state = CrawlerState.READY
    
    async def _initialize_components(self):
        """组件初始化 - 统一管理"""
        self._state = CrawlerState.INITIALIZING
        
        # 按依赖顺序创建组件
        self.subscriber = ComponentFactory.create_subscriber()
        self.spider = ComponentFactory.create_spider(self.spider_cls, self)
        self.engine = ComponentFactory.create_engine(self)
        self.stats = ComponentFactory.create_stats(self)
        
        # 配置Spider
        self._configure_spider()
        
        logger.debug(f"所有组件初始化完成: {self.spider.name}")
    
    def _configure_spider(self):
        """配置Spider"""
        from crawlo.project import merge_settings
        from crawlo.event import spider_opened, spider_closed
        
        # 订阅事件
        self.subscriber.subscribe(self.spider.spider_opened, event=spider_opened)
        self.subscriber.subscribe(self.spider.spider_closed, event=spider_closed)
        
        # 合并设置
        merge_settings(self.spider, self.settings)
    
    def _validate_state(self):
        """状态验证"""
        required_components = [
            ('spider', self.spider),
            ('engine', self.engine),
            ('stats', self.stats),
            ('subscriber', self.subscriber)
        ]
        
        for name, component in required_components:
            if component is None:
                raise RuntimeError(f"{name} 未初始化")
        
        if not self.spider.name:
            raise ValueError("Spider name 不能为空")
    
    def _log_completion(self):
        """记录完成信息"""
        duration = self.metrics.get_total_duration()
        logger.info(f"Spider {self.spider.name} 完成，耗时 {duration:.2f} 秒")
    
    def _log_error(self, error: Exception):
        """记录错误信息"""
        spider_name = getattr(self.spider, 'name', 'Unknown')
        logger.error(f"Spider {spider_name} 运行失败: {error}", exc_info=True)
    
    async def _ensure_cleanup(self):
        """确保清理资源"""
        if self._state != CrawlerState.CLOSED:
            await self.close()
    
    async def close(self, reason: str = 'finished'):
        """关闭Crawler"""
        async with self._state_lock:
            if self._state == CrawlerState.CLOSED:
                return
                
            self._state = CrawlerState.CLOSING
            
        try:
            # 通知关闭事件
            if self.subscriber:
                from crawlo.event import spider_closed
                await self.subscriber.notify(spider_closed)
            
            # 统计数据收集
            if self.stats and self.spider:
                self.stats.close_spider(spider=self.spider, reason=reason)
            
            # 记录关闭信息
            spider_name = getattr(self.spider, 'name', 'Unknown')
            duration = self.metrics.get_total_duration()
            logger.info(f"Spider '{spider_name}' 已关闭，原因: {reason}，耗时: {duration:.2f} 秒")
            
        except Exception as e:
            logger.error(f"关闭Crawler时出错: {e}", exc_info=True)
        finally:
            async with self._state_lock:
                self._state = CrawlerState.CLOSED
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        return {
            'state': self._state.value,
            'spider_name': getattr(self.spider, 'name', 'Unknown'),
            **self.metrics.get_stats_dict()
        }


class ImprovedCrawlerProcess:
    """
    改进的CrawlerProcess
    减少重复代码，提升健壮性
    """
    
    def __init__(self, settings=None, max_concurrency=None, spider_modules=None):
        self.settings = settings or self._get_default_settings()
        self.max_concurrency = max_concurrency or self.settings.get('CONCURRENCY', 3)
        self.crawlers: Set[RefactoredCrawler] = set()
        self._spider_registry = {}
        
        # 自动发现Spider
        if spider_modules:
            self._auto_discover(spider_modules)
        
        # 只输出一次框架启动信息
        self._log_startup_info()
    
    def _get_default_settings(self) -> SettingManager:
        """获取默认设置"""
        from crawlo.core.framework_initializer import initialize_framework
        return initialize_framework()
    
    def _auto_discover(self, modules: List[str]):
        """自动发现Spider模块"""
        from .spider import get_global_spider_registry
        
        # 导入模块触发Spider注册
        for module_name in modules:
            try:
                __import__(module_name)
            except ImportError as e:
                logger.warning(f"无法导入模块 {module_name}: {e}")
        
        self._spider_registry = get_global_spider_registry()
        logger.debug(f"发现 {len(self._spider_registry)} 个Spider")
    
    def _log_startup_info(self):
        """统一的框架启动信息输出"""
        from crawlo.utils.log import get_logger
        
        framework_logger = get_logger('crawlo.framework')
        version = self.settings.get('VERSION', '1.0.0')
        run_mode = self.settings.get('RUN_MODE', 'standalone')
        
        framework_logger.info(f"Crawlo Framework Started {version}")
        framework_logger.info(f"Run Mode: {run_mode}")
        
        # 运行模式信息已改为DEBUG级别
        mode_info = self.settings.get('_mode_info')
        if mode_info:
            framework_logger.debug(mode_info)
    
    async def crawl(self, spiders):
        """执行爬取任务"""
        spider_classes = self._resolve_spiders(spiders)
        
        if not spider_classes:
            raise ValueError("至少需要一个Spider")
        
        # 创建Crawler实例
        crawlers = []
        for spider_cls in spider_classes:
            crawler = RefactoredCrawler(spider_cls, self.settings)
            crawlers.append(crawler)
            self.crawlers.add(crawler)
        
        # 并发执行
        tasks = [crawler.crawl() for crawler in crawlers]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理结果
        successful = sum(1 for r in results if not isinstance(r, Exception))
        failed = len(results) - successful
        
        logger.info(f"爬取完成: {successful} 成功, {failed} 失败")
        
        return {
            'total': len(results),
            'successful': successful,
            'failed': failed,
            'results': results
        }
    
    def _resolve_spiders(self, spiders):
        """解析Spider参数"""
        if isinstance(spiders, str):
            if spiders in self._spider_registry:
                return [self._spider_registry[spiders]]
            else:
                raise ValueError(f"未找到Spider: {spiders}")
        
        if isinstance(spiders, type):
            return [spiders]
        
        if isinstance(spiders, (list, tuple)):
            result = []
            for spider in spiders:
                result.extend(self._resolve_spiders(spider))
            return result
        
        raise ValueError(f"不支持的Spider类型: {type(spiders)}")


# 向后兼容的导出
Crawler = RefactoredCrawler
CrawlerProcess = ImprovedCrawlerProcess