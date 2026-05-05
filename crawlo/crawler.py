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
import sys
import time
from contextlib import asynccontextmanager
from typing import Optional, Type, Dict, Any, List, Union, TYPE_CHECKING, cast

from crawlo.factories import get_component_registry
from crawlo.initialization import initialize_framework, is_framework_ready
from dataclasses import dataclass
from enum import Enum
from crawlo.logging import get_logger
from crawlo.utils.resource_manager import ResourceManager, ResourceType


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

if TYPE_CHECKING:
    from crawlo.spider import Spider
    from crawlo.settings.setting_manager import SettingManager



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
        
        # 确保框架已初始化
        self._ensure_framework_ready()
        
        # 日志：使用全局日志，不创建爬虫独立日志文件
        # 原因：独立日志会导致多爬虫场景下日志混乱和重复配置问题
        # 所有爬虫日志统一写入全局日志文件，通过 logger 名称区分
        self._logger = get_logger(f'crawler.{spider_cls.__name__ if spider_cls else "unknown"}')
    
    def _ensure_framework_ready(self) -> None:
        """确保框架已准备就绪"""
        if not is_framework_ready():
            try:
                self._settings = initialize_framework(self._settings)
                # 此时配置公用日志是一个普逐日志
            except Exception as e:
                # 使用降级策略
                if not self._settings:
                    from crawlo.settings.setting_manager import SettingManager
                    self._settings = SettingManager()
            
        # 确保是 SettingManager 实例
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
            self._logger.info("爬取任务被取消（Ctrl+C）")
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
            await self._cleanup(reason='shutdown')
            raise
        except Exception as e:
            await self._handle_error(e)
            raise
        finally:
            # 只有在非 CancelledError 的情况下才清理（CancelledError 已在 except 中清理）
            if not isinstance(sys.exc_info()[1], asyncio.CancelledError):
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
            
            # 创建Extension Manager（使用统一方法，避免代码重复）
            self._create_extension()
            
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
    
    async def _cleanup(self, reason: str = 'finished') -> None:
        """清理资源
        
        Args:
            reason: 关闭原因，'finished' 或 'shutdown'
        """
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
            
            # 注意：不再调用 _cleanup_engine()，因为 Engine.close_spider()
            # 已在 Engine.crawl() 的 finally 块中被调用。
            # Engine.close_spider() 现在是幂等的，即使被多次调用也安全。
            # 如果 Engine 未启动（初始化失败），_engine 可能为 None 或未运行，
            # 此时 close_spider 也不会被调用，无需额外清理。
            
            # 关闭Stats组件（Stats未注册到ResourceManager，需要显式清理）
            await self._cleanup_stats(reason)
            
            # 触发spider_closed事件，通知所有订阅者（包括扩展）
            if self.subscriber:
                from crawlo.event import CrawlerEvent
                await self.subscriber.notify(CrawlerEvent.SPIDER_CLOSED, reason=reason)
            
            async with self._state_lock:
                self._state = CrawlerState.CLOSED
            
            self._logger.debug(f"Crawler cleanup completed (reason={reason})")
            
            # 显式关闭所有日志handlers，释放文件句柄
            self._close_logger_handlers()
            
        except Exception as e:
            self._logger.error(f"Cleanup error: {e}")
            # 即使发生错误也要清理handlers
            try:
                self._close_logger_handlers()
            except Exception:
                pass
    
    async def _cleanup_engine(self, reason: str) -> None:
        """清理Engine资源"""
        if not self._engine:
            return
            
        if hasattr(self._engine, 'close'):
            try:
                await self._engine.close()
            except Exception as e:
                self._logger.warning(f"Engine cleanup failed: {e}")
        
        if hasattr(self._engine, 'close_spider'):
            try:
                await self._engine.close_spider(reason=reason)
            except Exception as e:
                self._logger.warning(f"Engine close_spider failed: {e}")
    
    async def _cleanup_stats(self, reason: str) -> None:
        """清理Stats资源"""
        if not self._stats:
            return
            
        if hasattr(self._stats, 'close_spider'):
            try:
                self._stats.close_spider(self._spider, reason=reason)
            except Exception as e:
                self._logger.warning(f"Stats close_spider failed: {e}")
        
        if hasattr(self._stats, 'close'):
            try:
                close_result = self._stats.close()
                if asyncio.iscoroutine(close_result):
                    await close_result
            except Exception as e:
                self._logger.warning(f"Stats cleanup failed: {e}")
    
    def _close_logger_handlers(self) -> None:
        """
        显式关闭当前 crawler 自己创建的日志 handlers
        
        注意：不再关闭根 logger 的 handlers，避免影响其他爬虫和库的日志输出。
        """
        try:
            # 获取当前logger的所有handlers
            if self._logger:
                for handler in self._logger.handlers[:]:
                    try:
                        handler.close()
                        self._logger.removeHandler(handler)
                    except Exception:
                        pass  # 忽略关闭handler时的错误
                # 不再关闭根 logger 的 handlers，防止影响其他组件
        except Exception:
            pass


# 向后兼容：CrawlerProcess 已移至独立模块
from crawlo.crawler_process import CrawlerProcess  # noqa: F401, E402
