#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Crawler系统
==========

核心组件：
- Crawler: 爬虫核心控制器，负责单个爬虫的生命周期管理
- CrawlerProcess: 爬虫进程管理器，支持单个/多个爬虫运行

设计原则：
1. 单一职责 - 每个类只负责一个明确的功能
2. 依赖注入 - 通过工厂创建组件，便于测试
3. 状态管理 - 清晰的状态转换和生命周期
4. 错误处理 - 优雅的错误处理和恢复机制
5. 资源管理 - 统一的资源注册和清理机制
"""

import asyncio
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Type, Dict, Any, List, Union, TYPE_CHECKING, cast

from crawlo.factories import get_component_registry
from crawlo.initialization import initialize_framework, is_framework_ready
from crawlo.logging import get_logger
from crawlo.utils.resource_manager import ResourceManager, ResourceType

if TYPE_CHECKING:
    from crawlo.spider import Spider
    from crawlo.settings.setting_manager import SettingManager


class CrawlerState(Enum):
    """Crawler状态枚举"""
    CREATED = "created"
    INITIALIZING = "initializing"
    READY = "ready"
    RUNNING = "running"
    CLOSING = "closing"
    CLOSED = "closed"
    ERROR = "error"


@dataclass
class CrawlerMetrics:
    """Crawler性能指标"""
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    initialization_duration: float = 0.0
    crawl_duration: float = 0.0
    request_count: int = 0
    success_count: int = 0
    error_count: int = 0
    
    def get_total_duration(self) -> float:
        """
        获取总执行时间
        
        Returns:
            float: 总执行时间（秒）
        """
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0.0
    
    def get_success_rate(self) -> float:
        """
        获取成功率
        
        Returns:
            float: 成功率（百分比）
        """
        total = self.success_count + self.error_count
        return (self.success_count / total * 100) if total > 0 else 0.0


class Crawler:
    """
    爬虫核心控制器
    
    特点：
    1. 清晰的状态管理
    2. 依赖注入
    3. 组件化架构
    4. 完善的错误处理
    5. 统一的资源管理
    """
    
    def __init__(self, spider_cls: Type['Spider'], settings: Optional['SettingManager'] = None) -> None:
        """
        初始化爬虫控制器
        
        Args:
            spider_cls: 爬虫类
            settings: 配置管理器
        """
        self._spider_cls: Type['Spider'] = spider_cls
        self._settings: Optional['SettingManager'] = settings
        self._state: CrawlerState = CrawlerState.CREATED
        self._state_lock: asyncio.Lock = asyncio.Lock()
        
        # 组件
        self._spider: Optional['Spider'] = None
        self._engine: Any = None
        self._stats: Any = None
        self._subscriber: Any = None
        self._extension: Any = None
        
        # 指标
        self._metrics: CrawlerMetrics = CrawlerMetrics()
        
        # 资源管理器
        self._resource_manager: ResourceManager = ResourceManager(name=f"crawler.{spider_cls.__name__ if spider_cls else 'unknown'}")
        
        # 日志
        self._logger = get_logger(f'crawler.{spider_cls.__name__ if spider_cls else "unknown"}')
        
        # 确保框架已初始化
        self._ensure_framework_ready()
    
    def _ensure_framework_ready(self) -> None:
        """确保框架已准备就绪"""
        if not is_framework_ready():
            try:
                self._settings = initialize_framework(self._settings)
                self._logger.debug("Framework initialized successfully")
            except Exception as e:
                self._logger.warning(f"Framework initialization failed: {e}")
                # 使用降级策略
                if not self._settings:
                    from crawlo.settings.setting_manager import SettingManager
                    self._settings = SettingManager()
        
        # 确保是SettingManager实例
        if isinstance(self._settings, dict):
            from crawlo.settings.setting_manager import SettingManager
            settings_manager = SettingManager()
            settings_manager.update_attributes(self._settings)
            self._settings = settings_manager
    
    @property
    def state(self) -> CrawlerState:
        """
        获取当前状态
        
        Returns:
            CrawlerState: 当前状态
        """
        return self._state
    
    @property
    def spider(self) -> Optional['Spider']:
        """
        获取Spider实例
        
        Returns:
            Optional[Spider]: Spider实例
        """
        return self._spider
    
    @property
    def stats(self) -> Any:
        """
        获取Stats实例（向后兼容）
        
        Returns:
            Any: Stats实例
        """
        return self._stats
    
    @property 
    def metrics(self) -> CrawlerMetrics:
        """
        获取性能指标
        
        Returns:
            CrawlerMetrics: 性能指标
        """
        return self._metrics
    
    @property
    def settings(self) -> Optional['SettingManager']:
        """
        获取配置
        
        Returns:
            Optional[SettingManager]: 配置管理器
        """
        return self._settings
    
    @property
    def engine(self) -> Any:
        """
        获取Engine实例（向后兼容）
        
        Returns:
            Any: Engine实例
        """
        return self._engine
    
    @property
    def subscriber(self) -> Any:
        """
        获取Subscriber实例（向后兼容）
        
        Returns:
            Any: Subscriber实例
        """
        return self._subscriber
    
    @property
    def extension(self) -> Any:
        """
        获取Extension实例（向后兼容）
        
        Returns:
            Any: Extension实例
        """
        return self._extension
    
    @extension.setter
    def extension(self, value: Any) -> None:
        """
        设置Extension实例（向后兼容）
        
        Args:
            value: Extension实例
        """
        self._extension = value
    
    def _create_extension(self) -> Any:
        """
        创建Extension管理器（向后兼容）
        
        Returns:
            Any: Extension管理器
        """
        if self._extension is None:
            try:
                registry = get_component_registry()
                self._extension = registry.create('extension_manager', crawler=self)
            except Exception as e:
                from crawlo.exceptions import NotConfigured
                if isinstance(e, NotConfigured):
                    # 对于未配置启用的扩展，仅输出提示信息，不记录为错误
                    self._logger.info(f"Extension manager not created (disabled): {e}")
                else:
                    self._logger.warning(f"Failed to create extension manager: {e}")
        return self._extension
    
    async def close(self) -> None:
        """关闭爬虫（向后兼容）"""
        await self._cleanup()
    
    async def crawl(self) -> None:
        """执行爬取任务"""
        self._logger.info("开始爬取任务")
        try:
            async with self._lifecycle_manager():
                await self._initialize_components()
                await self._run_crawler()
        except asyncio.CancelledError:
            self._logger.info("爬取任务被取消")
            # 重新抛出CancelledError以便调用者可以正确处理
            raise
        except Exception as e:
            self._logger.error(f"爬取任务执行失败: {e}")
            raise
        finally:
            self._logger.info("爬取任务结束")
    
    @asynccontextmanager
    async def _lifecycle_manager(self):
        """生命周期管理"""
        self._metrics.start_time = time.time()
        
        try:
            yield
        except asyncio.CancelledError:
            self._logger.info("爬虫任务被取消，开始清理资源...")
            await self._cleanup()
            raise
        except Exception as e:
            await self._handle_error(e)
            raise
        finally:
            await self._cleanup()
            self._metrics.end_time = time.time()
    
    async def _initialize_components(self) -> None:
        """初始化组件"""
        async with self._state_lock:
            if self._state != CrawlerState.CREATED:
                raise RuntimeError(f"Cannot initialize from state {self._state}")
            
            self._state = CrawlerState.INITIALIZING
        
        init_start = time.time()
        
        try:
            # 使用组件工厂创建组件
            registry = get_component_registry()
            
            # 创建Subscriber（无依赖）
            self._subscriber = registry.create('subscriber')
            
            # 创建Spider
            self._spider = self._create_spider()
            
            # 创建Engine（需要crawler参数）
            self._engine = registry.create('engine', crawler=self)
            # 注册Engine到资源管理器
            if self._engine and hasattr(self._engine, 'close'):
                self._resource_manager.register(
                    self._engine,
                    lambda e: e.close() if hasattr(e, 'close') else None,
                    ResourceType.OTHER,
                    name="engine"
                )
            
            # 创建Stats（需要crawler参数）
            self._stats = registry.create('stats', crawler=self)
            
            # 创建Extension Manager (可选，需要crawler参数)
            try:
                self._extension = registry.create('extension_manager', crawler=self)
            except Exception as e:
                from crawlo.exceptions import NotConfigured
                if isinstance(e, NotConfigured):
                    # 对于未配置启用的扩展，仅输出提示信息，不记录为错误
                    self._logger.info(f"Extension manager not created (disabled): {e}")
                else:
                    self._logger.warning(f"Failed to create extension manager: {e}")
            
            self._metrics.initialization_duration = time.time() - init_start
            
            async with self._state_lock:
                self._state = CrawlerState.READY
            
            self._logger.debug(f"Crawler components initialized successfully in {self._metrics.initialization_duration:.2f}s")
            
        except Exception as e:
            async with self._state_lock:
                self._state = CrawlerState.ERROR
            raise RuntimeError(f"Component initialization failed: {e}")
    
    def _create_spider(self) -> 'Spider':
        """
        创建Spider实例
        
        Returns:
            Spider: Spider实例
            
        Raises:
            ValueError: Spider类无效
        """
        if not self._spider_cls:
            raise ValueError("Spider class not provided")
        
        # 检查Spider类的有效性
        if not hasattr(self._spider_cls, 'name'):
            raise ValueError("Spider class must have 'name' attribute")
        
        # 创建Spider实例
        spider = self._spider_cls()
        
        # 设置crawler引用
        if hasattr(spider, 'crawler'):
            spider.crawler = self  # type: ignore
        
        return spider
    
    async def _run_crawler(self) -> None:
        """运行爬虫引擎"""
        async with self._state_lock:
            if self._state != CrawlerState.READY:
                raise RuntimeError(f"Cannot run from state {self._state}")
            
            self._state = CrawlerState.RUNNING
        
        crawl_start = time.time()
        
        try:
            # 启动引擎
            if self._engine:
                await self._engine.start_spider(self._spider)
            else:
                raise RuntimeError("Engine not initialized")
            
            self._metrics.crawl_duration = time.time() - crawl_start
            
            self._logger.debug(f"Crawler completed successfully in {self._metrics.crawl_duration:.2f}s")
            
        except Exception as e:
            self._metrics.crawl_duration = time.time() - crawl_start
            raise RuntimeError(f"Crawler execution failed: {e}")
    
    async def _handle_error(self, error: Exception) -> None:
        """
        处理错误
        
        Args:
            error: 异常对象
        """
        async with self._state_lock:
            self._state = CrawlerState.ERROR
        
        self._metrics.error_count += 1
        self._logger.error(f"Crawler error: {error}", exc_info=True)
        
        # 这里可以添加错误恢复逻辑
    
    async def _cleanup(self) -> None:
        """清理资源"""
        async with self._state_lock:
            if self._state not in [CrawlerState.CLOSING, CrawlerState.CLOSED]:
                self._state = CrawlerState.CLOSING
        
        try:
            # 使用资源管理器统一清理
            self._logger.debug("开始清理Crawler资源...")
            cleanup_result = await self._resource_manager.cleanup_all()
            self._logger.debug(
                f"资源清理完成: {cleanup_result['success']}成功, "
                f"{cleanup_result['errors']}失败, 耗时{cleanup_result['duration']:.2f}s"
            )
            
            # 关闭各个组件（继续兼容旧逻辑）
            if self._engine and hasattr(self._engine, 'close'):
                try:
                    await self._engine.close()
                except Exception as e:
                    self._logger.warning(f"Engine cleanup failed: {e}")
            
            # 调用Spider的spider_closed方法
            if self._spider:
                try:
                    if asyncio.iscoroutinefunction(self._spider.spider_closed):
                        await self._spider.spider_closed()
                    else:
                        await asyncio.get_event_loop().run_in_executor(None, self._spider.spider_closed)
                except Exception as e:
                    self._logger.warning(f"Spider cleanup failed: {e}")
            
            # 调用StatsCollector的close_spider方法，设置reason和spider_name
            if self._stats and hasattr(self._stats, 'close_spider'):
                try:
                    # 使用默认的'finished'作为reason
                    self._stats.close_spider(self._spider, reason='finished')
                except Exception as e:
                    self._logger.warning(f"Stats close_spider failed: {e}")
            
            # 触发spider_closed事件，通知所有订阅者（包括扩展）
            # 传递reason参数，这里使用默认的'finished'作为reason
            if self.subscriber:
                from crawlo.event import CrawlerEvent
                await self.subscriber.notify(CrawlerEvent.SPIDER_CLOSED, reason='finished')
            
            if self._stats and hasattr(self._stats, 'close'):
                try:
                    close_result = self._stats.close()
                    if asyncio.iscoroutine(close_result):
                        await close_result
                except Exception as e:
                    self._logger.warning(f"Stats cleanup failed: {e}")
            
            async with self._state_lock:
                self._state = CrawlerState.CLOSED
            
            self._logger.debug("Crawler cleanup completed")
            
        except Exception as e:
            self._logger.error(f"Cleanup error: {e}")


class CrawlerProcess:
    """
    Crawler进程管理器 - 管理多个Crawler的执行
    
    简化版本，专注于核心功能
    """
    
    def __init__(self, settings: Optional['SettingManager'] = None, max_concurrency: int = 3, spider_modules: Optional[List[str]] = None) -> None:
        """
        初始化爬虫进程管理器
        
        Args:
            settings: 配置管理器
            max_concurrency: 最大并发数
            spider_modules: 爬虫模块列表
        """
        # 初始化框架配置
        self._settings: Optional['SettingManager'] = settings or initialize_framework()
        self._max_concurrency: int = max_concurrency
        self._crawlers: List[Crawler] = []
        self._semaphore: asyncio.Semaphore = asyncio.Semaphore(max_concurrency)
        self._logger = get_logger('crawler.process')
        
        # 信号处理相关
        from crawlo.utils.process_utils import ProcessSignalHandler
        self._signal_handler = ProcessSignalHandler(self._logger, self._crawlers)
        self._shutdown_event: asyncio.Event = self._signal_handler.shutdown_event
        self._shutdown_requested: bool = self._signal_handler.shutdown_requested
        
        # 如果没有显式提供spider_modules，则从settings中获取
        if spider_modules is None and self._settings:
            spider_modules = self._settings.get('SPIDER_MODULES', [])
            self._logger.debug(f"从settings中获取SPIDER_MODULES: {spider_modules}")
        
        self._spider_modules: List[str] = spider_modules or []  # 保存spider_modules
        
        # 如果提供了spider_modules，自动注册这些模块中的爬虫
        if self._spider_modules:
            self._register_spider_modules(self._spider_modules)
        
        # 指标
        self._start_time: Optional[float] = None
        self._end_time: Optional[float] = None
        
        # 注册信号处理器
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self):
        """设置信号处理器以优雅地处理关闭信号"""
        self._signal_handler.set_crawlers(self._crawlers)
        self._signal_handler.setup_signal_handlers()
    
    async def _graceful_shutdown(self):
        """优雅地关闭所有爬虫"""
        self._signal_handler.set_crawlers(self._crawlers)
        await self._signal_handler.graceful_shutdown()

    def _register_spider_modules(self, spider_modules: List[str]) -> None:
        """
        注册爬虫模块
        
        Args:
            spider_modules: 爬虫模块列表
        """
        from crawlo.utils.process_utils import SpiderDiscoveryUtils
        SpiderDiscoveryUtils.register_spider_modules(spider_modules, self._logger)
    
    def _auto_discover_spider_modules(self, spider_modules: List[str]) -> None:
        """
        自动发现并导入爬虫模块中的所有爬虫
        这个方法会扫描指定模块目录下的所有Python文件并自动导入
        
        Args:
            spider_modules: 爬虫模块列表
        """
        from crawlo.utils.process_utils import SpiderDiscoveryUtils
        SpiderDiscoveryUtils.auto_discover_spider_modules(spider_modules, self._logger)
    
    def is_spider_registered(self, name: str) -> bool:
        """
        检查爬虫是否已注册
        
        Args:
            name: 爬虫名称
            
        Returns:
            bool: 是否已注册
        """
        from crawlo.spider import get_global_spider_registry
        registry = get_global_spider_registry()
        return name in registry
    
    def get_spider_class(self, name: str) -> Optional[Type['Spider']]:
        """
        获取爬虫类
        
        Args:
            name: 爬虫名称
            
        Returns:
            Optional[Type[Spider]]: 爬虫类
        """
        from crawlo.spider import get_global_spider_registry
        registry = get_global_spider_registry()
        return registry.get(name)
    
    def get_spider_names(self) -> List[str]:
        """
        获取所有注册的爬虫名称
        
        Returns:
            List[str]: 爬虫名称列表
        """
        from crawlo.spider import get_global_spider_registry
        registry = get_global_spider_registry()
        return list(registry.keys())

    
    async def crawl(self, spider_cls_or_name: Union[Type['Spider'], str, List[Union[Type['Spider'], str]]], settings: Optional[Dict[str, Any]] = None) -> Union[Crawler, List[Union[Crawler, BaseException]]]:
        """
        运行爬虫（单个或多个）
        
        Args:
            spider_cls_or_name: 爬虫类/名称或爬虫类/名称列表
            settings: 配置字典
            
        Returns:
            Union[Crawler, List[Union[Crawler, BaseException]]]: 单个爬虫实例或爬虫实例列表
        """
        # Windows平台兼容性处理
        import sys
        if sys.platform.lower().startswith('win'):
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
        # 判断输入是单个还是多个爬虫
        if not isinstance(spider_cls_or_name, list):
            # 单个爬虫
            try:
                spider_cls = self._resolve_spider_class(spider_cls_or_name)
                
                # 记录启动的爬虫名称（符合规范要求）
                from crawlo.logging import get_logger
                logger = get_logger('crawlo.framework')
                logger.info(f"Starting spider: {spider_cls.name}")
                
                merged_settings = self._merge_settings(settings)
                crawler = Crawler(spider_cls, merged_settings)
                
                async with self._semaphore:
                    await crawler.crawl()
                
                # 清理crawler资源，防止内存泄漏
                try:
                    if hasattr(crawler, '_resource_manager'):
                        await crawler._resource_manager.cleanup_all()
                    self._logger.debug(f"Cleaned up crawler: {spider_cls.name}")
                except Exception as e:
                    self._logger.warning(f"Failed to cleanup crawler: {e}")
                
                return crawler
            except Exception as e:
                self._logger.error(f"Error running crawler: {e}")
                raise
        else:
            # 多个爬虫
            spider_classes_or_names = spider_cls_or_name
            self._start_time = time.time()
            
            try:
                spider_classes = []
                for cls_or_name in spider_classes_or_names:
                    spider_cls = self._resolve_spider_class(cls_or_name)
                    spider_classes.append(spider_cls)
                
                # 记录启动的爬虫名称（符合规范要求）
                spider_names = [cls.name for cls in spider_classes]
                from crawlo.logging import get_logger
                logger = get_logger('crawlo.framework')
                if len(spider_names) == 1:
                    logger.info(f"Starting spider: {spider_names[0]}")
                else:
                    logger.info(f"Starting spiders: {', '.join(spider_names)}")
                
                tasks = []
                for spider_cls in spider_classes:
                    merged_settings = self._merge_settings(settings)
                    crawler = Crawler(spider_cls, merged_settings)
                    self._crawlers.append(crawler)
                    
                    task = asyncio.create_task(self._run_with_semaphore(crawler))
                    tasks.append(task)
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # 处理结果
                successful = sum(1 for r in results if not isinstance(r, Exception))
                failed = len(results) - successful
                
                self._logger.info(f"Crawl completed: {successful} successful, {failed} failed")
                
                return cast(List[Union[Crawler, BaseException]], results)
                
            finally:
                # 清理所有crawler，防止资源累积
                self._logger.debug(f"Cleaning up {len(self._crawlers)} crawler(s)...")
                for crawler in self._crawlers:
                    try:
                        # 确保每个crawler都被清理
                        if hasattr(crawler, '_resource_manager'):
                            await crawler._resource_manager.cleanup_all()
                    except Exception as e:
                        self._logger.warning(f"Failed to cleanup crawler: {e}")
                
                # 清空crawlers列表，释放引用
                self._crawlers.clear()
                
                self._end_time = time.time()
                if self._start_time:
                    duration = self._end_time - self._start_time
                    self._logger.info(f"Total execution time: {duration:.2f}s")
    
    async def _run_with_semaphore(self, crawler: Crawler) -> Crawler:
        """
        在信号量控制下运行爬虫
        
        Args:
            crawler: 爬虫实例
            
        Returns:
            Crawler: 爬虫实例
        """
        async with self._semaphore:
            await crawler.crawl()
            return crawler
    
    def _resolve_spider_class(self, spider_cls_or_name: Union[Type['Spider'], str]) -> Type['Spider']:
        """
        解析Spider类
        
        Args:
            spider_cls_or_name: 爬虫类或名称
            
        Returns:
            Type[Spider]: 爬虫类
            
        Raises:
            ValueError: 无法解析爬虫类
        """
        from crawlo.utils.spider_resolver import SpiderResolver
        return SpiderResolver.resolve_spider_class(spider_cls_or_name, getattr(self, '_spider_modules', None))
    
    def _merge_settings(self, additional_settings: Optional[Dict[str, Any]]) -> Optional['SettingManager']:
        """
        合并配置
        
        Args:
            additional_settings: 额外配置字典
            
        Returns:
            Optional[SettingManager]: 合并后的配置管理器
        """
        from crawlo.utils.process_utils import SettingsUtils
        return SettingsUtils.merge_settings(self._settings, additional_settings)
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        获取整体指标
        
        Returns:
            Dict[str, Any]: 整体指标字典
        """
        total_duration = 0.0
        if self._start_time and self._end_time:
            total_duration = self._end_time - self._start_time
        
        crawler_metrics = [crawler.metrics for crawler in self._crawlers]
        
        return {
            'total_duration': total_duration,
            'crawler_count': len(self._crawlers),
            'total_requests': sum(m.request_count for m in crawler_metrics),
            'total_success': sum(m.success_count for m in crawler_metrics),
            'total_errors': sum(m.error_count for m in crawler_metrics),
            'average_success_rate': sum(m.get_success_rate() for m in crawler_metrics) / len(crawler_metrics) if crawler_metrics else 0.0
        }