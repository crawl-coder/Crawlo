#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
Engine 模块 — 爬虫引擎核心（拆分后主骨架）

拆分历史：
- 辅助组件拆分到 engine_helpers.py（GenerationStats / EngineBackpressureAdapter / …）
- RequestGenerationMixin 拆分到 engine_generation.py
- 分布式协调拆出 engine_distributed.py（DistributedCoordinator，组合持有）
- 请求派发 / 主循环 / 退出判断 拆出 engine_dispatch.py（RequestDispatcher，组合持有）

本模块只保留 Engine 主类（骨架），负责：
  1. __init__ / _init_configs：初始化所有组件并组合持有 _distributed / _dispatcher
  2. start_spider / crawl：生命周期骨架，调用 generation / dispatch / distributed
  3. close_spider：清理 & 检查点保存
  4. 对外薄代理方法：_check_control_state / _handle_distributed_idle / _try_claim_stale_pending
                      → 转给 self._distributed
     _run_main_loop / _dispatch_requests / _check_components_idle / _exit /
     _should_exit / _check_all_idle                           → 转给 self._dispatcher
  5. _crawl / _fetch：请求级处理（与 Engine 生命周期深度耦合，不拆）
"""
import asyncio
import time
from typing import Any, Dict, Optional, Union

from crawlo.spider import Spider
from crawlo.event import CrawlerEvent
from crawlo.project import common_call
from crawlo.core.errors import Failure, ErrorClassifier
from crawlo.logging import get_logger
from crawlo.core.scheduling.task_manager import TaskManager
from crawlo.downloader import DownloaderBase
from crawlo.core.processor import Processor
from crawlo.core.scheduling.task_scheduler import Scheduler
from crawlo.core.checkpoint_coordinator import CheckpointCoordinator
from crawlo.utils.misc import load_object, safe_get_config
from crawlo.__version__ import __version__
from crawlo.cluster.coordinator import ClusterMixin, ClusterState, _ack_message

# P1：Mixin + 辅助组件
from crawlo.core.engine_generation import RequestGenerationMixin
from crawlo.core.engine_helpers import (
    safe_queue_size,
    has_pending_enqueues,
    GenerationStats,
    EngineBackpressureAdapter,
    resolve_start_requests,
    process_callback_output,
)

# 组合模式的 Coordinator / Dispatcher
from crawlo.core.engine_distributed import DistributedCoordinator
from crawlo.core.engine_dispatch import RequestDispatcher

__all__ = [
    'Engine',
    'RequestGenerationMixin',
    'DistributedCoordinator',
    'RequestDispatcher',
    'resolve_start_requests',
    'process_callback_output',
    'GenerationStats',
    'EngineBackpressureAdapter',
    'safe_queue_size',
    'has_pending_enqueues',
]


class Engine(RequestGenerationMixin, ClusterMixin):

    CRITICAL_EXCEPTIONS = ErrorClassifier.CRITICAL_EXCEPTIONS

    def __init__(
        self,
        crawler,
        dispatcher=None,
        distributed=None,
        dispatcher_cls=None,
        distributed_cls=None,
    ):
        self.running = False
        self.normal = True
        self.crawler = crawler
        self.settings: Union[Dict[str, Any], Any] = crawler.settings if crawler.settings is not None else {}
        self.spider: Optional[Spider] = None
        self.downloader: Optional[DownloaderBase] = None
        self.scheduler: Optional[Scheduler] = None
        self.processor: Optional[Processor] = None
        self._start_requests_source = None
        self._start_requests_is_async = False
        self._seed_lock_key = None
        self._seed_renewal_task = None
        self._close_reason: str = 'finished'
        self._spider_closed: bool = False
        self._background_tasks: set = set()
        self._request_available = asyncio.Event()
        self._idle_since: Optional[float] = None
        self._idle_scan_counter: float = 0.0
        self._cluster_state = ClusterState()

        # 初始化配置
        self._init_configs()

        # P1 辅助组件
        self._generation_stats = GenerationStats()
        self._backpressure_ctrl = EngineBackpressureAdapter(
            max_queue_size=self.max_queue_size,
            backpressure_ratio=self.backpressure_ratio,
            strategy=self.backpressure_strategy,
            enabled=safe_get_config(self.settings, 'BACKPRESSURE_ENABLED', True, bool),
        )

        # Logger 必须先初始化，P4 组合对象（DistributedCoordinator / RequestDispatcher）
        # __init__ 里会立即读取 self.logger
        self.logger = get_logger(name=self.__class__.__name__)

        # P4 组合组件（P3-4 可配置化）：支持注入实例、注入类，或通过
        # ENGINE_DISPATCHER_CLASS / ENGINE_DISTRIBUTED_CLASS 配置类路径。
        if dispatcher_cls is None:
            dispatcher_cls = self._resolve_engine_component(
                'ENGINE_DISPATCHER_CLASS', RequestDispatcher
            )
        if distributed_cls is None:
            distributed_cls = self._resolve_engine_component(
                'ENGINE_DISTRIBUTED_CLASS', DistributedCoordinator
            )
        self._distributed = distributed or distributed_cls(self)
        self._dispatcher = dispatcher or dispatcher_cls(self)

    def _resolve_engine_component(self, settings_key: str, default_cls):
        """从 settings 解析组合组件类（完整类路径），失败回退默认。"""
        path = safe_get_config(self.settings, settings_key, None, str)
        if not path:
            return default_cls
        try:
            from crawlo.utils.misc import load_object
            return load_object(path)
        except Exception as e:
            self.logger.warning(
                f"Failed to load engine component '{settings_key}={path}': {e}, "
                f"falling back to {default_cls.__name__}"
            )
            return default_cls

    # ======================================================================
    # 工具方法 & 配置
    # ======================================================================
    def _create_background_task(self, coro):
        """创建带引用追踪的后台任务，防止 fire-and-forget 任务泄漏"""
        task = asyncio.create_task(coro)
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)
        return task

    def _init_configs(self) -> None:
        concurrency = safe_get_config(self.settings, 'CONCURRENCY', 8, int)
        self.task_manager: Optional[TaskManager] = TaskManager(concurrency)

        self.days = safe_get_config(self.settings, 'LOG_RETENTION_DAYS', 1, int)
        self.max_queue_size = safe_get_config(self.settings, 'SCHEDULER_MAX_QUEUE_SIZE', 10000, int)
        self.generation_batch_size = safe_get_config(self.settings, 'REQUEST_GENERATION_BATCH_SIZE', 10, int)
        self.generation_interval = safe_get_config(self.settings, 'REQUEST_GENERATION_INTERVAL', 0.01, float)
        self.backpressure_ratio = safe_get_config(self.settings, 'BACKPRESSURE_RATIO', 0.9, float)
        self.backpressure_strategy = safe_get_config(
            self.settings, 'BACKPRESSURE_STRATEGY', 'queue_size', str
        )
        self.enable_controlled_generation = safe_get_config(
            self.settings, 'ENABLE_CONTROLLED_REQUEST_GENERATION', False, bool
        )

        self.version = __version__

        self.checkpoint_save_on_signal = safe_get_config(
            self.settings, 'CHECKPOINT_SAVE_ON_SIGNAL', False, bool
        )

        self._worker_idle_timeout = safe_get_config(
            self.settings, 'DISTRIBUTED_WORKER_IDLE_TIMEOUT', 300, int
        )

        self._distributed_idle_xclaim_scan_interval = safe_get_config(
            self.settings, 'DISTRIBUTED_IDLE_XCLAIM_SCAN_INTERVAL', 15, int
        )
        self._distributed_idle_xclaim_min_idle = safe_get_config(
            self.settings, 'DISTRIBUTED_IDLE_XCLAIM_MIN_IDLE', 120, int
        )
        self._distributed_idle_xclaim_batch = safe_get_config(
            self.settings, 'DISTRIBUTED_IDLE_XCLAIM_BATCH', 200, int
        )

        self._cluster_state.coordinated_shutdown_enabled = safe_get_config(
            self.settings, 'DISTRIBUTED_COORDINATED_SHUTDOWN_ENABLED', True, bool
        )

        self.downloader_type = safe_get_config(self.settings, 'DOWNLOADER_TYPE')
        self.downloader_path = safe_get_config(self.settings, 'DOWNLOADER')

        self._checkpoint = CheckpointCoordinator(self.settings)

    def _get_downloader_cls(self):
        if self.downloader_type:
            try:
                from crawlo.downloader import get_downloader_class
                downloader_cls = get_downloader_class(self.downloader_type)
                self.logger.debug(f"使用下载器类型: {self.downloader_type} -> {downloader_cls.__name__}")
                return downloader_cls
            except (ImportError, ValueError) as e:
                self.logger.warning(f"无法使用下载器类型 '{self.downloader_type}': {e}，回退到默认配置")

        if not self.downloader_path:
            from crawlo.downloader import HttpXDownloader
            return HttpXDownloader

        downloader_cls = load_object(self.downloader_path)
        if not issubclass(downloader_cls, DownloaderBase):
            raise TypeError(f'下载器 {downloader_cls.__name__} 不是 DownloaderBase 的子类。')
        return downloader_cls

    def engine_start(self):
        self.running = True
        self.logger.debug(f"Crawlo框架已启动 {self.version}")

    # ======================================================================
    # 生命周期：start_spider / crawl / close_spider
    # ======================================================================
    async def start_spider(self, spider, resume=None):
        self.spider = spider
        if resume is None:
            resume = bool(safe_get_config(self.settings, 'CHECKPOINT_ENABLED', False, bool))

        self.scheduler = Scheduler.create_instance(self.crawler)
        if hasattr(self.scheduler, 'open'):
            if asyncio.iscoroutinefunction(self.scheduler.open):
                await self.scheduler.open()
            else:
                result = self.scheduler.open()
                if result is not None and asyncio.iscoroutine(result):
                    await result

        downloader_cls = self._get_downloader_cls()
        self.downloader = downloader_cls(self.crawler)
        if hasattr(self.downloader, 'open'):
            self.downloader.open()

        if hasattr(self.crawler, '_resource_manager') and self.downloader is not None:
            from crawlo.utils.resource_manager import ResourceType
            self.crawler._resource_manager.register(
                self.downloader,
                lambda d: d.close() if hasattr(d, 'close') else None,
                ResourceType.DOWNLOADER,
                name=f"downloader.{downloader_cls.__name__}"
            )
            self.logger.debug(f"Downloader registered to resource manager: {downloader_cls.__name__}")

        self.processor = Processor(self.crawler)
        if hasattr(self.processor, 'open'):
            await self.processor.open()
        if not hasattr(self.crawler, 'extension') or not self.crawler.extension:
            self.crawler.extension = self.crawler._create_extension()

        self.engine_start()
        await self._init_cluster()

        checkpoint_resumed = False
        if resume:
            checkpoint_resumed = await self._checkpoint.resume_from_checkpoint(spider, self.scheduler)
            if checkpoint_resumed:
                self._start_requests_source = None

        if not checkpoint_resumed:
            is_seed_generator = True
            run_mode = safe_get_config(self.settings, 'RUN_MODE', 'standalone')
            if run_mode == 'distributed' and self._cluster_state.redis:
                project = safe_get_config(self.settings, 'PROJECT_NAME', 'crawlo')
                spider_name = safe_get_config(self.settings, 'SPIDER_NAME', 'default')
                seed_lock_key = f"crawlo:{project}:{spider_name}:seed:generator"

                acquired = await self._try_acquire_seed_lock_atomic(
                    seed_lock_key, project, spider_name
                )

                if not acquired:
                    is_seed_generator = False
                    self._start_requests_source = None
                    self.logger.info(
                        f"Worker {self._cluster_state.worker_id}: another Worker is generating "
                        f"seed URLs, skipping start_requests"
                    )
                else:
                    self._seed_lock_key = seed_lock_key
                    self._seed_renewal_task = asyncio.create_task(self._renew_seed_lock())

            if is_seed_generator:
                try:
                    source, is_async = await resolve_start_requests(spider, self.logger)
                    self._start_requests_source = source
                    self._start_requests_is_async = is_async
                    self.logger.debug("start_requests 解析成功")
                except Exception as e:
                    self.logger.error(f"解析 start_requests 失败: {e}")
                    import traceback
                    self.logger.error(traceback.format_exc())

        await self._open_spider()

    async def crawl(self):
        """智能请求生成 + 背压控制的主爬取流程"""
        generation_task = self._setup_generation()
        await self._start_cluster_tasks()
        self._request_available.set()

        try:
            await self._run_main_loop()
        finally:
            await self._cleanup_crawl(generation_task)

    def _setup_generation(self):
        if self._start_requests_source is not None and self.enable_controlled_generation:
            self.logger.debug("创建受控请求生成任务")
            return asyncio.create_task(self._controlled_request_generation())
        self.logger.debug("创建传统请求生成任务")
        return asyncio.create_task(self._traditional_request_generation())

    async def _cleanup_crawl(self, generation_task):
        """crawl() 退出后的清理工作"""
        self.running = False

        if self._seed_renewal_task and not self._seed_renewal_task.done():
            self._seed_renewal_task.cancel()
            try:
                await self._seed_renewal_task
            except asyncio.CancelledError:
                pass
        self._seed_renewal_task = None

        if generation_task and not generation_task.done():
            generation_task.cancel()
            try:
                await generation_task
            except asyncio.CancelledError:
                self.logger.debug("Generation task cancelled")
            except Exception as e:
                self.logger.debug(f"Generation task completed with error: {e}")

        reason = self._close_reason
        if reason != 'shutdown':
            process = getattr(self.crawler, '_process', None) if self.crawler else None
            if process is not None:
                try:
                    reason = 'shutdown' if process._shutdown_requested else reason
                except Exception as e:
                    self.logger.debug(f"Failed to read process shutdown flag: {e}")

        try:
            await self.close_spider(reason=reason)
        except asyncio.CancelledError:
            self.logger.debug("close_spider cancelled")

    async def _open_spider(self):
        self._create_background_task(self.crawler.subscriber.notify(CrawlerEvent.SPIDER_OPENED))
        await self.crawl()

    # ======================================================================
    # 请求级处理（_crawl / _fetch）
    # ======================================================================
    async def _crawl(self, request):
        async def crawl_task():
            start_time = time.time()
            try:
                outputs = await self._fetch(request)
                response_time = time.time() - start_time
                if self.task_manager:
                    self.task_manager.record_response_time(response_time)
                depth = getattr(request, 'meta', {}).get('depth', 0)
                page_type = '详情' if isinstance(depth, int) and depth > 1 else '列表'
                self.logger.debug(
                    f"[{page_type}] {request.url} ({response_time:.2f}s)"
                )
                if outputs and not isinstance(outputs, Failure):
                    await self._handle_spider_output(outputs, request)

                await _ack_message(request, self, success=True)

            except asyncio.CancelledError:
                await _ack_message(request, self, success=False)
                raise
            except Exception as e:
                self.logger.error(
                    f"处理请求失败: {getattr(request, 'url', 'Unknown URL')} - {type(e).__name__}: {e}",
                    exc_info=True
                )
                if hasattr(self.crawler, 'stats'):
                    self.crawler.stats.inc_value('downloader/exception_count')
                    self.crawler.stats.inc_value(f'downloader/exception_type_count/{type(e).__name__}')
                    if hasattr(request, 'url'):
                        self.crawler.stats.inc_value('downloader/failed_urls_count')

                errback = getattr(request, 'errback', None)
                if errback and callable(errback):
                    try:
                        errback_result = await common_call(errback, Failure(e, request=request))
                        if errback_result is not None:
                            await self._handle_errback_output(errback_result, request)
                    except Exception as errback_error:
                        self.logger.error(
                            f"errback 执行失败 [{getattr(request, 'url', 'Unknown URL')}]: "
                            f"{type(errback_error).__name__}: {errback_error}"
                        )

                await _ack_message(request, self, success=False, error=e)

                if ErrorClassifier.is_critical(e):
                    self.logger.critical(f"遇到关键错误，停止爬虫: {type(e).__name__}: {e}")
                    raise

                return None

        if self.task_manager:
            coro = crawl_task()
            try:
                await self.task_manager.create_task_nowait(coro)
            except asyncio.CancelledError:
                if not getattr(self, '_cancel_logged', False):
                    self.logger.info("爬取任务被取消")
                    self._cancel_logged = True
                coro.close()
                raise
            except Exception as e:
                self.logger.error(f"创建爬取任务时发生错误: {e}")
                coro.close()

    async def _fetch(self, request):
        if self.spider is None:
            self.logger.warning(
                f"_fetch called but engine.spider is None ({request.url if request else 'n/a'}), "
                "skip callback processing, return None"
            )
            return None
        if self.downloader is None:
            self.logger.error("Downloader is not initialized, cannot fetch request")
            return Failure(request, RuntimeError("Downloader not available"))
        _response = await self.downloader.fetch(request)
        if _response is None:
            self.logger.warning(
                f"Downloader returned None for {request.url}, skipping errback"
            )
            return Failure(
                request,
                RuntimeError(f"Downloader returned empty response for {request.url}")
            )
        output = await process_callback_output(
            self.spider,
            request.callback or self.spider.parse,
            request.cb_kwargs,
            _response,
            self.logger
        )
        return output

    # ======================================================================
    # Request 入队 / 获取（小工具，不移出）
    # ======================================================================
    async def enqueue_request(self, start_request):
        if self.scheduler is not None:
            await self._schedule_request(start_request)
        else:
            self.logger.warning("Scheduler 未初始化，无法入队请求")

    async def _schedule_request(self, request):
        if self.scheduler is not None and await self.scheduler.enqueue_request(request):
            self._request_available.set()
            if self.crawler is not None and self.crawler.spider is not None:
                self._create_background_task(self.crawler.subscriber.notify(CrawlerEvent.REQUEST_SCHEDULED, request, self.crawler.spider))

    async def _get_next_request(self):
        if self.scheduler is not None:
            return await self.scheduler.next_request()
        return None

    # ======================================================================
    # 薄代理：DistributedCoordinator
    # ======================================================================
    async def _check_control_state(self) -> bool:
        return await self._distributed.check_control_state()

    async def _handle_distributed_idle(self, idle_count: int) -> bool:
        return await self._distributed.handle_distributed_idle(idle_count)

    async def _try_claim_stale_pending(self) -> int:
        return await self._distributed.try_claim_stale_pending()

    # ======================================================================
    # 薄代理：RequestDispatcher
    # ======================================================================
    async def _run_main_loop(self):
        return await self._dispatcher.run_main_loop()

    async def _dispatch_requests(self, requests, max_inflight):
        return await self._dispatcher.dispatch_requests(requests, max_inflight)

    async def _check_components_idle(self, include_background: bool = False):
        return await self._dispatcher.check_components_idle(include_background)

    async def _exit(self) -> bool:
        return await self._dispatcher.exit_fast()

    async def _check_all_idle(self) -> bool:
        return await self._dispatcher.check_all_idle()

    async def _should_exit(self, last_component_states=None):
        return await self._dispatcher.should_exit(last_component_states)

    # ======================================================================
    # close_spider（生命周期，保留）
    # ======================================================================
    async def close_spider(self, reason='finished'):
        if self._spider_closed:
            self.logger.debug("close_spider already called, skipping")
            return
        self._spider_closed = True
        self._close_reason = reason

        try:
            if reason != 'finished' and self.task_manager is not None and self.task_manager.current_task:
                self.logger.debug(f"Waiting for {len(self.task_manager.current_task)} active tasks to complete...")
                try:
                    await asyncio.gather(*self.task_manager.current_task, return_exceptions=True)
                except asyncio.CancelledError:
                    self.logger.debug("Task manager gather cancelled")
                except Exception as e:
                    self.logger.debug(f"Task manager gather completed with errors: {e}")

            if reason == 'shutdown':
                await self._checkpoint.save_checkpoint(
                    self.scheduler, self.spider,
                    getattr(self.crawler, 'stats', None),
                    self.checkpoint_save_on_signal,
                )

            if reason == 'finished':
                await self._checkpoint.clear_checkpoint(self.spider)

            if self.processor is not None and hasattr(self.processor, 'pipelines'):
                await self.processor.pipelines.close()

            try:
                from crawlo.logging import LogManager
                LogManager().cleanup_old_logs(days=self.days)
            except Exception as e:
                self.logger.error(f"Failed to clean up expired log files: {e}")

            if self.downloader is not None and hasattr(self.downloader, 'close'):
                try:
                    close_result = self.downloader.close()
                    if asyncio.iscoroutine(close_result):
                        close_task = asyncio.ensure_future(close_result)
                        try:
                            await asyncio.wait_for(close_task, timeout=5.0)
                        except asyncio.TimeoutError:
                            close_task.cancel()
                            try:
                                await close_task
                            except asyncio.CancelledError:
                                pass
                            raise
                except asyncio.TimeoutError:
                    self.logger.warning("下载器关闭超时，强制清理资源")
                except Exception as e:
                    self.logger.debug(f"下载器关闭时发生错误: {e}")

            await self._shutdown_cluster()

            if self.scheduler is not None:
                try:
                    close_task = asyncio.ensure_future(self.scheduler.close())
                    try:
                        await asyncio.wait_for(close_task, timeout=5.0)
                    except asyncio.TimeoutError:
                        close_task.cancel()
                        try:
                            await close_task
                        except asyncio.CancelledError:
                            pass
                        raise
                except asyncio.TimeoutError:
                    self.logger.warning("调度器关闭超时")
                except Exception as e:
                    self.logger.debug(f"调度器关闭时发生错误: {e}")
        except (Exception, asyncio.CancelledError):
            self._spider_closed = False
            try:
                if self.crawler is not None and self.crawler.subscriber is not None:
                    from crawlo.event import CrawlerEvent
                    asyncio.ensure_future(
                        self.crawler.subscriber.notify(
                            CrawlerEvent.SPIDER_CLOSED, reason='error'
                        )
                    )
            except Exception as e:
                self.logger.debug(f"Failed to notify SPIDER_CLOSED: {e}")
            raise

    # ======================================================================
    # Public API
    # ======================================================================
    def get_generation_stats(self) -> dict:
        return {
            **self._generation_stats.to_dict(),
            'queue_size': safe_queue_size(self.scheduler),
            'active_tasks': len(self.task_manager.current_task) if self.task_manager else 0,
            'backpressure_stats': self._backpressure_ctrl.get_stats(),
        }
