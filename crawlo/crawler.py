#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Crawler System
==========

Core Components:
- Crawler: Core controller for individual spider lifecycle management
- CrawlerProcess: Process manager supporting single/multiple spider execution

Design Principles:
1. Single Responsibility - Each class has one clear purpose
2. Dependency Injection - Components created via factories for testability
3. State Management - Clear state transitions and lifecycle
4. Error Handling - Graceful error handling and recovery mechanisms
5. Resource Management - Unified resource registration and cleanup
"""

import asyncio
import time
from contextlib import asynccontextmanager
from typing import Optional, Type, Dict, Any, List, Union, TYPE_CHECKING, cast

from crawlo.factories import get_component_registry
from crawlo.initialization import initialize_framework, is_framework_ready
from dataclasses import dataclass
from enum import Enum
from crawlo.logging import get_logger
from crawlo.utils.resource_manager import ResourceManager, ResourceType
from crawlo.settings.setting_manager import SettingManager


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
        self._logger = get_logger(f'crawler.{spider_cls.__name__ if spider_cls else "unknown"}')
    
    def _ensure_framework_ready(self) -> None:
        """Ensure framework is ready"""
        if not is_framework_ready():
            try:
                self._settings = initialize_framework(self._settings)
                # At this point, the configured logger is a global logger
            except Exception as e:
                # Use fallback strategy
                if not self._settings:
                    # SettingManager 已在顶部导入
                    self._settings = SettingManager()
            
        # Ensure it is a SettingManager instance
        if isinstance(self._settings, dict):
            # SettingManager 已在顶部导入
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
                from crawlo.exceptions import NotConfigured
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
                from crawlo.event import CrawlerEvent
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


# Backward compatibility: CrawlerProcess moved to a separate module
from crawlo.crawler_process import CrawlerProcess  # noqa: F401, E402
