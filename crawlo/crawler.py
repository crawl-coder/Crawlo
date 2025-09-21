#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Crawlo Crawler Module
====================
Provides crawler process management and runtime core functionality.

Core Components:
- Crawler: Single crawler runtime instance, managing Spider and engine lifecycle
- CrawlerProcess: Crawler process manager, supporting multi-crawler concurrent scheduling and resource management

Features:
- Intelligent concurrency control and resource management
- Graceful shutdown and signal handling
- Statistics monitoring and performance tracking
- Automatic module discovery and registration
- Error recovery and retry mechanism
- Large-scale crawler optimization support

Example Usage:
    # Single crawler run
    crawler = Crawler(MySpider, settings)
    await crawler.crawl()

    # Multi-crawler concurrent management
    process = CrawlerProcess()
    await process.crawl([Spider1, Spider2])
"""
from __future__ import annotations
import asyncio
import signal
import time
import threading
from typing import Type, Optional, Set, List, Union, Dict, Any
from .spider import Spider, get_global_spider_registry
from .core.engine import Engine
from .subscriber import Subscriber
from .extension import ExtensionManager
from .stats_collector import StatsCollector
from .event import spider_opened, spider_closed
from .settings.setting_manager import SettingManager
from crawlo.project import merge_settings, get_settings

# 使用自定义日志系统
from crawlo.utils.log import get_logger
logger = get_logger(__name__)


class CrawlerContext:
    """
    Crawler context manager
    Provides shared state and resource management
    """

    def __init__(self):
        self.start_time = time.time()
        self.total_crawlers = 0
        self.active_crawlers = 0
        self.completed_crawlers = 0
        self.failed_crawlers = 0
        self.error_log = []
        self._lock = threading.RLock()

    def increment_total(self):
        with self._lock:
            self.total_crawlers += 1

    def increment_active(self):
        with self._lock:
            self.active_crawlers += 1

    def decrement_active(self):
        with self._lock:
            self.active_crawlers -= 1

    def increment_completed(self):
        with self._lock:
            self.completed_crawlers += 1

    def increment_failed(self, error: str):
        with self._lock:
            self.failed_crawlers += 1
            self.error_log.append({
                'timestamp': time.time(),
                'error': error
            })

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            duration = time.time() - self.start_time
            return {
                'total_crawlers': self.total_crawlers,
                'active_crawlers': self.active_crawlers,
                'completed_crawlers': self.completed_crawlers,
                'failed_crawlers': self.failed_crawlers,
                'success_rate': (self.completed_crawlers / max(1, self.total_crawlers)) * 100,
                'duration_seconds': round(duration, 2),
                'error_count': len(self.error_log)
            }


class Crawler:
    """
    Single crawler runtime instance, managing Spider and engine lifecycle

    Provides functionality:
    - Spider lifecycle management (initialization, running, closing)
    - Engine component coordination management
    - Configuration merging and validation
    - Statistics data collection
    - Extension management
    - Exception handling and cleanup
    """

    def __init__(self, spider_cls: Type[Spider], settings: SettingManager, context: Optional[CrawlerContext] = None):
        self.spider_cls = spider_cls
        self.spider: Optional[Spider] = None
        self.engine: Optional[Engine] = None
        self.stats: Optional[StatsCollector] = None
        self.subscriber: Optional[Subscriber] = None
        self.extension: Optional[ExtensionManager] = None
        self.settings: SettingManager = settings.copy()
        self.context = context or CrawlerContext()

        # State management
        self._closed = False
        self._close_lock = asyncio.Lock()
        self._start_time = None
        self._end_time = None

        # Performance monitoring
        self._performance_metrics = {
            'initialization_time': 0,
            'crawl_duration': 0,
            'memory_peak': 0,
            'request_count': 0,
            'error_count': 0
        }

    async def crawl(self):
        """
        Start the crawler core process

        Includes the following stages:
        1. Initialization stage: Create all components
        2. Validation stage: Check configuration and state
        3. Running stage: Start the crawler engine
        4. Cleanup stage: Resource release
        """
        init_start = time.time()
        self._start_time = init_start

        try:
            # Update context status
            self.context.increment_active()

            # Phase 1: Initialize components
            # Adjust component initialization order to ensure log output order meets requirements
            self.subscriber = self._create_subscriber()
            self.spider = self._create_spider()
            self.engine = self._create_engine()
            self.stats = self._create_stats()
            # Note: Do not initialize extension manager here, let it initialize in the engine

            # Record initialization time
            self._performance_metrics['initialization_time'] = time.time() - init_start

            # Phase 2: Validate state
            self._validate_crawler_state()

            # Phase 3: Display runtime configuration summary
            self._log_runtime_summary()

            # Phase 4: Start crawler
            crawl_start = time.time()
            await self.engine.start_spider(self.spider)

            # Record crawl time
            self._performance_metrics['crawl_duration'] = time.time() - crawl_start
            self._end_time = time.time()

            # Update context status
            self.context.increment_completed()

            logger.info(f"Spider {self.spider.name} completed, took {self._get_total_duration():.2f} seconds")

        except Exception as e:
            self._performance_metrics['error_count'] += 1
            self.context.increment_failed(str(e))
            logger.error(f"Spider {getattr(self.spider, 'name', 'Unknown')} failed to run: {e}", exc_info=True)
            raise
        finally:
            self.context.decrement_active()
            # Ensure resource cleanup
            await self._ensure_cleanup()

    def _log_runtime_summary(self):
        """Log runtime configuration summary"""
        # Get spider name
        spider_name = getattr(self.spider, 'name', 'Unknown')

        # Ensure spider name is a string and strip leading/trailing whitespace
        if spider_name:
            spider_name = str(spider_name).strip()
        else:
            spider_name = 'Unknown'

        logger.info(f"Starting running {spider_name}")

    def _validate_crawler_state(self):
        """
        Validate crawler state and configuration
        Ensure all necessary components are properly initialized
        """
        if not self.spider:
            raise RuntimeError("Spider instance not initialized")
        if not self.engine:
            raise RuntimeError("Engine not initialized")
        if not self.stats:
            raise RuntimeError("Stats collector not initialized")
        if not self.subscriber:
            raise RuntimeError("Event subscriber not initialized")

        # Check key configuration
        if not self.spider.name:
            raise ValueError("Spider name cannot be empty")

        logger.debug(f"Spider {self.spider.name} state validation passed")

    def _get_total_duration(self) -> float:
        """Get total runtime"""
        if self._start_time and self._end_time:
            return self._end_time - self._start_time
        return 0.0

    async def _ensure_cleanup(self):
        """Ensure resource cleanup"""
        try:
            if not self._closed:
                await self.close()
        except Exception as e:
            logger.warning(f"Error cleaning up resources: {e}")

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        metrics = self._performance_metrics.copy()
        metrics['total_duration'] = self._get_total_duration()
        if self.stats:
            # Add statistics data
            stats_data = getattr(self.stats, 'get_stats', lambda: {})()
            metrics.update(stats_data)
        return metrics

    @staticmethod
    def _create_subscriber() -> Subscriber:
        """Create event subscriber"""
        return Subscriber()

    def _create_spider(self) -> Spider:
        """
        Create and validate spider instance (enhanced version)

        Performs the following validations:
        - Spider name must exist
        - start_requests method must be callable
        - start_urls cannot be a string
        - parse method is recommended to exist
        """
        spider = self.spider_cls.create_instance(self)

        # Required attribute check
        if not getattr(spider, 'name', None):
            raise AttributeError(
                f"Spider class '{self.spider_cls.__name__}' must define 'name' attribute.\n"
                f"Example: name = 'my_spider'"
            )

        if not callable(getattr(spider, 'start_requests', None)):
            raise AttributeError(
                f"Spider '{spider.name}' must implement a callable 'start_requests' method.\n"
                f"Example: def start_requests(self): yield Request(url='...')"
            )

        # start_urls type check
        start_urls = getattr(spider, 'start_urls', [])
        if isinstance(start_urls, str):
            raise TypeError(
                f"Spider '{spider.name}' 'start_urls' must be a list or tuple, not a string.\n"
                f"Correct: start_urls = ['http://example.com']\n"
                f"Incorrect: start_urls = 'http://example.com'"
            )

        # parse method check (warning instead of error)
        if not callable(getattr(spider, 'parse', None)):
            logger.warning(
                f"Spider '{spider.name}' does not define 'parse' method.\n"
                f"Ensure all Requests specify a callback function, otherwise responses will be ignored."
            )

        # Set spider configuration
        self._set_spider(spider)

        logger.debug(f"Spider '{spider.name}' initialized successfully")
        return spider

    def _create_engine(self) -> Engine:
        """Create and initialize engine"""
        engine = Engine(self)
        engine.engine_start()
        logger.debug(f"Engine initialized successfully, spider: {getattr(self.spider, 'name', 'Unknown')}")
        return engine

    def _create_stats(self) -> StatsCollector:
        """Create stats collector"""
        stats = StatsCollector(self)
        logger.debug(
            f"Stats collector initialized successfully, spider: {getattr(self.spider, 'name', 'Unknown')}")
        return stats

    def _create_extension(self) -> ExtensionManager:
        """Create extension manager"""
        # Modify extension manager creation method, delay initialization until needed
        extension = ExtensionManager.create_instance(self)
        logger.debug(
            f"Extension manager initialized successfully, spider: {getattr(self.spider, 'name', 'Unknown')}")
        return extension

    def _set_spider(self, spider: Spider):
        """
        Set spider configuration and event subscription
        Bind spider lifecycle events with subscriber
        """
        # Subscribe to spider lifecycle events
        self.subscriber.subscribe(spider.spider_opened, event=spider_opened)
        self.subscriber.subscribe(spider.spider_closed, event=spider_closed)

        # Merge spider custom configuration
        merge_settings(spider, self.settings)

        logger.debug(f"Spider '{spider.name}' configuration merged successfully")

    async def close(self, reason='finished') -> None:
        """
        Close crawler and clean up resources (enhanced version)

        Ensure closing only once and handle all cleanup operations
        """
        async with self._close_lock:
            if self._closed:
                return

            self._closed = True
            self._end_time = time.time()

            try:
                # Notify spider close event
                if self.subscriber:
                    await self.subscriber.notify(spider_closed)

                # Statistics data collection
                if self.stats and self.spider:
                    self.stats.close_spider(spider=self.spider, reason=reason)
                    # Record statistics data
                    try:
                        from crawlo.commands.stats import record_stats
                        record_stats(self)
                    except ImportError:
                        logger.debug("Statistics recording module does not exist, skipping statistics recording")

                logger.info(
                    f"Spider '{getattr(self.spider, 'name', 'Unknown')}' closed, "
                    f"reason: {reason}, took: {self._get_total_duration():.2f} seconds"
                )

            except Exception as e:
                logger.error(f"Error closing crawler: {e}", exc_info=True)
            finally:
                # Ensure resource cleanup
                await self._cleanup_resources()

    async def _cleanup_resources(self):
        """Clean up all resources"""
        cleanup_tasks = []

        # Engine cleanup
        if self.engine:
            try:
                cleanup_tasks.append(self.engine.close())
            except AttributeError:
                pass  # Engine has no close method

        # Extension cleanup
        if self.extension:
            try:
                cleanup_tasks.append(self.extension.close())
            except AttributeError:
                pass

        # Stats collector cleanup
        if self.stats:
            try:
                cleanup_tasks.append(self.stats.close())
            except AttributeError:
                pass

        # Concurrently execute cleanup tasks
        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)

        logger.debug("Resource cleanup completed")


class CrawlerProcess:
    """
    Crawler process manager

    Supported features:
    - Multi-crawler concurrent scheduling and resource management
    - Automatic module discovery and spider registration
    - Intelligent concurrency control and load balancing
    - Graceful shutdown and signal handling
    - Real-time status monitoring and statistics
    - Error recovery and retry mechanism
    - Large-scale crawler optimization support

    Usage example:
        # Basic usage
        process = CrawlerProcess()
        await process.crawl(MySpider)

        # Multi-crawler concurrency
        await process.crawl([Spider1, Spider2, 'spider_name'])

        # Custom concurrency
        process = CrawlerProcess(max_concurrency=8)
    """

    def __init__(
            self,
            settings: Optional[SettingManager] = None,
            max_concurrency: Optional[int] = None,
            spider_modules: Optional[List[str]] = None,
            enable_monitoring: bool = True
    ):
        # Basic configuration
        self.settings: SettingManager = settings or self._get_default_settings()
        self.crawlers: Set[Crawler] = set()
        self._active_tasks: Set[asyncio.Task] = set()

        # Context manager
        self.context = CrawlerContext()

        # Concurrency control configuration
        self.max_concurrency: int = (
                max_concurrency
                or self.settings.get('MAX_RUNNING_SPIDERS')
                or self.settings.get('CONCURRENCY', 3)
        )
        self.semaphore = asyncio.Semaphore(self.max_concurrency)

        # Monitoring configuration
        self.enable_monitoring = enable_monitoring
        self._monitoring_task = None
        self._shutdown_event = asyncio.Event()

        # Automatically discover and import spider modules
        if spider_modules:
            self.auto_discover(spider_modules)

        # Use snapshot of global registry (avoid subsequent import impact)
        self._spider_registry: Dict[str, Type[Spider]] = get_global_spider_registry()

        # Performance monitoring
        self._performance_stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'memory_usage_mb': 0,
            'cpu_usage_percent': 0
        }

        # Register signal handlers
        signal.signal(signal.SIGINT, self._shutdown)
        signal.signal(signal.SIGTERM, self._shutdown)

        self._log_startup_info()

        logger.debug(
            f"CrawlerProcess initialized successfully\n"
            f"  - Max concurrent crawlers: {self.max_concurrency}\n"
            f"  - Registered crawlers: {len(self._spider_registry)}\n"
            f"  - Monitoring enabled: {self.enable_monitoring}"
        )

    async def start_monitoring(self):
        """Start monitoring task"""
        if not self.enable_monitoring:
            return

        self._monitoring_task = asyncio.create_task(self._monitor_loop())
        logger.debug("Monitoring task started")

    async def stop_monitoring(self):
        """Stop monitoring task"""
        if self._monitoring_task and not self._monitoring_task.done():
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
            logger.debug("Monitoring task stopped")

    async def _monitor_loop(self):
        """Monitoring loop, periodically collect and report status"""
        try:
            while not self._shutdown_event.is_set():
                await self._collect_performance_stats()

                # Output status every 30 seconds
                stats = self.context.get_stats()
                if stats['active_crawlers'] > 0:
                    logger.debug(
                        f"Crawler status: Active {stats['active_crawlers']}, "
                        f"Completed {stats['completed_crawlers']}, "
                        f"Failed {stats['failed_crawlers']}, "
                        f"Success rate {stats['success_rate']:.1f}%"
                    )

                await asyncio.sleep(30)  # 30 second interval

        except asyncio.CancelledError:
            logger.debug("Monitoring loop cancelled")
        except Exception as e:
            logger.error(f"Monitoring loop error: {e}", exc_info=True)

    async def _collect_performance_stats(self):
        """Collect performance statistics data"""
        try:
            import psutil
            import os

            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()

            self._performance_stats.update({
                'memory_usage_mb': round(memory_info.rss / 1024 / 1024, 2),
                'cpu_usage_percent': round(process.cpu_percent(), 2)
            })

        except ImportError:
            # Skip performance monitoring when psutil is not available
            pass
        except Exception as e:
            logger.debug(f"Failed to collect performance statistics: {e}")

    @staticmethod
    def auto_discover(modules: List[str]):
        """
        Automatically import modules, trigger Spider class definition and registration (enhanced version)

        Supports recursive scanning and error recovery
        """
        import importlib
        import pkgutil

        discovered_count = 0
        error_count = 0

        for module_name in modules:
            try:
                module = importlib.import_module(module_name)

                if hasattr(module, '__path__'):
                    # Package module, recursive scanning
                    for _, name, _ in pkgutil.walk_packages(module.__path__, module.__name__ + "."):
                        try:
                            importlib.import_module(name)
                            discovered_count += 1
                        except Exception as sub_e:
                            error_count += 1
                            logger.warning(f"Failed to import submodule {name}: {sub_e}")
                else:
                    # Single module
                    importlib.import_module(module_name)
                    discovered_count += 1

                logger.debug(f"Module scanned: {module_name}")

            except Exception as e:
                error_count += 1
                logger.error(f"Failed to scan module {module_name}: {e}", exc_info=True)

        logger.debug(
            f"Spider registration completed: {discovered_count} succeeded, {error_count} failed"
        )

    # === Public read-only interface: Avoid direct access to _spider_registry ===

    def get_spider_names(self) -> List[str]:
        """Get all registered spider names"""
        return list(self._spider_registry.keys())

    def get_spider_class(self, name: str) -> Optional[Type[Spider]]:
        """Get spider class by name"""
        return self._spider_registry.get(name)

    def is_spider_registered(self, name: str) -> bool:
        """Check if a name is registered"""
        return name in self._spider_registry

    async def crawl(self, spiders: Union[Type[Spider], str, List[Union[Type[Spider], str]]]):
        """
        Start one or more crawlers

        Enhanced features:
        - Intelligent concurrency control
        - Real-time monitoring and statistics
        - Error recovery and retry
        - Graceful shutdown handling
        """
        # Phase 1: Preprocessing and validation
        spider_classes_to_run = self._resolve_spiders_to_run(spiders)
        total = len(spider_classes_to_run)

        if total == 0:
            raise ValueError("At least one spider class or name must be provided")

        # Phase 2: Initialize context and monitoring
        for _ in range(total):
            self.context.increment_total()

        # Start monitoring task
        await self.start_monitoring()

        try:
            # Phase 3: Initialize context and monitoring
            spider_classes_to_run.sort(key=lambda cls: cls.__name__.lower())

            logger.debug(
                f"Starting {total} crawlers\n"
                f"  - Max concurrency: {self.max_concurrency}\n"
                f"  - Spider list: {[cls.__name__ for cls in spider_classes_to_run]}"
            )

            # Phase 4: Stream start all crawler tasks
            tasks = [
                asyncio.create_task(
                    self._run_spider_with_limit(spider_cls, index + 1, total),
                    name=f"spider-{spider_cls.__name__}-{index + 1}"
                )
                for index, spider_cls in enumerate(spider_classes_to_run)
            ]

            # Phase 5: Wait for all tasks to complete (failures do not interrupt)
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Phase 6: Statistics exceptions and results
            failed = [i for i, r in enumerate(results) if isinstance(r, Exception)]
            successful = total - len(failed)

            if failed:
                failed_spiders = [spider_classes_to_run[i].__name__ for i in failed]
                logger.error(
                    f"Crawler execution result: {successful}/{total} succeeded, {len(failed)}/{total} failed\n"
                    f"  - Failed crawlers: {failed_spiders}"
                )

                # Record detailed error information
                for i in failed:
                    error = results[i]
                    logger.error(f"Spider {spider_classes_to_run[i].__name__} error details: {error}")
            else:
                logger.info(f"All {total} crawlers completed successfully!")

            # Return statistics results
            return {
                'total': total,
                'successful': successful,
                'failed': len(failed),
                'success_rate': (successful / total) * 100 if total > 0 else 0,
                'context_stats': self.context.get_stats()
            }

        finally:
            # Phase 7: Cleanup and shutdown
            await self.stop_monitoring()
            await self._cleanup_process()

    async def _cleanup_process(self):
        """Clean up process resources"""
        try:
            # Wait for all active crawlers to complete
            if self.crawlers:
                close_tasks = [crawler.close() for crawler in self.crawlers]
                await asyncio.gather(*close_tasks, return_exceptions=True)
                self.crawlers.clear()

            # Clean up active tasks
            if self._active_tasks:
                for task in list(self._active_tasks):
                    if not task.done():
                        task.cancel()
                await asyncio.gather(*self._active_tasks, return_exceptions=True)
                self._active_tasks.clear()

            logger.debug("Process resources cleanup completed")

        except Exception as e:
            logger.error(f"Error cleaning up process resources: {e}", exc_info=True)

    def get_process_stats(self) -> Dict[str, Any]:
        """Get process statistics information"""
        context_stats = self.context.get_stats()

        return {
            'context': context_stats,
            'performance': self._performance_stats.copy(),
            'crawlers': {
                'total_registered': len(self._spider_registry),
                'active_crawlers': len(self.crawlers),
                'max_concurrency': self.max_concurrency
            },
            'registry': {
                'spider_names': list(self._spider_registry.keys()),
                'spider_classes': [cls.__name__ for cls in self._spider_registry.values()]
            }
        }

    def _resolve_spiders_to_run(
            self,
            spiders_input: Union[Type[Spider], str, List[Union[Type[Spider], str]]]
    ) -> List[Type[Spider]]:
        """
        Resolve input to spider class list

        Supports various input formats and validates uniqueness
        """
        inputs = self._normalize_inputs(spiders_input)
        seen_spider_names: Set[str] = set()
        spider_classes: List[Type[Spider]] = []

        for item in inputs:
            try:
                spider_cls = self._resolve_spider_class(item)
                spider_name = getattr(spider_cls, 'name', None)

                if not spider_name:
                    raise ValueError(f"Spider class {spider_cls.__name__} missing 'name' attribute")

                if spider_name in seen_spider_names:
                    raise ValueError(
                        f"Duplicate spider name '{spider_name}' in this run.\n"
                        f"Ensure each spider's name attribute is unique in this run."
                    )

                seen_spider_names.add(spider_name)
                spider_classes.append(spider_cls)

                logger.debug(
                    f"Spider resolved successfully: {item} -> {spider_cls.__name__} (name='{spider_name}')")

            except Exception as e:
                logger.error(f"Failed to resolve spider: {item} - {e}")
                raise

        return spider_classes

    @staticmethod
    def _normalize_inputs(spiders_input) -> List[Union[Type[Spider], str]]:
        """
        Normalize input to list

        Supports more input types and provides better error information
        """
        if isinstance(spiders_input, (type, str)):
            return [spiders_input]
        elif isinstance(spiders_input, (list, tuple, set)):
            spider_list = list(spiders_input)
            if not spider_list:
                raise ValueError("Spider list cannot be empty")
            return spider_list
        else:
            raise TypeError(
                f"Unsupported spiders parameter type: {type(spiders_input)}\n"
                f"Supported types: Spider class, name string, or their list/tuple/set"
            )

    def _resolve_spider_class(self, item: Union[Type[Spider], str]) -> Type[Spider]:
        """
        Resolve single input item to spider class

        Provides better error prompts and debugging information
        """
        if isinstance(item, type) and issubclass(item, Spider):
            # Direct Spider class
            return item
        elif isinstance(item, str):
            # String name, need to look up registry
            spider_cls = self._spider_registry.get(item)
            if not spider_cls:
                available_spiders = list(self._spider_registry.keys())
                raise ValueError(
                    f"Spider named '{item}' not found.\n"
                    f"Registered spiders: {available_spiders}\n"
                    f"Please check if the spider name is correct, or ensure the spider has been properly imported and registered."
                )
            return spider_cls
        else:
            raise TypeError(
                f"Invalid type {type(item)}: {item}\n"
                f"Must be Spider class or string name.\n"
                f"Example: MySpider or 'my_spider'"
            )

    async def _run_spider_with_limit(self, spider_cls: Type[Spider], seq: int, total: int):
        """
        Spider running function limited by semaphore

        Includes enhanced error handling and monitoring functionality
        """
        task = asyncio.current_task()
        crawler = None

        try:
            # Register task
            if task:
                self._active_tasks.add(task)

            # Acquire concurrency permit
            await self.semaphore.acquire()

            # start_msg = f"[{seq}/{total}] Initializing spider: {spider_cls.__name__}"
            # logger.info(start_msg)

            # Create and run crawler
            crawler = Crawler(spider_cls, self.settings, self.context)
            self.crawlers.add(crawler)

            # Record start time
            start_time = time.time()

            # Run crawler
            await crawler.crawl()

            # Calculate runtime
            duration = time.time() - start_time

            end_msg = (
                f"[{seq}/{total}] Crawler completed: {spider_cls.__name__}, "
                f"took: {duration:.2f} seconds"
            )
            logger.info(end_msg)

            # Record success statistics
            self._performance_stats['successful_requests'] += 1

        except Exception as e:
            # Record failure statistics
            self._performance_stats['failed_requests'] += 1

            error_msg = f"Spider {spider_cls.__name__} execution failed: {e}"
            logger.error(error_msg, exc_info=True)

            # Record error information to context
            if hasattr(self, 'context'):
                self.context.increment_failed(error_msg)

            raise
        finally:
            # Clean up resources
            try:
                if crawler and crawler in self.crawlers:
                    self.crawlers.remove(crawler)

                if task and task in self._active_tasks:
                    self._active_tasks.remove(task)

                self.semaphore.release()

            except Exception as cleanup_error:
                logger.warning(f"Error cleaning up resources: {cleanup_error}")

    def _shutdown(self, _signum, _frame):
        """
        Graceful shutdown signal handling

        Provides better shutdown experience and resource cleanup
        """
        signal_name = {signal.SIGINT: 'SIGINT', signal.SIGTERM: 'SIGTERM'}.get(_signum, str(_signum))
        logger.warning(f"Received shutdown signal {signal_name}, stopping all crawlers...")

        # Set shutdown event
        if hasattr(self, '_shutdown_event'):
            self._shutdown_event.set()

        # Stop all crawler engines
        for crawler in list(self.crawlers):
            if crawler.engine:
                crawler.engine.running = False
                crawler.engine.normal = False
                logger.debug(f"Crawler engine stopped: {getattr(crawler.spider, 'name', 'Unknown')}")

        # Create shutdown task
        asyncio.create_task(self._wait_for_shutdown())

        logger.info("Shutdown command sent, waiting for crawlers to complete current tasks...")

    async def _wait_for_shutdown(self):
        """
        Wait for all active tasks to complete

        Provides better shutdown time control and progress feedback
        """
        try:
            # Stop monitoring task
            await self.stop_monitoring()

            # Wait for active tasks to complete
            pending = [t for t in self._active_tasks if not t.done()]

            if pending:
                logger.info(
                    f"Waiting for {len(pending)} active tasks to complete..."
                    f"(Maximum wait time: 30 seconds)"
                )

                # Set timeout
                try:
                    await asyncio.wait_for(
                        asyncio.gather(*pending, return_exceptions=True),
                        timeout=30.0
                    )
                except asyncio.TimeoutError:
                    logger.warning("Some tasks timed out, forcing cancellation...")

                    # Force cancel timed out tasks
                    for task in pending:
                        if not task.done():
                            task.cancel()

                    # Wait for cancellation to complete
                    await asyncio.gather(*pending, return_exceptions=True)

            # Final cleanup
            await self._cleanup_process()

            # Output final statistics
            final_stats = self.context.get_stats()
            logger.info(
                f"All crawlers gracefully shut down 👋\n"
                f"  - Total crawlers: {final_stats['total_crawlers']}\n"
                f"  - Successfully completed: {final_stats['completed_crawlers']}\n"
                f"  - Failed: {final_stats['failed_crawlers']}\n"
                f"  - Success rate: {final_stats['success_rate']:.1f}%\n"
                f"  - Total runtime: {final_stats['duration_seconds']} seconds"
            )

        except Exception as e:
            logger.error(f"Error during shutdown process: {e}", exc_info=True)

    @classmethod
    def _get_default_settings(cls) -> SettingManager:
        """
        Load default configuration

        Provides better error handling and fallback strategy
        """
        try:
            settings = get_settings()
            logger.debug("Default configuration loaded successfully")
            return settings
        except Exception as e:
            logger.warning(f"Unable to load default configuration: {e}, using empty configuration")
            return SettingManager()

    def _log_startup_info(self):
        """Print startup information, including run mode and key configuration checks"""
        # Get run mode
        run_mode = self.settings.get('RUN_MODE', 'standalone')

        # Get version number
        version = self.settings.get('VERSION', '1.0.0')
        if not version or version == 'None':
            version = '1.0.0'

        # Build startup info log
        startup_info = [
            f"Crawlo Framework Started {version}"
        ]

        # Get actual queue type
        queue_type = self.settings.get('QUEUE_TYPE', 'memory')

        # Display information based on run mode and queue type combination
        if run_mode == 'distributed':
            startup_info.append("Run Mode: distributed")
            startup_info.append("Distributed Mode - Multi-node collaboration supported")
            # Show Redis configuration
            redis_host = self.settings.get('REDIS_HOST', 'localhost')
            redis_port = self.settings.get('REDIS_PORT', 6379)
            startup_info.append(f"Redis Address: {redis_host}:{redis_port}")
        elif run_mode == 'standalone':
            if queue_type == 'redis':
                startup_info.append("Run Mode: standalone+redis")
                # Show Redis configuration
                redis_host = self.settings.get('REDIS_HOST', 'localhost')
                redis_port = self.settings.get('REDIS_PORT', 6379)
                startup_info.append(f"Redis Address: {redis_host}:{redis_port}")
            elif queue_type == 'auto':
                startup_info.append("Run Mode: standalone+auto")
            else:  # memory
                startup_info.append("Run Mode: standalone")
        else:
            startup_info.append(f"Run Mode: {run_mode}")

        # Print startup information at INFO level
        for info in startup_info:
            logger.info(info)


# === Utility functions ===

def create_crawler_with_optimizations(
        spider_cls: Type[Spider],
        settings: Optional[SettingManager] = None,
        **optimization_kwargs
) -> Crawler:
    """
    Create an optimized crawler instance

    :param spider_cls: Spider class
    :param settings: Settings manager
    :param optimization_kwargs: Optimization parameters
    :return: Crawler instance
    """
    if settings is None:
        settings = SettingManager()

    # Apply optimization configuration
    for key, value in optimization_kwargs.items():
        settings.set(key, value)

    context = CrawlerContext()
    return Crawler(spider_cls, settings, context)


def create_process_with_large_scale_config(
        config_type: str = 'balanced',
        concurrency: int = 16,
        **kwargs
) -> CrawlerProcess:
    """
    Create a process manager that supports large-scale optimization

    :param config_type: Configuration type ('conservative', 'balanced', 'aggressive', 'memory_optimized')
    :param concurrency: Concurrency count
    :param kwargs: Other parameters
    :return: Process manager
    """
    try:
        from crawlo.utils.large_scale_config import LargeScaleConfig

        # Get optimization configuration
        config_methods = {
            'conservative': LargeScaleConfig.conservative_config,
            'balanced': LargeScaleConfig.balanced_config,
            'aggressive': LargeScaleConfig.aggressive_config,
            'memory_optimized': LargeScaleConfig.memory_optimized_config
        }

        if config_type not in config_methods:
            logger.warning(f"Unknown configuration type: {config_type}, using default configuration")
            settings = SettingManager()
        else:
            config = config_methods[config_type](concurrency)
            settings = SettingManager()
            settings.update(config)

        return CrawlerProcess(
            settings=settings,
            max_concurrency=concurrency,
            **kwargs
        )

    except ImportError:
        logger.warning("Large-scale configuration module does not exist, using default configuration")
        return CrawlerProcess(max_concurrency=concurrency, **kwargs)


# === Exported interfaces ===

__all__ = [
    'Crawler',
    'CrawlerProcess',
    'CrawlerContext',
    'create_crawler_with_optimizations',
    'create_process_with_large_scale_config'
]