#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
重构后的Crawler系统
==================

设计原则：
1. 单一职责 - 每个类只负责一个明确的功能
2. 依赖注入 - 通过工厂创建组件，便于测试
3. 状态管理 - 清晰的状态转换和生命周期
4. 错误处理 - 优雅的错误处理和恢复机制
"""

import asyncio
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Type, Dict, Any, List

from crawlo.factories import get_component_registry
from crawlo.initialization import initialize_framework, is_framework_ready
from crawlo.logging import get_logger


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
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0.0
    
    def get_success_rate(self) -> float:
        total = self.success_count + self.error_count
        return (self.success_count / total * 100) if total > 0 else 0.0


class ModernCrawler:
    """
    现代化的Crawler实现
    
    特点：
    1. 清晰的状态管理
    2. 依赖注入
    3. 组件化架构
    4. 完善的错误处理
    """
    
    def __init__(self, spider_cls: Type, settings=None):
        self._spider_cls = spider_cls
        self._settings = settings
        self._state = CrawlerState.CREATED
        self._state_lock = asyncio.Lock()
        
        # 组件
        self._spider = None
        self._engine = None
        self._stats = None
        self._subscriber = None
        self._extension = None
        
        # 指标
        self._metrics = CrawlerMetrics()
        
        # 日志
        self._logger = get_logger(f'crawler.{spider_cls.__name__ if spider_cls else "unknown"}')
        
        # 确保框架已初始化
        self._ensure_framework_ready()
    
    def _ensure_framework_ready(self):
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
        """获取当前状态"""
        return self._state
    
    @property
    def spider(self):
        """获取Spider实例"""
        return self._spider
    
    @property
    def stats(self):
        """获取Stats实例（向后兼容）"""
        return self._stats
    
    @property 
    def metrics(self) -> CrawlerMetrics:
        """获取性能指标"""
        return self._metrics
    
    @property
    def settings(self):
        """获取配置"""
        return self._settings
    
    @property
    def engine(self):
        """获取Engine实例（向后兼容）"""
        return self._engine
    
    @property
    def subscriber(self):
        """获取Subscriber实例（向后兼容）"""
        return self._subscriber
    
    @property
    def extension(self):
        """获取Extension实例（向后兼容）"""
        return self._extension
    
    @extension.setter
    def extension(self, value):
        """设置Extension实例（向后兼容）"""
        self._extension = value
    
    def _create_extension(self):
        """创建Extension管理器（向后兼容）"""
        if self._extension is None:
            try:
                registry = get_component_registry()
                self._extension = registry.create('extension_manager', crawler=self)
            except Exception as e:
                self._logger.warning(f"Failed to create extension manager: {e}")
        return self._extension
    
    async def close(self):
        """关闭爹虫（向后兼容）"""
        await self._cleanup()
    
    async def crawl(self):
        """执行爬取任务"""
        async with self._lifecycle_manager():
            await self._initialize_components()
            await self._run_crawler()
    
    @asynccontextmanager
    async def _lifecycle_manager(self):
        """生命周期管理"""
        self._metrics.start_time = time.time()
        
        try:
            yield
        except Exception as e:
            await self._handle_error(e)
            raise
        finally:
            await self._cleanup()
            self._metrics.end_time = time.time()
    
    async def _initialize_components(self):
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
            
            # 创建Stats（需要crawler参数）
            self._stats = registry.create('stats', crawler=self)
            
            # 创建Extension Manager (可选，需要crawler参数)
            try:
                self._extension = registry.create('extension_manager', crawler=self)
            except Exception as e:
                self._logger.warning(f"Failed to create extension manager: {e}")
            
            self._metrics.initialization_duration = time.time() - init_start
            
            async with self._state_lock:
                self._state = CrawlerState.READY
            
            self._logger.debug(f"Crawler components initialized successfully in {self._metrics.initialization_duration:.2f}s")
            
        except Exception as e:
            async with self._state_lock:
                self._state = CrawlerState.ERROR
            raise RuntimeError(f"Component initialization failed: {e}")
    
    def _create_spider(self):
        """创建Spider实例"""
        if not self._spider_cls:
            raise ValueError("Spider class not provided")
        
        # 检查Spider类的有效性
        if not hasattr(self._spider_cls, 'name'):
            raise ValueError("Spider class must have 'name' attribute")
        
        # 创建Spider实例
        spider = self._spider_cls()
        
        # 设置crawler引用
        if hasattr(spider, 'crawler'):
            spider.crawler = self
        
        return spider
    
    async def _run_crawler(self):
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
            
            self._logger.info(f"Crawler completed successfully in {self._metrics.crawl_duration:.2f}s")
            
        except Exception as e:
            self._metrics.crawl_duration = time.time() - crawl_start
            raise RuntimeError(f"Crawler execution failed: {e}")
    
    async def _handle_error(self, error: Exception):
        """处理错误"""
        async with self._state_lock:
            self._state = CrawlerState.ERROR
        
        self._metrics.error_count += 1
        self._logger.error(f"Crawler error: {error}", exc_info=True)
        
        # 这里可以添加错误恢复逻辑
    
    async def _cleanup(self):
        """清理资源"""
        async with self._state_lock:
            if self._state not in [CrawlerState.CLOSING, CrawlerState.CLOSED]:
                self._state = CrawlerState.CLOSING
        
        try:
            # 关闭各个组件
            if self._engine and hasattr(self._engine, 'close'):
                try:
                    await self._engine.close()
                except Exception as e:
                    self._logger.warning(f"Engine cleanup failed: {e}")
            
            if self._stats and hasattr(self._stats, 'close'):
                try:
                    await self._stats.close()
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
    
    def __init__(self, settings=None, max_concurrency: int = 3):
        self._settings = settings or initialize_framework()
        self._max_concurrency = max_concurrency
        self._crawlers: List[ModernCrawler] = []
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._logger = get_logger('crawler.process')
        
        # 指标
        self._start_time: Optional[float] = None
        self._end_time: Optional[float] = None
    
    async def crawl(self, spider_cls_or_name, settings=None):
        """运行单个爬虫"""
        spider_cls = self._resolve_spider_class(spider_cls_or_name)
        
        merged_settings = self._merge_settings(settings)
        crawler = ModernCrawler(spider_cls, merged_settings)
        
        async with self._semaphore:
            await crawler.crawl()
        
        return crawler
    
    async def crawl_multiple(self, spider_classes_or_names, settings=None):
        """运行多个爬虫"""
        self._start_time = time.time()
        
        try:
            spider_classes = [
                self._resolve_spider_class(cls_or_name) 
                for cls_or_name in spider_classes_or_names
            ]
            
            tasks = []
            for spider_cls in spider_classes:
                merged_settings = self._merge_settings(settings)
                crawler = ModernCrawler(spider_cls, merged_settings)
                self._crawlers.append(crawler)
                
                task = asyncio.create_task(self._run_with_semaphore(crawler))
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 处理结果
            successful = sum(1 for r in results if not isinstance(r, Exception))
            failed = len(results) - successful
            
            self._logger.info(f"Crawl completed: {successful} successful, {failed} failed")
            
            return results
            
        finally:
            self._end_time = time.time()
            if self._start_time:
                duration = self._end_time - self._start_time
                self._logger.info(f"Total execution time: {duration:.2f}s")
    
    async def _run_with_semaphore(self, crawler: ModernCrawler):
        """在信号量控制下运行爬虫"""
        async with self._semaphore:
            await crawler.crawl()
            return crawler
    
    def _resolve_spider_class(self, spider_cls_or_name):
        """解析Spider类"""
        if isinstance(spider_cls_or_name, str):
            # 从注册表中查找
            try:
                from crawlo.spider import get_global_spider_registry
                registry = get_global_spider_registry()
                if spider_cls_or_name in registry:
                    return registry[spider_cls_or_name]
                else:
                    raise ValueError(f"Spider '{spider_cls_or_name}' not found in registry")
            except ImportError:
                raise ValueError(f"Cannot resolve spider name '{spider_cls_or_name}'")
        else:
            return spider_cls_or_name
    
    def _merge_settings(self, additional_settings):
        """合并配置"""
        if not additional_settings:
            return self._settings
        
        # 这里可以实现更复杂的配置合并逻辑
        from crawlo.settings.setting_manager import SettingManager
        merged = SettingManager()
        
        # 复制基础配置
        if self._settings:
            merged.update_attributes(self._settings.__dict__)
        
        # 应用额外配置
        merged.update_attributes(additional_settings)
        
        return merged
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取整体指标"""
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