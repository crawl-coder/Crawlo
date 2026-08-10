#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
CrawlerProcess 进程管理器子模块（管理多个 Crawler）。

管理信号处理 / Windows asyncio 修复 / 信号量并发 / 多爬虫并行。
"""
from __future__ import annotations

import asyncio
import sys
import time
import threading  # noqa: F401 (kept for backward-compat alias at runtime)
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Type, Union, cast

from crawlo.core.application import initialize_framework
from crawlo.logging import get_logger
from crawlo.settings.setting_manager import SettingManager
from crawlo.utils.concurrency import ProcessSignalHandler, SpiderDiscoveryUtils, SettingsUtils
from crawlo.spider import get_global_spider_registry, SpiderResolver

from ._crawler import Crawler

if TYPE_CHECKING:
    from crawlo.spider import Spider


class CrawlerProcess:
    """Crawler 进程管理器 - 管理多个 Crawler 的执行。"""

    def __init__(
        self,
        settings: Optional['SettingManager'] = None,
        max_spiders: int = None,
        spider_modules: Optional[List[str]] = None,
    ) -> None:
        self._settings: Optional['SettingManager'] = settings or initialize_framework()

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

        self._signal_handler = ProcessSignalHandler(self._logger, self._crawlers)
        self._shutdown_event: asyncio.Event = self._signal_handler.shutdown_event

        self._apply_windows_asyncio_fix()

        if spider_modules is None and self._settings:
            spider_modules = self._settings.get('SPIDER_MODULES', [])
            self._logger.debug(f"从settings中获取SPIDER_MODULES: {spider_modules}")
        self._spider_modules: List[str] = spider_modules or []

        if self._spider_modules:
            self._register_spider_modules(self._spider_modules)

        self._start_time: Optional[float] = None
        self._end_time: Optional[float] = None

        self._setup_signal_handlers()

    def _setup_signal_handlers(self):
        self._signal_handler.set_crawlers(self._crawlers)

    @property
    def _shutdown_requested(self) -> bool:
        return self._signal_handler.shutdown_requested

    def _apply_windows_asyncio_fix(self) -> None:
        if sys.platform != 'win32':
            return

        try:
            import asyncio.proactor_events
            import warnings

            _original_del = asyncio.proactor_events._ProactorBasePipeTransport.__del__

            def _patched_del(self):
                try:
                    _original_del(self)
                except (ValueError, OSError):
                    pass

            asyncio.proactor_events._ProactorBasePipeTransport.__del__ = _patched_del

            try:
                import asyncio.base_subprocess
                _original_sub_del = asyncio.base_subprocess.BaseSubprocessTransport.__del__

                def _patched_sub_del(self):
                    try:
                        _original_sub_del(self)
                    except (ValueError, OSError):
                        pass

                asyncio.base_subprocess.BaseSubprocessTransport.__del__ = _patched_sub_del
            except Exception as e:
                get_logger(__name__).debug("Suppressed exception: %s", e)

            warnings.filterwarnings('ignore', message='unclosed transport', category=ResourceWarning)
            self._logger.debug("已自动应用 Windows asyncio 传输关闭警告修复")
        except Exception as e:
            self._logger.debug(f"应用 Windows asyncio 修复失败(可忽略): {e}")
        try:
            asyncio.get_running_loop()
            if hasattr(self, '_signal_handler') and self._signal_handler is not None:
                self._signal_handler.setup_signal_handlers()
        except RuntimeError:
            self._logger.debug("Event loop not running, signal handlers will be set up later")

    async def _graceful_shutdown(self):
        self._signal_handler.set_crawlers(self._crawlers)
        await self._signal_handler.graceful_shutdown()

    def _register_spider_modules(self, spider_modules: List[str]) -> None:
        SpiderDiscoveryUtils.register_spider_modules(spider_modules, self._logger)

    def _auto_discover_spider_modules(self, spider_modules: List[str]) -> None:
        SpiderDiscoveryUtils.auto_discover_spider_modules(spider_modules, self._logger)

    def is_spider_registered(self, name: str) -> bool:
        registry = get_global_spider_registry()
        return name in registry

    def get_spider_class(self, name: str) -> Optional[Type['Spider']]:
        registry = get_global_spider_registry()
        return registry.get(name)

    def get_spider_names(self) -> List[str]:
        registry = get_global_spider_registry()
        return list(registry.keys())

    async def crawl(
        self,
        spider_cls_or_name: Union[Type['Spider'], str, List[Union[Type['Spider'], str]]],
        settings: Optional[Dict[str, Any]] = None,
    ) -> Union[Crawler, List[Union[Crawler, BaseException]]]:
        if sys.platform.lower().startswith('win'):
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

        self._signal_handler.setup_signal_handlers()

        result = None
        try:
            if not isinstance(spider_cls_or_name, list):
                result = await self._crawl_single(spider_cls_or_name, settings)
            else:
                result = await self._crawl_multiple(spider_cls_or_name, settings)
            return result

        except KeyboardInterrupt:
            self._shutdown_event.set()
            await self._graceful_shutdown()
            raise
        except asyncio.CancelledError:
            await self._graceful_shutdown()
            raise
        except Exception as e:
            self._logger.error(f"Error during crawl: {e}")
            await self._graceful_shutdown()
            raise
        finally:
            await self._shutdown_loop_transports()

    async def _crawl_single(
        self,
        spider_cls_or_name: Union[Type['Spider'], str],
        settings: Optional[Dict[str, Any]] = None,
    ) -> Crawler:
        spider_cls = self._resolve_spider_class(spider_cls_or_name)
        self._logger.info(f"Starting spider: {spider_cls.name}")

        merged_settings = self._merge_settings(settings)
        crawler = Crawler(spider_cls, merged_settings)
        crawler._process = self

        if crawler not in self._crawlers:
            self._crawlers.append(crawler)

        async with self._semaphore:
            crawl_task = asyncio.create_task(crawler.crawl())
            shutdown_wait_task = asyncio.create_task(self._shutdown_event.wait())

            try:
                done, pending = await asyncio.wait(
                    [crawl_task, shutdown_wait_task],
                    return_when=asyncio.FIRST_COMPLETED
                )

                if self._shutdown_event.is_set() and not crawl_task.done():
                    self._logger.info(f"Shutdown requested, cancelling spider: {spider_cls.name}")
                    crawl_task.cancel()
                    try:
                        await crawl_task
                    except asyncio.CancelledError:
                        self._logger.debug(f"Spider {spider_cls.name} cancelled successfully")

                if crawl_task.done() and not crawl_task.cancelled():
                    exc = crawl_task.exception()
                    if exc:
                        raise exc

            except asyncio.CancelledError:
                self._logger.debug(f"Crawl task was cancelled: {spider_cls.name}")
                raise
            finally:
                if not crawl_task.done():
                    crawl_task.cancel()
                    try:
                        await crawl_task
                    except asyncio.CancelledError:
                        pass
                if not shutdown_wait_task.done():
                    shutdown_wait_task.cancel()
                    try:
                        await shutdown_wait_task
                    except asyncio.CancelledError:
                        pass

        await self._graceful_shutdown()
        await self._cleanup_crawler(crawler, spider_cls.name)
        return crawler

    async def _crawl_multiple(
        self,
        spider_classes_or_names: List[Union[Type['Spider'], str]],
        settings: Optional[Dict[str, Any]] = None,
    ) -> List[Union[Crawler, BaseException]]:
        self._start_time = time.time()

        try:
            spider_classes = []
            for cls_or_name in spider_classes_or_names:
                spider_cls = self._resolve_spider_class(cls_or_name)
                spider_classes.append(spider_cls)

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

            successful = sum(1 for r in results if not isinstance(r, Exception))
            failed = len(results) - successful
            self._logger.info(f"Crawl completed: {successful} successful, {failed} failed")

            return cast(List[Union[Crawler, BaseException]], results)

        finally:
            await self._cleanup_all_crawlers()
            self._end_time = time.time()
            if self._start_time:
                duration = self._end_time - self._start_time
                self._logger.info(f"Total execution time: {duration:.2f}s")

    async def _cleanup_crawler(self, crawler: Crawler, spider_name: str) -> None:
        await self._cleanup_single_crawler(crawler)
        self._logger.debug(f"Cleaned up crawler: {spider_name}")

    async def _cleanup_all_crawlers(self) -> None:
        self._logger.debug(f"Cleaning up {len(self._crawlers)} crawler(s)...")
        for crawler in self._crawlers:
            await self._cleanup_single_crawler(crawler)
        self._crawlers.clear()

    async def _cleanup_single_crawler(self, crawler: Crawler) -> None:
        try:
            # 在调用 crawler.close 前把 resource_manager 存下来：
            # 因为 close 内部在破引用环阶段会把 crawler._resource_manager 置 None，
            # 若 close 中途异常走不到兜底 cleanup_all，用这个局部变量仍可兜底。
            rm_backup = getattr(crawler, '_resource_manager', None)
            try:
                if hasattr(crawler, 'close'):
                    result = crawler.close()
                    if asyncio.iscoroutine(result):
                        await result
            except Exception as e:
                self._logger.warning(f"crawler.close() failed: {e}")
            # 兜底：如果 crawler.close 没走到 _resource_manager.cleanup_all
            # （例如中途异常 _state=ERROR/close 抛错），再做一次，保证注册的资源被触发。
            # Crawler._cleanup 里 cleanup_all 成功后会调用 rm.clear()（幂等且安全），
            # 所以这里即使再 cleanup_all 也不会有副作用（仅多打几条 debug log）。
            if rm_backup is not None:
                try:
                    await rm_backup.cleanup_all()
                    if hasattr(rm_backup, 'clear'):
                        rm_backup.clear()
                except Exception as e:
                    self._logger.warning(f"Fallback resource_manager.cleanup_all failed: {e}")
        except Exception as e:
            self._logger.warning(f"Failed to cleanup crawler: {e}")

    async def _shutdown_loop_transports(self) -> None:
        if sys.platform != 'win32':
            return
        try:
            loop = asyncio.get_running_loop()
            await loop.shutdown_asyncgens()
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
                except Exception as e:
                    get_logger(__name__).debug("Suppressed exception: %s", e)
            if closed_count:
                self._logger.debug(f"Proactively closed {closed_count} transport(s)")
                await asyncio.sleep(0.05)
        except Exception as e:
            self._logger.debug(f"Loop transport cleanup error (ignorable): {e}")

    async def _run_with_semaphore(self, crawler: Crawler) -> Crawler:
        async with self._semaphore:
            await crawler.crawl()
            return crawler

    def _resolve_spider_class(
        self, spider_cls_or_name: Union[Type['Spider'], str]
    ) -> Type['Spider']:
        return SpiderResolver.resolve_spider_class(
            spider_cls_or_name, getattr(self, '_spider_modules', None)
        )

    def _merge_settings(
        self, additional_settings: Optional[Dict[str, Any]]
    ) -> Optional['SettingManager']:
        return SettingsUtils.merge_settings(self._settings, additional_settings)

    def get_metrics(self) -> Dict[str, Any]:
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
            'average_success_rate': sum(m.get_success_rate() for m in crawler_metrics) / len(crawler_metrics)
            if crawler_metrics else 0.0,
        }


__all__ = ['CrawlerProcess']
