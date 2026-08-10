#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Crawler 单爬虫控制器子模块。

包含：
- CrawlerState (Enum)：状态枚举
- CrawlerMetrics (dataclass)：性能指标容器
- Crawler：单爬虫控制器（组件初始化 / 生命周期 / 清理）
"""
from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any, Optional, Type

from crawlo.core.factories import get_component_registry
from crawlo.core.errors import NotConfigured
from crawlo.event import CrawlerEvent
from crawlo.core.application import initialize_framework, is_framework_ready
from crawlo.settings.setting_manager import SettingManager
from crawlo.utils.resource_manager import ResourceManager, ResourceType
from crawlo.logging import get_logger
from crawlo.spider import get_global_spider_registry  # noqa: F401 (re-used by callers)

if TYPE_CHECKING:
    from crawlo.spider import Spider


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
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0.0

    def get_success_rate(self) -> float:
        total = self.success_count + self.error_count
        return (self.success_count / total * 100) if total > 0 else 0.0


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
        self._resource_manager: ResourceManager = ResourceManager(
            name=f"crawler.{spider_cls.__name__ if spider_cls else 'unknown'}"
        )

        # Ensure framework is initialized
        self._ensure_framework_ready()

        self._logger = get_logger(f'crawler.{spider_cls.__name__ if spider_cls else "unknown"}')

    def _ensure_framework_ready(self) -> None:
        """Ensure framework is ready"""
        if not is_framework_ready():
            try:
                self._settings = initialize_framework(self._settings)
            except Exception:
                if not self._settings:
                    self._settings = SettingManager()

        if isinstance(self._settings, dict):
            settings_manager = SettingManager()
            settings_manager.update_attributes(self._settings)
            self._settings = settings_manager

    @property
    def state(self) -> CrawlerState:
        return self._state

    @property
    def spider(self) -> Optional['Spider']:
        return self._spider

    @property
    def stats(self) -> Any:
        return self._stats

    @property
    def metrics(self) -> CrawlerMetrics:
        # 兼容：在 close() 末尾的破环阶段 _metrics 会被置 None，这时仍
        # 需要对外（CrawlerProcess.get_metrics / 监控等）返回一个空 metrics
        # 对象，避免 AttributeError: 'NoneType' has no attribute 'error_count'
        return self._metrics or CrawlerMetrics()

    @property
    def settings(self) -> Optional['SettingManager']:
        return self._settings

    @property
    def engine(self) -> Any:
        return self._engine

    @property
    def subscriber(self) -> Any:
        return self._subscriber

    @property
    def extension(self) -> Any:
        return self._extension

    @extension.setter
    def extension(self, value: Any) -> None:
        self._extension = value

    def _create_extension(self) -> Any:
        """Create Extension manager (backward compatibility)"""
        if self._extension is None:
            try:
                registry = get_component_registry()
                self._extension = registry.create('extension_manager', crawler=self)
            except Exception as e:
                if isinstance(e, NotConfigured):
                    self._logger.info(f"Extension manager not created (disabled): {e}")
                else:
                    self._logger.warning(f"Failed to create extension manager: {e}")
        return self._extension

    async def close(self) -> None:
        await self._cleanup()

    async def crawl(self) -> None:
        logger = self._logger
        logger.debug("Starting crawl task")
        try:
            async with self._lifecycle_manager():
                await self._initialize_components()
                await self._run_crawler()
        except asyncio.CancelledError:
            logger.info("Crawl task cancelled (Ctrl+C)")
            raise
        except Exception as e:
            logger.error(f"Crawl task execution failed: {e}")
            raise
        finally:
            logger.info("Crawl task completed")

    @asynccontextmanager
    async def _lifecycle_manager(self):
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
            # 先在 cleanup 前写 end_time（确保 metrics 此时仍可用；cleanup 内部会幂等
            # 保留已有 end_time，不会覆盖），再 cleanup 破引用环，二次 close 不做事
            if self._metrics is not None:
                self._metrics.end_time = time.time()
            if not cleaned_up:
                await self._cleanup()

    async def _initialize_components(self) -> None:
        """Initialize components"""
        async with self._state_lock:
            if self._state != CrawlerState.CREATED:
                raise RuntimeError(f"Cannot initialize from state {self._state}")
            self._state = CrawlerState.INITIALIZING

        init_start = time.time()

        try:
            registry = get_component_registry()

            self._subscriber = registry.create('subscriber')
            self._spider = self._create_spider()

            self._engine = registry.create('engine', crawler=self)
            if self._engine and hasattr(self._engine, 'close'):
                self._resource_manager.register(
                    self._engine,
                    lambda e: e.close() if hasattr(e, 'close') else None,
                    ResourceType.OTHER,
                    name="engine"
                )

            self._stats = registry.create('stats', crawler=self)
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
        if not self._spider_cls:
            raise ValueError("Spider class not provided")
        if not hasattr(self._spider_cls, 'name'):
            raise ValueError("Spider class must have 'name' attribute")
        spider = self._spider_cls()
        if hasattr(spider, 'crawler'):
            spider.crawler = self  # type: ignore
        return spider

    async def _run_crawler(self) -> None:
        async with self._state_lock:
            if self._state != CrawlerState.READY:
                raise RuntimeError(f"Cannot run from state {self._state}")
            self._state = CrawlerState.RUNNING

        crawl_start = time.time()
        try:
            if self._engine:
                await self._engine.start_spider(self._spider)
            else:
                raise RuntimeError("Engine not initialized")

            self._metrics.crawl_duration = time.time() - crawl_start
            self._logger.debug(f"Crawler completed successfully in {self._metrics.crawl_duration:.2f}s")
        except asyncio.CancelledError:
            raise
        except Exception as e:
            self._metrics.crawl_duration = time.time() - crawl_start
            raise RuntimeError(f"Crawler execution failed: {e}")

    async def _handle_error(self, error: Exception) -> None:
        async with self._state_lock:
            self._state = CrawlerState.ERROR
        self._metrics.error_count += 1
        self._logger.error(f"Crawler error: {error}", exc_info=True)

    async def _cleanup(self, reason: str = 'finished') -> None:
        async with self._state_lock:
            if self._state == CrawlerState.CLOSED:
                return  # 幂等：避免 CrawlerProcess 兜底清理时二次执行（字段已置None）
            if self._state not in [CrawlerState.CLOSING, CrawlerState.CLOSED]:
                self._state = CrawlerState.CLOSING

        try:
            self._logger.debug("Starting Crawler resource cleanup...")
            cleanup_result = await self._resource_manager.cleanup_all()
            self._logger.debug(
                f"Resource cleanup completed: {cleanup_result['success']} succeeded, "
                f"{cleanup_result['errors']} failed, duration {cleanup_result['duration']:.2f}s"
            )

            await self._cleanup_stats(reason)

            if self.subscriber:
                await self.subscriber.notify(CrawlerEvent.SPIDER_CLOSED, reason=reason)

            # 先记录 end_time（metrics 仍可用），再进入 CLOSED + 破环
            if self._metrics is not None:
                self._metrics.end_time = self._metrics.end_time or time.time()

            async with self._state_lock:
                self._state = CrawlerState.CLOSED

            self._logger.debug(f"Crawler cleanup completed (reason={reason})")

            self._close_logger_handlers()

            # 破引用环：防止 Crawler↔Engine↔Pipeline↔Spider↔Stats 等环形引用导致
            # CPython 循环垃圾回收无法释放（尤其是协程 frame / cell / closure function
            # 参与构成的环）。先清引擎再清顶层字段。
            try:
                # 注意：此处为异步方法，同步代码无需 await
                self._cleanup_engine_sync(reason)
            except Exception as e:
                get_logger(__name__).debug("Suppressed exception: %s", e)
            self._spider = None
            self._engine = None
            self._stats = None
            self._subscriber = None
            self._extension = None
            # metrics: 保留 end_time 但断开引用
            self._metrics = None
            # ResourceManager 在 cleanup_all 后清空内部表防止 dict 引用链
            rm = getattr(self, '_resource_manager', None)
            if rm is not None and hasattr(rm, 'clear'):
                try:
                    rm.clear()
                except Exception as e:
                    get_logger(__name__).debug("Suppressed exception: %s", e)
            self._resource_manager = None  # type: ignore[assignment]
            self._settings = None
            # logger 最后再清，确保上面日志都可用
            self._logger = None  # type: ignore[assignment]

        except Exception as e:
            # 破环失败不应阻塞 close 流程
            safe_log = getattr(self, '_logger', None)
            try:
                if safe_log is not None:
                    safe_log.error(f"Cleanup error: {e}")
            except Exception as e:
                get_logger(__name__).debug("Suppressed exception: %s", e)
            try:
                self._close_logger_handlers()
            except Exception as e:
                get_logger(__name__).debug("Suppressed exception: %s", e)
            # 即使异常也尽最大努力破环
            for attr in ('_spider', '_engine', '_stats', '_subscriber', '_extension',
                         '_metrics', '_resource_manager', '_settings', '_logger'):
                try:
                    object.__setattr__(self, attr, None)
                except Exception as e:
                    get_logger(__name__).debug("Suppressed exception: %s", e)

    def _cleanup_engine_sync(self, reason: str) -> None:
        """同步版本 _cleanup_engine（破环专用，忽略失败）"""
        if not self._engine:
            return
        # 异步 close 无法在同步代码里调用；这里只做引用断开
        self._engine = None

    async def _cleanup_engine(self, reason: str) -> None:
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
        try:
            if self._logger:
                for handler in self._logger.handlers[:]:
                    try:
                        handler.close()
                        self._logger.removeHandler(handler)
                    except Exception as e:
                        get_logger(__name__).debug("Suppressed exception: %s", e)
        except Exception as e:
            get_logger(__name__).debug("Suppressed exception: %s", e)


__all__ = [
    'CrawlerState', 'CrawlerMetrics', 'Crawler',
    'initialize_framework', 'is_framework_ready', 'get_logger',
]
