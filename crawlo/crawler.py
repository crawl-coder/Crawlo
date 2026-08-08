#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Crawler System
==========

Core Components:
- Crawler: 单爬虫控制器
- CrawlerProcess: 多爬虫进程管理器
- CrawloFramework: Facade 门面类
- run_spider / run_spiders / create_crawler: 便捷函数

Design Principles:
1. Single Responsibility - Each class has one clear purpose
2. Dependency Injection - Components created via factories for testability
3. State Management - Clear state transitions and lifecycle
4. Error Handling - Graceful error handling and recovery mechanisms
5. Resource Management - Unified resource registration and cleanup
"""

import asyncio
import time
import os
import sys
import threading
from contextlib import asynccontextmanager
from typing import Optional, Type, Dict, Any, List, Union, TYPE_CHECKING, cast
from dataclasses import dataclass
from enum import Enum

from crawlo.core.factories import get_component_registry
from crawlo.logging import get_logger as _get_logger
from crawlo.logging import get_logger
from crawlo.core.errors import NotConfigured
from crawlo.event import CrawlerEvent
from crawlo.core.application import initialize_framework, is_framework_ready
from crawlo.settings.setting_manager import SettingManager
from crawlo.utils.resource_manager import ResourceManager, ResourceType
from crawlo.utils.concurrency import ProcessSignalHandler, SpiderDiscoveryUtils, SettingsUtils
from crawlo.spider import get_global_spider_registry, SpiderResolver

from .project import read_crawlo_cfg
from .settings.setting_manager import EnvConfigManager

__all__ = [
    'CrawlerState',
    'CrawlerMetrics',
    'Crawler',
    'CrawlerProcess',
    'CrawloFramework',
    'get_framework',
    'reset_framework',
    'run_spider',
    'run_spiders',
    'create_crawler',
    'configure_framework',
]


class CrawlerState(Enum):
    """Crawler state enumeration"""
    CREATED = "created"
    INITIALIZING = "initializing"
    READY = "ready"
    RUNNING = "running"
    CLOSING = "closing"
    CLOSED = "closed"
    ERROR = "error"


@dataclass
class CrawlerMetrics:
    """Crawler performance metrics"""
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    initialization_duration: float = 0.0
    crawl_duration: float = 0.0
    request_count: int = 0
    success_count: int = 0
    error_count: int = 0
    
    def get_total_duration(self) -> float:
        """Get total execution time
        
        Returns:
            float: Total execution time in seconds
        """
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0.0
    
    def get_success_rate(self) -> float:
        """Get success rate
        
        Returns:
            float: Success rate percentage
        """
        total = self.success_count + self.error_count
        return (self.success_count / total * 100) if total > 0 else 0.0

if TYPE_CHECKING:
    from crawlo.spider import Spider



class Crawler:
    """Core spider controller
        
    Features:
    1. Clear state management
    2. Dependency injection
    3. Component-based architecture
    4. Comprehensive error handling
    5. Unified resource management
    """
    
    def __init__(self, spider_cls: Type['Spider'], settings: Optional['SettingManager'] = None) -> None:
        """Initialize spider controller
                
        Args:
            spider_cls: Spider class
            settings: Configuration manager
        """
        self._spider_cls: Type['Spider'] = spider_cls
        self._settings: Optional['SettingManager'] = settings
        self._state: CrawlerState = CrawlerState.CREATED
        self._state_lock: asyncio.Lock = asyncio.Lock()
        
        # Components
        self._spider: Optional['Spider'] = None
        self._engine: Any = None
        self._stats: Any = None
        self._subscriber: Any = None
        self._extension: Any = None
        
        # Metrics
        self._metrics: CrawlerMetrics = CrawlerMetrics()
        
        # Resource manager
        self._resource_manager: ResourceManager = ResourceManager(name=f"crawler.{spider_cls.__name__ if spider_cls else 'unknown'}")

        # Ensure framework is initialized
        self._ensure_framework_ready()

        # Logging: Use global logger, do not create spider-specific log files
        # Reason: Separate log files cause log confusion and duplicate configuration in multi-spider scenarios
        # All spider logs are written to the global log file, distinguished by logger name
        self._logger = _get_logger(f'crawler.{spider_cls.__name__ if spider_cls else "unknown"}')
    
    def _ensure_framework_ready(self) -> None:
        """Ensure framework is ready"""
        if not is_framework_ready():
            try:
                self._settings = initialize_framework(self._settings)
                # At this point, the configured logger is a global logger
            except Exception as e:
                # Use fallback strategy
                if not self._settings:
                    self._settings = SettingManager()
            
        # Ensure it is a SettingManager instance
        if isinstance(self._settings, dict):
            settings_manager = SettingManager()
            settings_manager.update_attributes(self._settings)
            self._settings = settings_manager
        

    
    @property
    def state(self) -> CrawlerState:
        """Get current state
                
        Returns:
            CrawlerState: Current state
        """
        return self._state
    
    @property
    def spider(self) -> Optional['Spider']:
        """Get Spider instance
                
        Returns:
            Optional[Spider]: Spider instance
        """
        return self._spider
    
    @property
    def stats(self) -> Any:
        """Get Stats instance (backward compatibility)
                
        Returns:
            Any: Stats instance
        """
        return self._stats
    
    @property 
    def metrics(self) -> CrawlerMetrics:
        """Get performance metrics
                
        Returns:
            CrawlerMetrics: Performance metrics
        """
        return self._metrics
    
    @property
    def settings(self) -> Optional['SettingManager']:
        """Get configuration
                
        Returns:
            Optional[SettingManager]: Configuration manager
        """
        return self._settings
    
    @property
    def engine(self) -> Any:
        """Get Engine instance (backward compatibility)
                
        Returns:
            Any: Engine instance
        """
        return self._engine
    
    @property
    def subscriber(self) -> Any:
        """Get Subscriber instance (backward compatibility)
                
        Returns:
            Any: Subscriber instance
        """
        return self._subscriber
    
    @property
    def extension(self) -> Any:
        """Get Extension instance (backward compatibility)
                
        Returns:
            Any: Extension instance
        """
        return self._extension
    
    @extension.setter
    def extension(self, value: Any) -> None:
        """Set Extension instance (backward compatibility)
                
        Args:
            value: Extension instance
        """
        self._extension = value
    
    def _create_extension(self) -> Any:
        """Create Extension manager (backward compatibility)
                
        Returns:
            Any: Extension manager
        """
        if self._extension is None:
            try:
                registry = get_component_registry()
                self._extension = registry.create('extension_manager', crawler=self)
            except Exception as e:
                if isinstance(e, NotConfigured):
                    # For extensions that are not configured/enabled, log as info only, not error
                    self._logger.info(f"Extension manager not created (disabled): {e}")
                else:
                    self._logger.warning(f"Failed to create extension manager: {e}")
        return self._extension
    
    async def close(self) -> None:
        """Close spider (backward compatibility)"""
        await self._cleanup()
    
    async def crawl(self) -> None:
        """Execute crawl task"""
        self._logger.debug("Starting crawl task")
        try:
            async with self._lifecycle_manager():
                await self._initialize_components()
                await self._run_crawler()
        except asyncio.CancelledError:
            self._logger.info("Crawl task cancelled (Ctrl+C)")
            # Re-raise CancelledError so the caller can handle it properly
            raise
        except Exception as e:
            self._logger.error(f"Crawl task execution failed: {e}")
            raise
        finally:
            self._logger.info("Crawl task completed")
    
    @asynccontextmanager
    async def _lifecycle_manager(self):
        """Lifecycle management"""
        self._metrics.start_time = time.time()
        cleaned_up = False
        try:
            yield
        except asyncio.CancelledError:
            self._logger.info("Crawler task cancelled, starting resource cleanup...")
            cleaned_up = True
            await self._cleanup(reason='shutdown')
            raise
        except Exception as e:
            await self._handle_error(e)
            raise
        finally:
            if not cleaned_up:
                await self._cleanup()
            self._metrics.end_time = time.time()
    
    async def _initialize_components(self) -> None:
        """Initialize components"""
        async with self._state_lock:
            if self._state != CrawlerState.CREATED:
                raise RuntimeError(f"Cannot initialize from state {self._state}")
            
            self._state = CrawlerState.INITIALIZING
        
        init_start = time.time()
        
        try:
            # Create components using component factory
            registry = get_component_registry()
            
            # Create Subscriber (no dependencies)
            self._subscriber = registry.create('subscriber')
            
            # Create Spider
            self._spider = self._create_spider()
            
            # Create Engine (requires crawler parameter)
            self._engine = registry.create('engine', crawler=self)
            # Register Engine to resource manager
            if self._engine and hasattr(self._engine, 'close'):
                self._resource_manager.register(
                    self._engine,
                    lambda e: e.close() if hasattr(e, 'close') else None,
                    ResourceType.OTHER,
                    name="engine"
                )
            
            # Create Stats (requires crawler parameter)
            self._stats = registry.create('stats', crawler=self)
            
            # Create Extension Manager (using unified method to avoid code duplication)
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
        """Create Spider instance
                
        Returns:
            Spider: Spider instance
                    
        Raises:
            ValueError: If Spider class is invalid
        """
        if not self._spider_cls:
            raise ValueError("Spider class not provided")
        
        # Validate Spider class
        if not hasattr(self._spider_cls, 'name'):
            raise ValueError("Spider class must have 'name' attribute")
        
        # Create Spider instance
        spider = self._spider_cls()
        
        # Set crawler reference
        if hasattr(spider, 'crawler'):
            spider.crawler = self  # type: ignore
        
        return spider
    
    async def _run_crawler(self) -> None:
        """Run crawler engine"""
        async with self._state_lock:
            if self._state != CrawlerState.READY:
                raise RuntimeError(f"Cannot run from state {self._state}")
            
            self._state = CrawlerState.RUNNING
        
        crawl_start = time.time()
        
        try:
            # Start engine
            if self._engine:
                await self._engine.start_spider(self._spider)
            else:
                raise RuntimeError("Engine not initialized")
            
            self._metrics.crawl_duration = time.time() - crawl_start
            
            self._logger.debug(f"Crawler completed successfully in {self._metrics.crawl_duration:.2f}s")
            
        except asyncio.CancelledError:
            # Python 3.8: CancelledError 是 Exception 子类，在 3.9+ 是 BaseException
            # 显式守卫防止被包装为 RuntimeError 破坏取消传播链
            raise
        except Exception as e:
            self._metrics.crawl_duration = time.time() - crawl_start
            raise RuntimeError(f"Crawler execution failed: {e}")
    
    async def _handle_error(self, error: Exception) -> None:
        """Handle error
                
        Args:
            error: Exception object
        """
        async with self._state_lock:
            self._state = CrawlerState.ERROR
        
        self._metrics.error_count += 1
        self._logger.error(f"Crawler error: {error}", exc_info=True)
        
        # Error recovery logic can be added here
    
    async def _cleanup(self, reason: str = 'finished') -> None:
        """Clean up resources
        
        Args:
            reason: Shutdown reason, 'finished' or 'shutdown'
        """
        async with self._state_lock:
            if self._state not in [CrawlerState.CLOSING, CrawlerState.CLOSED]:
                self._state = CrawlerState.CLOSING
        
        try:
            # Clean up using resource manager
            self._logger.debug("Starting Crawler resource cleanup...")
            cleanup_result = await self._resource_manager.cleanup_all()
            self._logger.debug(
                f"Resource cleanup completed: {cleanup_result['success']} succeeded, "
                f"{cleanup_result['errors']} failed, duration {cleanup_result['duration']:.2f}s"
            )
            
            # Note: _cleanup_engine() is no longer called because Engine.close_spider()
            # is already called in the finally block of Engine.crawl().
            # Engine.close_spider() is now idempotent and safe to call multiple times.
            # If Engine was not started (initialization failed), _engine may be None or not running,
            # in which case close_spider will not be called, and no additional cleanup is needed.
            
            # Close Stats component (Stats is not registered to ResourceManager, needs explicit cleanup)
            await self._cleanup_stats(reason)
            
            # Trigger spider_closed event to notify all subscribers (including extensions)
            if self.subscriber:
                await self.subscriber.notify(CrawlerEvent.SPIDER_CLOSED, reason=reason)
            
            async with self._state_lock:
                self._state = CrawlerState.CLOSED
            
            self._logger.debug(f"Crawler cleanup completed (reason={reason})")
            
            # Explicitly close all log handlers to release file handles
            self._close_logger_handlers()
            
        except Exception as e:
            self._logger.error(f"Cleanup error: {e}")
            # Ensure handlers are cleaned up even if an error occurs
            try:
                self._close_logger_handlers()
            except Exception:
                pass
    
    async def _cleanup_engine(self, reason: str) -> None:
        """Clean up Engine resources"""
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
        """Clean up Stats resources"""
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
        """Explicitly close log handlers created by this crawler
        
        Note: Root logger handlers are no longer closed to avoid affecting other spiders and library logging output.
        """
        try:
            # Get all handlers from the current logger
            if self._logger:
                for handler in self._logger.handlers[:]:
                    try:
                        handler.close()
                        self._logger.removeHandler(handler)
                    except Exception:
                        pass  # Ignore errors when closing handlers
                # No longer close root logger handlers to avoid affecting other components
        except Exception:
            pass


if TYPE_CHECKING:
    from crawlo.spider import Spider
    from crawlo.settings.setting_manager import SettingManager


class CrawlerProcess:
    """
    Crawler进程管理器 - 管理多个Crawler的执行

    简化版本，专注于核心功能
    """

    def __init__(self, settings: Optional['SettingManager'] = None, max_spiders: int = None, spider_modules: Optional[List[str]] = None) -> None:
        """
        初始化爬虫进程管理器

        Args:
            settings: 配置管理器
            max_spiders: 同时运行的最大爬虫数（默认从 settings 的 MAX_RUNNING_SPIDERS 读取，未配置时为 3）
            spider_modules: 爬虫模块列表
        """
        # 初始化框架配置
        self._settings: Optional['SettingManager'] = settings or initialize_framework()

        # 从 settings 读取 MAX_RUNNING_SPIDERS，参数 max_spiders 可覆盖
        if max_spiders is not None:
            effective_max_spiders = max_spiders
        elif self._settings:
            effective_max_spiders = int(self._settings.get('MAX_RUNNING_SPIDERS', 3))
        else:
            effective_max_spiders = 3

        self._max_spiders: int = effective_max_spiders
        self._crawlers: List[Crawler] = []
        self._semaphore: asyncio.Semaphore = asyncio.Semaphore(effective_max_spiders)
        self._logger = get_logger('crawler.process')
        
        # 信号处理相关（必须在 _apply_windows_asyncio_fix 之前创建，
        # 因为 _apply_windows_asyncio_fix 在调度器环境中会访问 _signal_handler）
        # ProcessSignalHandler 已在顶部导入
        self._signal_handler = ProcessSignalHandler(self._logger, self._crawlers)
        self._shutdown_event: asyncio.Event = self._signal_handler.shutdown_event

        # Windows 平台: 在框架层面自动应用猴子补丁修复
        # 必须在 _logger 和 _signal_handler 初始化之后调用
        self._apply_windows_asyncio_fix()

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
        """设置信号处理器以优雅地处理关闭信号

        注意：在 Windows 上，信号处理器需要在事件循环启动后设置
        """
        self._signal_handler.set_crawlers(self._crawlers)
        # 延迟信号处理器设置到事件循环启动后

    @property
    def _shutdown_requested(self) -> bool:
        """实时读取信号处理器的状态，而非初始化时拷贝的值"""
        return self._signal_handler.shutdown_requested

    def _apply_windows_asyncio_fix(self) -> None:
        """
        在 Windows 平台自动应用 asyncio 传输关闭警告的修复。
        
        这个方法在 CrawlerProcess 初始化时调用，确保所有使用 CrawlerProcess
        的项目都能自动获得修复，无需用户手动导入和调用。
        """
        if sys.platform != 'win32':
            return
        
        try:
            import asyncio.proactor_events
            import warnings
            
            # 1. 猴子补丁 _ProactorBasePipeTransport.__del__
            _original_del = asyncio.proactor_events._ProactorBasePipeTransport.__del__

            def _patched_del(self):
                try:
                    _original_del(self)
                except (ValueError, OSError):
                    pass

            asyncio.proactor_events._ProactorBasePipeTransport.__del__ = _patched_del

            # 2. 同样修补 BaseSubprocessTransport
            try:
                import asyncio.base_subprocess
                _original_sub_del = asyncio.base_subprocess.BaseSubprocessTransport.__del__

                def _patched_sub_del(self):
                    try:
                        _original_sub_del(self)
                    except (ValueError, OSError):
                        pass

                asyncio.base_subprocess.BaseSubprocessTransport.__del__ = _patched_sub_del
            except Exception:
                pass

            # 3. 抑制 warnings 模块的 ResourceWarning
            warnings.filterwarnings('ignore', message='unclosed transport', category=ResourceWarning)
            
            self._logger.debug("已自动应用 Windows asyncio 传输关闭警告修复")
        except Exception as e:
            # 修复失败不应该影响正常运行
            self._logger.debug(f"应用 Windows asyncio 修复失败(可忽略): {e}")
        try:
            loop = asyncio.get_running_loop()
            # 如果事件循环已经在运行，直接设置
            if hasattr(self, '_signal_handler') and self._signal_handler is not None:
                self._signal_handler.setup_signal_handlers()
        except RuntimeError:
            # 事件循环尚未启动，将在 crawl() 方法中设置
            self._logger.debug("Event loop not running, signal handlers will be set up later")

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
        # SpiderDiscoveryUtils 已在顶部导入
        SpiderDiscoveryUtils.register_spider_modules(spider_modules, self._logger)

    def _auto_discover_spider_modules(self, spider_modules: List[str]) -> None:
        """
        自动发现并导入爬虫模块中的所有爬虫
        这个方法会扫描指定模块目录下的所有Python文件并自动导入

        Args:
            spider_modules: 爬虫模块列表
        """
        # SpiderDiscoveryUtils 已在顶部导入
        SpiderDiscoveryUtils.auto_discover_spider_modules(spider_modules, self._logger)

    def is_spider_registered(self, name: str) -> bool:
        """
        检查爬虫是否已注册

        Args:
            name: 爬虫名称

        Returns:
            bool: 是否已注册
        """
        # get_global_spider_registry 已在顶部导入
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
        # get_global_spider_registry 已在顶部导入
        registry = get_global_spider_registry()
        return registry.get(name)

    def get_spider_names(self) -> List[str]:
        """
        获取所有注册的爬虫名称

        Returns:
            List[str]: 爬虫名称列表
        """
        # get_global_spider_registry 已在顶部导入
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
        if sys.platform.lower().startswith('win'):
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

        # 确保信号处理器已设置（在事件循环启动后）
        self._signal_handler.setup_signal_handlers()

        result = None
        try:
            # 判断输入是单个还是多个爬虫
            if not isinstance(spider_cls_or_name, list):
                result = await self._crawl_single(spider_cls_or_name, settings)
            else:
                result = await self._crawl_multiple(spider_cls_or_name, settings)
            return result

        except KeyboardInterrupt:
            # 捕获 Ctrl+C (Windows/Linux 都支持)
            self._shutdown_event.set()
            # 执行优雅关闭
            await self._graceful_shutdown()
            # 重新抛出以便调用者知道是被中断的
            raise
        except asyncio.CancelledError:
            # 处理取消异常
            await self._graceful_shutdown()
            raise
        except Exception as e:
            self._logger.error(f"Error during crawl: {e}")
            await self._graceful_shutdown()
            raise
        finally:
            # 在事件循环关闭前，主动关闭所有残留的 transport
            # 这是解决 Windows ProactorEventLoop "unclosed transport" 警告的根本方案
            await self._shutdown_loop_transports()

    async def _crawl_single(self, spider_cls_or_name: Union[Type['Spider'], str], settings: Optional[Dict[str, Any]] = None) -> Crawler:
        """
        运行单个爬虫

        Args:
            spider_cls_or_name: 爬虫类或名称
            settings: 配置字典

        Returns:
            Crawler: 爬虫实例
        """
        spider_cls = self._resolve_spider_class(spider_cls_or_name)

        # 记录启动的爬虫名称
        self._logger.info(f"Starting spider: {spider_cls.name}")

        merged_settings = self._merge_settings(settings)
        crawler = Crawler(spider_cls, merged_settings)
        # 让 engine 可以访问 CrawlerProcess 的状态（如 shutdown_requested）
        crawler._process = self

        # 将 crawler 添加到信号处理器的列表中
        if crawler not in self._crawlers:
            self._crawlers.append(crawler)

        async with self._semaphore:
            # 创建爬虫任务
            crawl_task = asyncio.create_task(crawler.crawl())
            shutdown_wait_task = asyncio.create_task(self._shutdown_event.wait())

            try:
                # 等待爬虫完成或收到关闭信号
                done, pending = await asyncio.wait(
                    [crawl_task, shutdown_wait_task],
                    return_when=asyncio.FIRST_COMPLETED
                )

                # 如果收到关闭信号，取消爬虫任务
                if self._shutdown_event.is_set() and not crawl_task.done():
                    self._logger.info(f"Shutdown requested, cancelling spider: {spider_cls.name}")
                    crawl_task.cancel()
                    try:
                        await crawl_task
                    except asyncio.CancelledError:
                        self._logger.debug(f"Spider {spider_cls.name} cancelled successfully")

                # 检查爬虫任务是否异常（排除 CancelledError）
                if crawl_task.done() and not crawl_task.cancelled():
                    exc = crawl_task.exception()
                    if exc:
                        raise exc

            except asyncio.CancelledError:
                # 处理任务取消异常
                self._logger.debug(f"Crawl task was cancelled: {spider_cls.name}")
                raise
            finally:
                # 确保爬虫任务被清理
                if not crawl_task.done():
                    crawl_task.cancel()
                    try:
                        await crawl_task
                    except asyncio.CancelledError:
                        pass
                # 确保 shutdown 等待任务被清理，避免 "Task was destroyed but it is pending!"
                if not shutdown_wait_task.done():
                    shutdown_wait_task.cancel()
                    try:
                        await shutdown_wait_task
                    except asyncio.CancelledError:
                        pass

        # 执行优雅关闭流程（保存检查点、打印统计信息等）
        await self._graceful_shutdown()

        # 清理crawler资源，防止内存泄漏
        await self._cleanup_crawler(crawler, spider_cls.name)

        return crawler

    async def _crawl_multiple(self, spider_classes_or_names: List[Union[Type['Spider'], str]], settings: Optional[Dict[str, Any]] = None) -> List[Union[Crawler, BaseException]]:
        """
        运行多个爬虫

        Args:
            spider_classes_or_names: 爬虫类/名称列表
            settings: 配置字典

        Returns:
            List[Union[Crawler, BaseException]]: 爬虫实例列表
        """
        self._start_time = time.time()

        try:
            spider_classes = []
            for cls_or_name in spider_classes_or_names:
                spider_cls = self._resolve_spider_class(cls_or_name)
                spider_classes.append(spider_cls)

            # 记录启动的爬虫名称
            spider_names = [cls.name for cls in spider_classes]
            if len(spider_names) == 1:
                self._logger.info(f"Starting spider: {spider_names[0]}")
            else:
                self._logger.info(f"Starting spiders: {', '.join(spider_names)}")

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
            await self._cleanup_all_crawlers()

            self._end_time = time.time()
            if self._start_time:
                duration = self._end_time - self._start_time
                self._logger.info(f"Total execution time: {duration:.2f}s")

    async def _cleanup_crawler(self, crawler: Crawler, spider_name: str) -> None:
        """
        清理单个爬虫资源

        Args:
            crawler: 爬虫实例
            spider_name: 爬虫名称
        """
        await self._cleanup_single_crawler(crawler)
        self._logger.debug(f"Cleaned up crawler: {spider_name}")

    async def _cleanup_all_crawlers(self) -> None:
        """清理所有爬虫资源"""
        self._logger.debug(f"Cleaning up {len(self._crawlers)} crawler(s)...")
        for crawler in self._crawlers:
            await self._cleanup_single_crawler(crawler)

        # 清空crawlers列表，释放引用
        self._crawlers.clear()

    async def _cleanup_single_crawler(self, crawler: Crawler) -> None:
        """
        清理单个爬虫资源的内部方法

        Args:
            crawler: 爬虫实例
        """
        try:
            if hasattr(crawler, '_resource_manager'):
                await crawler._resource_manager.cleanup_all()
        except Exception as e:
            self._logger.warning(f"Failed to cleanup crawler: {e}")

    async def _shutdown_loop_transports(self) -> None:
        """
        在事件循环关闭前主动关闭残留的 transport。

        作为猴子补丁之外的额外防御，在循环还活着时尽量关闭已知 transport，
        减少 GC 时 __del__ 被调用的机会。猴子补丁（在 crawlo 包导入时自动应用）
        负责兜底拦截任何遗漏 transport 的析构错误。
        """
        if sys.platform != 'win32':
            return

        try:
            loop = asyncio.get_running_loop()

            # 关闭所有异步生成器
            await loop.shutdown_asyncgens()

            # 主动关闭 ProactorEventLoop 上注册的 transport
            transports = []
            if hasattr(loop, '_transports'):
                transports = list(loop._transports.values())
            if hasattr(loop, '_subprocesses'):
                transports.extend(list(loop._subprocesses.values()))

            closed_count = 0
            for transport in transports:
                try:
                    if hasattr(transport, 'is_closing') and not transport.is_closing():
                        transport.close()
                        closed_count += 1
                except Exception:
                    pass

            if closed_count:
                self._logger.debug(f"Proactively closed {closed_count} transport(s)")
                await asyncio.sleep(0.05)

        except Exception as e:
            self._logger.debug(f"Loop transport cleanup error (ignorable): {e}")

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
        # SpiderResolver 已在顶部导入
        return SpiderResolver.resolve_spider_class(spider_cls_or_name, getattr(self, '_spider_modules', None))

    def _merge_settings(self, additional_settings: Optional[Dict[str, Any]]) -> Optional['SettingManager']:
        """
        合并配置

        Args:
            additional_settings: 额外配置字典

        Returns:
            Optional[SettingManager]: 合并后的配置管理器
        """
        # SettingsUtils 已在顶部导入
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


class CrawloFramework:
    """
    Crawlo框架门面类
    
    提供统一的框架入口点，简化使用复杂度
    """

    def __init__(self, settings=None, **kwargs):
        """
        初始化框架
        
        Args:
            settings: 配置对象
            **kwargs: 额外配置参数
        """
        # 合并配置
        config = {}
        if settings:
            if hasattr(settings, '__dict__'):
                config.update(settings.__dict__)
            elif isinstance(settings, dict):
                config.update(settings)
        config.update(kwargs)

        # 修复：先初始化 logger，确保 _load_project_config 可用 self._logger
        self._logger = get_logger('crawlo.framework')

        # 如果没有提供配置，尝试自动加载项目配置
        if not config:
            config = self._load_project_config()

        # 初始化框架
        self._settings = initialize_framework(config)

        # 获取版本号
        version = EnvConfigManager.get_version()

        # 创建进程管理器
        self._process = CrawlerProcess(self._settings)

        self._logger.info(f"Crawlo Framework Started {version}")
        
        # 获取运行模式和队列类型并记录日志
        run_mode = self._settings.get('RUN_MODE', 'unknown')
        queue_type = self._settings.get('QUEUE_TYPE', 'unknown')
        self._logger.info(f"RunMode: {run_mode}, QueueType: {queue_type}")
        
        # 记录项目名称
        project_name = self._settings.get('PROJECT_NAME', 'unknown')
        self._logger.info(f"Project: {project_name}")

    def _load_project_config(self):
        """
        自动加载项目配置
        """
        try:
            # 查找项目根目录
            project_root = self._find_project_root()
            if not project_root:
                # 修复：print 改为 logger（此时 _logger 已初始化）
                self._logger.warning("未找到项目根目录，使用默认配置")
                return {}

            # 添加项目根目录到Python路径
            if project_root not in sys.path:
                sys.path.insert(0, project_root)

            # 读取crawlo.cfg配置文件
            cfg_file = os.path.join(project_root, "crawlo.cfg")
            settings_module_path = read_crawlo_cfg(cfg_file)

            if not settings_module_path:
                self._logger.warning(f"配置文件 {cfg_file} 无效或不存在，使用默认配置")
                return {}
            
            project_package = settings_module_path.split(".")[0]
            
            # 导入项目配置模块
            import importlib
            settings_module = importlib.import_module(settings_module_path)
            
            # 创建配置字典
            project_config = {}
            for key in dir(settings_module):
                if key.isupper():
                    project_config[key] = getattr(settings_module, key)
            
            # print(f"已加载项目配置: {settings_module_path}")
            return project_config
            
        except Exception as e:
            self._logger.error(f"Error loading project configuration: {e}")
            return {}

    def _find_project_root(self):
        """
        查找项目根目录（包含crawlo.cfg的目录）
        """
        current_path = os.getcwd()
        
        # 向上查找直到找到crawlo.cfg
        checked_paths = set()
        path = current_path
        
        while path not in checked_paths:
            checked_paths.add(path)
            
            # 检查crawlo.cfg
            cfg_file = os.path.join(path, "crawlo.cfg")
            if os.path.exists(cfg_file):
                return path
            
            # 向上一级目录
            parent = os.path.dirname(path)
            if parent == path:
                break
            path = parent
        
        return None

    @property
    def settings(self):
        """获取配置"""
        return self._settings

    @property
    def logger(self):
        """获取框架日志器"""
        return self._logger

    async def run(self, spider_cls_or_name, settings=None):
        """
        运行单个爬虫
        
        Args:
            spider_cls_or_name: Spider类或名称
            settings: 额外配置
            
        Returns:
            Crawler实例
        """
        # 记录启动的爬虫名称
        if isinstance(spider_cls_or_name, str):
            spider_name = spider_cls_or_name
        else:
            spider_name = getattr(spider_cls_or_name, 'name', spider_cls_or_name.__name__)
        
        self._logger.info(f"Starting spider: {spider_name}")
        
        return await self._process.crawl(spider_cls_or_name, settings)

    async def run_multiple(self, spider_classes_or_names: List[Union[Type, str]],
                           settings=None):
        """
        运行多个爬虫
        
        Args:
            spider_classes_or_names: Spider类或名称列表
            settings: 额外配置
            
        Returns:
            结果列表
        """
        # 记录启动的爬虫名称
        spider_names = []
        for spider_cls_or_name in spider_classes_or_names:
            if isinstance(spider_cls_or_name, str):
                spider_names.append(spider_cls_or_name)
            else:
                spider_names.append(getattr(spider_cls_or_name, 'name', spider_cls_or_name.__name__))
        
        self._logger.info(f"Starting spiders: {', '.join(spider_names)}")
        
        try:
            return await self._process.crawl(spider_classes_or_names, settings)
        finally:
            # 清理全局Redis连接池
            await self._cleanup_global_resources()

    def create_crawler(self, spider_cls: Type, settings=None) -> Crawler:
        """
        创建Crawler实例
        
        Args:
            spider_cls: Spider类
            settings: 额外配置
            
        Returns:
            Crawler实例
        """
        merged_settings = self._merge_settings(settings)
        return Crawler(spider_cls, merged_settings)

    def _merge_settings(self, additional_settings):
        """合并配置"""
        if not additional_settings:
            return self._settings

        from .settings.setting_manager import SettingManager
        merged = SettingManager()

        # 复制基础配置
        if self._settings:
            merged.update_attributes(self._settings.__dict__)

        # 应用额外配置
        if isinstance(additional_settings, dict):
            merged.update_attributes(additional_settings)
        elif hasattr(additional_settings, '__dict__'):
            merged.update_attributes(additional_settings.__dict__)

        return merged

    def get_metrics(self) -> dict:
        """获取框架指标"""
        return self._process.get_metrics()
    
    async def _cleanup_global_resources(self):
        """清理全局资源（Redis连接池等）"""
        try:
            # 清理全局Redis连接池
            from crawlo.utils.redis import close_all_pools
            await close_all_pools()
            self._logger.debug("Global resources cleaned up")
        except Exception as e:
            self._logger.warning(f"Failed to cleanup global resources: {e}")


_framework_lock = threading.Lock()


def get_framework(settings=None, **kwargs) -> CrawloFramework:
    """
    获取全局框架实例（存储于 ApplicationContext，DCL 线程安全）

    Args:
        settings: 配置对象
        **kwargs: 额外配置参数

    Returns:
        CrawloFramework 实例
    """
    try:
        from crawlo.core.application import default_container
        if default_container.is_registered(CrawloFramework):
            return default_container.resolve(CrawloFramework)
    except Exception:  # pragma: no cover
        pass
    # Fallback：RegistryContext.framework（ApplicationContext 通过委托同步）
    reg_ctx = _resolve_registry_context()
    if reg_ctx.framework is None:
        with _framework_lock:
            # DCL 二次检查
            if reg_ctx.framework is None:
                inst = CrawloFramework(settings, **kwargs)
                reg_ctx.framework = inst
                try:
                    from crawlo.core.application import default_container as _c
                    _c.register_instance(CrawloFramework, inst)
                except Exception:  # pragma: no cover
                    pass
    return reg_ctx.framework


def _resolve_registry_context():
    """Phase 8 Step 8.5：优先从容器拿 RegistryContext，否则 fallback ctx.registries。"""
    try:
        from crawlo.core.application import default_container
        from crawlo.core.application import RegistryContext
        if default_container.is_registered(RegistryContext):
            return default_container.resolve(RegistryContext)
    except Exception:  # noqa: S110
        pass
    from crawlo.core.application import get_global_context
    return get_global_context().registries


def reset_framework():
    """重置全局框架实例（Phase 8 Step 8.5：通过 RegistryContext.framework 写位）。

    同时清除 DI 容器中的注册和 CoreInitializer 的初始化状态，
    避免 reset 后 get_framework 仍返回旧实例或使用旧 settings。
    """
    reg_ctx = _resolve_registry_context()
    reg_ctx.framework = None
    # 清除容器中的注册，确保下次 get_framework 创建新实例
    try:
        from crawlo.core.application import default_container
        default_container._registrations.pop(CrawloFramework, None)
    except Exception:  # pragma: no cover
        pass
    # 重置 CoreInitializer 单例状态，确保下次 initialize_framework 使用新 settings
    try:
        from crawlo.core.application import CoreInitializer
        CoreInitializer().reset()
    except Exception:  # pragma: no cover
        pass


# 便捷函数
async def run_spider(spider_cls_or_name, settings=None, **kwargs):
    """运行单个爬虫的便捷函数"""
    framework = get_framework(settings, **kwargs)
    return await framework.run(spider_cls_or_name)


async def run_spiders(spider_classes_or_names: List[Union[Type, str]],
                      settings=None, **kwargs):
    """运行多个爬虫的便捷函数"""
    framework = get_framework(settings, **kwargs)
    return await framework.run_multiple(spider_classes_or_names)


def create_crawler(spider_cls: Type, settings=None, **kwargs) -> Crawler:
    """创建Crawler的便捷函数"""
    framework = get_framework(settings, **kwargs)
    return framework.create_crawler(spider_cls)


# 配置相关便捷函数
def configure_framework(settings=None, **kwargs):
    """配置框架的便捷函数"""
    if settings or kwargs:
        reset_framework()  # 重置以应用新配置
    return get_framework(settings, **kwargs)

