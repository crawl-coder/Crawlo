#!/usr/bin/python
# -*- coding:UTF-8 -*-
import asyncio
import sys
import time
from inspect import iscoroutine, isasyncgen, isgenerator
from typing import Optional, Callable, Any, Union, Dict, Iterator

from crawlo import Request, Item
from crawlo.spider import Spider
from crawlo.event import CrawlerEvent
from crawlo.project import common_call
from crawlo.core.failure import Failure
from crawlo.logging import get_logger
from crawlo.exceptions import OutputError
from crawlo.core.error_types import ErrorClassifier
from crawlo.core.task_manager import TaskManager
from crawlo.downloader import DownloaderBase
from crawlo.core.processor import Processor
from crawlo.core.scheduler import Scheduler
from crawlo.checkpoint import CheckpointManager
from crawlo.core.engine_helpers import GenerationStats, EngineBackpressureAdapter
from crawlo.core.engine_generation import RequestGenerationMixin
from crawlo.core.engine_generation import resolve_start_requests, process_callback_output
from crawlo.utils.misc import load_object
from crawlo.utils.misc import safe_get_config
from crawlo.__version__ import __version__
from crawlo.queue.task_tracker import TaskTracker, TaskResult
from crawlo.core.engine_cluster import ClusterMixin, _ack_message


class Engine(RequestGenerationMixin, ClusterMixin):
    
    # 关键错误类型配置，从 error_types 模块导入
    CRITICAL_EXCEPTIONS = ErrorClassifier.CRITICAL_EXCEPTIONS

    def __init__(self, crawler):
        self.running = False
        self.normal = True
        self.crawler = crawler
        self.settings: Union[Dict[str, Any], Any] = crawler.settings if crawler.settings is not None else {}
        self.spider: Optional[Spider] = None
        self.downloader: Optional[DownloaderBase] = None
        self.scheduler: Optional[Scheduler] = None
        self.processor: Optional[Processor] = None
        self._start_requests_source = None  # Original generator (sync gen / async gen / iter)
        self._start_requests_is_async = False  # Whether it's an async generator
        self._seed_lock_key = None  # 种子锁 key（分布式模式）
        self._seed_renewal_task = None  # 种子锁续期任务
        self._close_reason: str = 'finished'  # Close reason: finished / shutdown
        self._spider_closed: bool = False  # Prevent duplicate close_spider calls
        self._background_tasks: set = set()  # Track fire-and-forget tasks to prevent leaks
        self._request_available = asyncio.Event()  # 事件驱动：新请求可用时唤醒主循环
        self._idle_since: Optional[float] = None  # 空闲起始时间（使用 time.monotonic()，分布式模式用）
        
        # Initialize configurations
        self._init_configs()
        
        # Initialize helper utilities
        self._generation_stats = GenerationStats()
        self._backpressure_ctrl = EngineBackpressureAdapter(
            max_queue_size=self.max_queue_size,
            backpressure_ratio=self.backpressure_ratio,
            strategy=self.backpressure_strategy,
        )

        # Cluster components (distributed only)
        self._cluster_registry = None       # WorkerRegistry
        self._cluster_heartbeat = None      # HeartbeatDaemon
        self._cluster_failover = None       # FailoverManager
        self._cluster_lock = None           # DistributedLock (for failover)
        self._cluster_progress = None       # ProgressAggregator
        self._cluster_monitor = None        # ClusterMonitor
        self._cluster_rate_limiter = None   # DistributedRateLimiter
        self._cluster_messenger = None      # ClusterMessenger
        self._cluster_dynamic_config = None # DynamicConfig
        self._cluster_worker_id = None      # Worker ID
        self._cluster_heartbeat_task = None # asyncio.Task
        self._cluster_failover_task = None  # asyncio.Task
        self._cluster_paused = False        # pause flag from control channel
        self._task_tracker = None           # TaskTracker (for ACK)

        # Leader coordinated shutdown
        self._cluster_redis = None              # Redis client (shared across cluster components)
        self._leader_lock = None                # DistributedLock for leader election (atomic SET NX EX + Lua release)
        self._leader_shutdown_task = None       # asyncio.Task for leader shutdown loop
        self._coordinated_shutdown_enabled = True  # Default from settings (overridden by _init_configs)

        self.logger = get_logger(name=self.__class__.__name__)
    
    def _create_background_task(self, coro):
        """创建带引用追踪的后台任务，防止 fire-and-forget 任务泄漏"""
        task = asyncio.create_task(coro)
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)
        return task
    
    def _init_configs(self) -> None:
        """
        Initialize all configurations from settings
        
        Centralized configuration extraction for better maintainability
        """
        # Concurrency control configuration
        concurrency = safe_get_config(self.settings, 'CONCURRENCY', 8, int)
        self.task_manager: Optional[TaskManager] = TaskManager(concurrency)
        
        # Request generation configuration
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
        
        # Version configuration (directly from __version__.py, not from config file)
        self.version = __version__
        
        # Checkpoint configuration
        self.checkpoint_save_on_signal = safe_get_config(
            self.settings, 'CHECKPOINT_SAVE_ON_SIGNAL', True, bool
        )
        
        # Distributed worker configuration
        self._worker_idle_timeout = safe_get_config(
            self.settings, 'DISTRIBUTED_WORKER_IDLE_TIMEOUT', 300, int
        )

        # Coordinated shutdown via leader election
        self._coordinated_shutdown_enabled = safe_get_config(
            self.settings, 'DISTRIBUTED_COORDINATED_SHUTDOWN_ENABLED', True, bool
        )

        # Downloader configuration
        self.downloader_type = safe_get_config(self.settings, 'DOWNLOADER_TYPE')
        self.downloader_path = safe_get_config(self.settings, 'DOWNLOADER')

    def _get_downloader_cls(self):
        """
        获取下载器类
        
        Returns:
            Type[DownloaderBase]: 下载器类
        """
        # 方式1: 使用 DOWNLOADER_TYPE 配置（推荐）
        if self.downloader_type:
            try:
                from crawlo.downloader import get_downloader_class
                downloader_cls = get_downloader_class(self.downloader_type)
                self.logger.debug(f"使用下载器类型: {self.downloader_type} -> {downloader_cls.__name__}")
                return downloader_cls
            except (ImportError, ValueError) as e:
                self.logger.warning(f"无法使用下载器类型 '{self.downloader_type}': {e}，回退到默认配置")
        
        # 方式2: 使用 DOWNLOADER 完整类路径（兼容旧版本）
        # 如果没有配置下载器，使用默认下载器
        if not self.downloader_path:
            from crawlo.downloader import HttpXDownloader
            return HttpXDownloader
            
        downloader_cls = load_object(self.downloader_path)
        if not issubclass(downloader_cls, DownloaderBase):
            raise TypeError(f'下载器 {downloader_cls.__name__} 不是 DownloaderBase 的子类。')
        return downloader_cls

    def engine_start(self):
        self.running = True
        # 使用初始化时获取的版本配置
        self.logger.debug(f"Crawlo框架已启动 {self.version}")

    async def start_spider(self, spider, resume=True):
        self.spider = spider

        self.scheduler = Scheduler.create_instance(self.crawler)
        if hasattr(self.scheduler, 'open'):
            if asyncio.iscoroutinefunction(self.scheduler.open):
                await self.scheduler.open()
            else:
                # 确保同步方法被正确调用
                result = self.scheduler.open()
                # 只有在result是协程时才await
                if result is not None and asyncio.iscoroutine(result):
                    await result

        downloader_cls = self._get_downloader_cls()
        self.downloader = downloader_cls(self.crawler)
        if hasattr(self.downloader, 'open'):
            self.downloader.open()
        
        # 注册下载器到资源管理器
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
        # 在处理器初始化之后初始化扩展管理器，确保日志输出顺序正确
        # 中间件 -> 管道 -> 扩展
        if not hasattr(self.crawler, 'extension') or not self.crawler.extension:
            self.crawler.extension = self.crawler._create_extension()

        # 启动引擎
        self.engine_start()

        # 初始化集群组件（distributed 模式）
        await self._init_cluster()

        # 检查点恢复：如果存在检查点且 resume=True，从检查点恢复
        checkpoint_resumed = False
        if resume:
            checkpoint_resumed = await self._try_resume_from_checkpoint(spider)

        if not checkpoint_resumed:
            # 正常流程：从 start_requests 开始（流式，不物化）
            # 分布式模式：SETNX 选举种子生成器 + 锁续期 + 崩溃恢复
            is_seed_generator = True
            run_mode = safe_get_config(self.settings, 'RUN_MODE', 'standalone')
            if run_mode == 'distributed' and self._cluster_redis:
                project = safe_get_config(self.settings, 'PROJECT_NAME', 'crawlo')
                spider_name = safe_get_config(self.settings, 'SPIDER_NAME', 'default')
                seed_lock_key = f"crawlo:{project}:{spider_name}:seed:generator"

                # 检查是否有死锁（持有者已不在 Registry 中）
                lock_owner = await self._cluster_redis.get(seed_lock_key)
                if lock_owner:
                    owner_str = lock_owner.decode() if isinstance(lock_owner, bytes) else str(lock_owner)
                    if self._cluster_registry:
                        owner_info = await self._cluster_registry.get_worker_info(owner_str)
                        if not owner_info:
                            await self._cluster_redis.delete(seed_lock_key)
                            self.logger.info(f"Cleared stale seed lock from dead worker: {owner_str}")

                # 尝试成为种子生成器（锁 TTL=120s，续期任务防止长时生成期间过
                acquired = await self._cluster_redis.set(
                    seed_lock_key, self._cluster_worker_id, nx=True, ex=120
                )
                if not acquired:
                    is_seed_generator = False
                    self._start_requests_source = None
                    self.logger.info(
                        f"Worker {self._cluster_worker_id}: another Worker is generating "
                        f"seed URLs, skipping start_requests"
                    )
                else:
                    # 启动锁续期任务：每 60 秒延长 TTL
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
        """创建请求生成后台任务"""
        if self._start_requests_source is not None and self.enable_controlled_generation:
            self.logger.debug("创建受控请求生成任务")
            return asyncio.create_task(self._controlled_request_generation())
        self.logger.debug("创建传统请求生成任务")
        return asyncio.create_task(self._traditional_request_generation())

    async def _run_main_loop(self):
        """主爬取循环：获取请求 → 流控 → 派发 → 空闲检测"""
        loop_count = 0
        last_exit_check = 0
        last_component_states = None
        batch_size = max(self.task_manager._concurrency_limit, 10)
        idle_count = 0
        max_inflight = self.task_manager._concurrency_limit + 3
        exit_check_interval, min_ci, max_ci = 10, 5, 20

        while self.running:
            loop_count += 1

            if self._cluster_messenger and self._cluster_dynamic_config:
                if not await self._check_control_state():
                    break
                if self._cluster_paused:
                    await asyncio.sleep(0.5)
                    continue

            # 批量获取请求
            requests = []
            for _ in range(batch_size):
                if request := await self._get_next_request():
                    requests.append(request)
                else:
                    break

            if requests:
                idle_count = 0
                await self._dispatch_requests(requests, max_inflight)
                exit_check_interval = min(exit_check_interval + 1, max_ci)
            else:
                idle_count += 1
                run_mode = safe_get_config(self.settings, 'RUN_MODE', 'standalone')
                if run_mode == 'distributed' and self._start_requests_source is None:
                    if await self._handle_distributed_idle(idle_count):
                        break
                    continue

                if idle_count == 1:
                    should_exit, last_component_states = await self._should_exit(last_component_states)
                    if should_exit:
                        await asyncio.sleep(0.001)
                        if await self._check_all_idle():
                            break
                    last_exit_check = loop_count
                exit_check_interval = max(exit_check_interval - 1, min_ci)

            if loop_count - last_exit_check >= exit_check_interval:
                should_exit, last_component_states = await self._should_exit(last_component_states)
                if should_exit:
                    break
                last_exit_check = loop_count

            if requests:
                await asyncio.sleep(0.000001)
            else:
                try:
                    await asyncio.wait_for(
                        self._request_available.wait(),
                        timeout=0.5 if idle_count > 10 else 0.1
                    )
                    self._request_available.clear()
                except asyncio.TimeoutError:
                    pass

        self.logger.debug(f"主爬取循环结束，总共执行了 {loop_count} 次")

    async def _check_control_state(self) -> bool:
        """检查集群控制状态，返回 True 继续运行"""
        try:
            state = await self._cluster_dynamic_config.get_control_state()
            if state == "paused":
                self._cluster_paused = True
            elif state == "running":
                self._cluster_paused = False
            elif state == "shutdown":
                self.logger.warning("Persistent shutdown state detected, exiting")
                self.running = False
                return False
        except Exception:
            pass
        return True

    async def _dispatch_requests(self, requests, max_inflight):
        """派发请求，控制并发流控"""
        self._request_available.clear()
        for req in requests:
            if len(self._background_tasks) >= max_inflight:
                if not getattr(self, '_fc_logged', False):
                    self.logger.debug(
                        f"[流控] 在途={len(self._background_tasks)}/{max_inflight}，等待释放后派发"
                    )
                    self._fc_logged = True
                while len(self._background_tasks) >= max_inflight:
                    await asyncio.sleep(0.01)
            else:
                self._fc_logged = False
            self._create_background_task(self._crawl(req))

    async def _handle_distributed_idle(self, idle_count: int) -> bool:
        """分布式模式下的空闲处理，返回 True 表示应退出"""
        if self._worker_idle_timeout > 0:
            if self._idle_since is not None:
                remaining = self._worker_idle_timeout - (time.monotonic() - self._idle_since)
            else:
                remaining = self._worker_idle_timeout
            if remaining <= 0:
                self.logger.info(f"Worker idle for {self._worker_idle_timeout}s, exiting")
                return True
        else:
            remaining = 30.0

        request = await self.scheduler.next_request_blocking(
            timeout=min(30.0, max(1.0, remaining))
        )
        if request:
            self._idle_since = None
            self._create_background_task(self._crawl(request))
        else:
            if self._idle_since is None:
                self._idle_since = time.monotonic()
            if self._worker_idle_timeout > 0:
                if time.monotonic() - self._idle_since >= self._worker_idle_timeout:
                    self.logger.info(
                        f"Distributed worker idle for {self._worker_idle_timeout}s, exiting"
                    )
                    return True
        return False

    async def _renew_seed_lock(self):
        """种子锁续期任务：每 60 秒延长锁 TTL，防止长时种子生成期间锁过期"""
        try:
            while self.running and self._seed_lock_key:
                await asyncio.sleep(60)
                if self._cluster_redis and self._seed_lock_key:
                    await self._cluster_redis.expire(self._seed_lock_key, 120)
        except asyncio.CancelledError:
            pass

    async def _cleanup_crawl(self, generation_task):
        """crawl() 退出后的清理工作"""
        self.running = False

        # 停止种子锁续期
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
                except Exception:
                    pass

        try:
            await self.close_spider(reason=reason)
        except asyncio.CancelledError:
            self.logger.debug("close_spider cancelled")

    async def _open_spider(self):
        self._create_background_task(self.crawler.subscriber.notify(CrawlerEvent.SPIDER_OPENED))
        # 直接调用crawl方法而不是创建任务，确保等待完成
        await self.crawl()

    async def _crawl(self, request):
        async def crawl_task():
            start_time = time.time()
            _last_error = None  # Capture error for distributed NACK
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

                # Distributed ACK: success
                await _ack_message(request, self, success=True)

            except asyncio.CancelledError:
                await _ack_message(request, self, success=False)
                raise
            except Exception as e:
                _last_error = e
                self.logger.error(
                    f"处理请求失败: {getattr(request, 'url', 'Unknown URL')} - {type(e).__name__}: {e}",
                    exc_info=True
                )
                if hasattr(self.crawler, 'stats'):
                    self.crawler.stats.inc_value('downloader/exception_count')
                    self.crawler.stats.inc_value(f'downloader/exception_type_count/{type(e).__name__}')
                    if hasattr(request, 'url'):
                        self.crawler.stats.inc_value(f'downloader/failed_urls_count')

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

                # Distributed NACK: failure
                await _ack_message(request, self, success=False, error=e)

                if ErrorClassifier.is_critical(e):
                    self.logger.critical(f"遇到关键错误，停止爬虫: {type(e).__name__}: {e}")
                    raise

                return None

        # 使用异步任务创建，遵守并发限制
        if self.task_manager:
            coro = crawl_task()
            try:
                # 创建后台任务但不等待完成（fire-and-forget），
                # 让多个浏览器请求真正并发执行。
                # task_manager 的信号量控制并发上限，
                # done_callback 负责释放信号量。
                await self.task_manager.create_task_nowait(coro)
            except asyncio.CancelledError:
                # 只在第一次取消时打印日志，避免重复
                if not getattr(self, '_cancel_logged', False):
                    self.logger.info("爬取任务被取消")
                    self._cancel_logged = True
                # 确保协程被正确关闭，避免 RuntimeWarning
                coro.close()
                # 重新抛出CancelledError以便调用者可以正确处理
                raise
            except Exception as e:
                self.logger.error(f"创建爬取任务时发生错误: {e}")
                # 确保协程被正确关闭
                coro.close()

    async def _fetch(self, request):
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

    async def enqueue_request(self, start_request):
        if self.scheduler is not None:
            await self._schedule_request(start_request)
        else:
            self.logger.warning("⚠️ Scheduler 未初始化，无法入队请求")

    async def _schedule_request(self, request):
        if self.scheduler is not None and await self.scheduler.enqueue_request(request):
            self._request_available.set()  # 唤醒主循环
            if self.crawler is not None and self.crawler.spider is not None:
                self._create_background_task(self.crawler.subscriber.notify(CrawlerEvent.REQUEST_SCHEDULED, request, self.crawler.spider))

    async def _get_next_request(self):
        if self.scheduler is not None:
            return await self.scheduler.next_request()
        return None

    async def _handle_spider_output(self, outputs, parent_request=None):
        """处理 spider 回调输出，自动为子 Request 传播 depth
        
        框架级 depth 传播机制：
        - 从 parent_request 获取当前 depth（默认 0）
        - 子 Request 的 depth 自动设为 parent_depth + 1
        - 配合 DEPTH_PRIORITY 配置，实现广度优先或深度优先策略
        
        Args:
            outputs: spider 回调的输出（异步生成器）
            parent_request: 产生此输出的原始请求（用于获取 depth）
        """
        # 获取父请求的 depth
        parent_depth = 0
        if parent_request is not None and hasattr(parent_request, 'meta'):
            parent_depth = parent_request.meta.get('depth', 0)
        
        if self.processor is None:
            return
        async for spider_output in outputs:
            if isinstance(spider_output, Request):
                # 框架级 depth 传播：子请求 depth = 父请求 depth + 1
                # 仅在子请求未手动设置 depth 时自动注入
                if 'depth' not in spider_output.meta:
                    spider_output.meta['depth'] = parent_depth + 1
                await self.processor.enqueue(spider_output)
            elif isinstance(spider_output, Item):
                await self.processor.enqueue(spider_output)
            elif isinstance(spider_output, Exception):
                if self.crawler is not None and self.spider is not None:
                    self._create_background_task(
                        self.crawler.subscriber.notify(CrawlerEvent.SPIDER_ERROR, spider_output, self.spider)
                    )
                raise spider_output
            else:
                raise OutputError(f'{type(self.spider)} must return `Request` or `Item`.')

    async def _handle_errback_output(self, result, parent_request=None):
        """
        处理 errback 的返回值，包装后委托给 _handle_spider_output。

        支持与 callback 相同的返回类型：
        - 单个 Request / Item
        - 列表 / 元组
        - 异步生成器
        - 同步生成器
        - 协程
        """
        if isinstance(result, (Request, Item)):
            async def _gen():
                yield result
            await self._handle_spider_output(_gen(), parent_request)
        elif isinstance(result, (list, tuple)):
            async def _gen():
                for item in result:
                    if isinstance(item, (Request, Item)):
                        yield item
            await self._handle_spider_output(_gen(), parent_request)
        elif isasyncgen(result):
            await self._handle_spider_output(result, parent_request)
        elif isgenerator(result):
            async def _wrap_sync_gen():
                for item in result:
                    if isinstance(item, (Request, Item)):
                        yield item
            await self._handle_spider_output(_wrap_sync_gen(), parent_request)
        elif iscoroutine(result):
            awaited = await result
            if awaited is not None:
                await self._handle_errback_output(awaited, parent_request)
        else:
            self.logger.warning(
                f"errback returned unexpected type {type(result).__name__}, ignored"
            )

    async def _check_components_idle(self, include_background: bool = False) -> tuple[bool, bool, bool, bool, bool]:
        """统一检查各组件是否空闲（消除 _exit / _should_exit 代码重复）
        
        Returns:
            (scheduler_idle, downloader_idle, task_manager_done, processor_idle, background_tasks_done)
        """
        scheduler_idle = False
        downloader_idle = False
        task_manager_done = False
        processor_idle = False
        background_tasks_done = False
        
        if self.scheduler is not None:
            scheduler_idle = await self.scheduler.async_idle() if hasattr(self.scheduler, 'async_idle') else self.scheduler.idle()
        if self.downloader is not None:
            downloader_idle = self.downloader.idle()
        if self.task_manager is not None:
            task_manager_done = self.task_manager.all_done()
        if self.processor is not None:
            processor_idle = await self.processor.idle_async()
        if include_background:
            background_tasks_done = len(self._background_tasks) == 0
        
        return scheduler_idle, downloader_idle, task_manager_done, processor_idle, background_tasks_done

    async def _exit(self):
        """快速退出检查（4 组件，不含 background_tasks）"""
        s, d, t, p, _ = await self._check_components_idle(include_background=False)
        return s and d and t and p

    async def _check_all_idle(self) -> bool:
        """二次确认所有组件是否仍然空闲（用于瞬时空闲误判）"""
        return await self._exit()

    async def _should_exit(self, last_component_states=None) -> tuple[bool, tuple]:
        """检查是否应该退出（5 组件 + start_requests 判断）
        
        standalone / auto 模式：队列空 + 所有组件空闲 → 正常退出
        distributed 模式：不因队列空退出，由 BZPOPMIN 超时 + idle_timeout 决定
        
        注意：auto 模式即使检测到 Redis 并切换为 Redis 队列，
             仍然按单机逻辑退出（auto 只是根据环境自动选队列类型，不是常驻 Worker）

        Args:
            last_component_states: 上次的组件状态元组，用于减少冗余日志
            
        Returns:
            tuple: (should_exit, current_states)
        """
        # 分布式模式不因"组件空闲"退出，由 BZPOPMIN 超时 + idle_timeout 决定
        # 如果将来 _should_exit 增加致命错误等退出条件，需要细化判断，仅跳过"队列空"相关条件
        run_mode = safe_get_config(self.settings, 'RUN_MODE', 'standalone')
        if run_mode == 'distributed':
            return False, None

        if self._start_requests_source is None:
            s, d, t, p, bg = await self._check_components_idle(include_background=True)
            current_states = (s, d, t, p, bg)
            
            if current_states != last_component_states:
                self.logger.debug(
                    f"组件状态变化 - Scheduler: {s}, "
                    f"Downloader: {d}, TaskManager: {t}, "
                    f"Processor: {p}, BackgroundTasks: {bg}"
                )
            
            if s and d and t and p and bg:
                self.logger.info("All components are idle, preparing to exit")
                return True, current_states
        else:
            self.logger.debug("start_requests 不为 None，不退出")
            current_states = None
        
        return False, current_states

    async def close_spider(self, reason='finished'):
        # 幂等保护：防止 close_spider 被重复调用
        if self._spider_closed:
            self.logger.debug("close_spider already called, skipping")
            return
        self._spider_closed = True
        self._close_reason = reason

        try:
            # 仅在非正常退出时等待活跃任务完成
            if reason != 'finished' and self.task_manager is not None and self.task_manager.current_task:
                self.logger.debug(f"Waiting for {len(self.task_manager.current_task)} active tasks to complete...")
                try:
                    await asyncio.gather(*self.task_manager.current_task, return_exceptions=True)
                except asyncio.CancelledError:
                    self.logger.debug("Task manager gather cancelled")
                except Exception as e:
                    self.logger.debug(f"Task manager gather completed with errors: {e}")
            
            # 检查点保存：Ctrl+C 触发的关闭时保存状态
            if reason == 'shutdown':
                await self._save_checkpoint()
            
            # 正常完成时清除检查点
            if reason == 'finished':
                await self._clear_checkpoint()
            
            # 关闭 pipeline（刷新批量数据、清理资源）
            if self.processor is not None and hasattr(self.processor, 'pipelines'):
                await self.processor.pipelines.close()
            
            # 清理过期日志文件（默认 3 天）
            await self._cleanup_old_logs()
            
            # 关闭下载器（带超时保护，超时后取消内部协程防止资源泄漏）
            if self.downloader is not None and hasattr(self.downloader, 'close'):
                try:
                    close_result = self.downloader.close()
                    # 如果是协程，使用超时等待
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
                            raise  # 重新抛给外层 except 处理
                except asyncio.TimeoutError:
                    self.logger.warning("下载器关闭超时，强制清理资源")
                except Exception as e:
                    self.logger.debug(f"下载器关闭时发生错误: {e}")
            
            # 关闭集群组件（heartbeat + failover + deregister）
            await self._shutdown_cluster()

            # 关闭调度器（带超时保护，超时后取消内部协程防止资源泄漏）
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
                        raise  # 重新抛给外层 except 处理
                except asyncio.TimeoutError:
                    self.logger.warning("调度器关闭超时")
                except Exception as e:
                    self.logger.debug(f"调度器关闭时发生错误: {e}")
        except (Exception, asyncio.CancelledError):
            # 清理失败，重置标志允许重试
            # 同时捕获 CancelledError（Python 3.9+ 中为 BaseException 子类）
            self._spider_closed = False
            raise
    
    async def _cleanup_old_logs(self):
        """清理过期日志文件"""
        try:
            from crawlo.logging import LogManager
            
            log_manager = LogManager()
            deleted = log_manager.cleanup_old_logs(days=self.days)
            
            if deleted > 0:
                self.logger.info(f"Cleaned up {deleted} expired log files (>{self.days} days)")
        except Exception as e:
            self.logger.error(f"Failed to clean up expired log files: {e}")
    
    async def _try_resume_from_checkpoint(self, spider) -> bool:
        """尝试从检查点恢复爬取状态
        
        Args:
            spider: 爬虫实例
            
        Returns:
            bool: 是否成功从检查点恢复
        """
        try:
            # CheckpointManager 已在顶部导入
            checkpoint_mgr = CheckpointManager(spider.name, self.settings)
            if not checkpoint_mgr.enabled or not await checkpoint_mgr.has_checkpoint():
                return False
            
            checkpoint = await checkpoint_mgr.load()
            if checkpoint is None:
                return False
            
            # 恢复请求到调度器
            requests_data = checkpoint.get('requests', [])
            restored_count = 0
            for req_data in requests_data:
                try:
                    request = checkpoint_mgr.restore_request(req_data, spider)
                    if request and self.scheduler is not None:
                        # 设置 dont_filter=True 避免被过滤器拦截
                        request.dont_filter = True
                        await self.scheduler.enqueue_request(request)
                        restored_count += 1
                except Exception as e:
                    self.logger.debug(f"Failed to restore request: {e}")
            
            # 恢复去重指纹
            fingerprints = checkpoint.get('fingerprints', set())
            if fingerprints and self.scheduler is not None:
                checkpoint_mgr.restore_fingerprints(fingerprints, self.scheduler)
            
            # 跳过 start_requests（检查点中已包含未完成的请求）
            self._start_requests_source = None
            
            self.logger.info(
                f"Resumed from checkpoint: {restored_count}/{len(requests_data)} requests restored, "
                f"{len(fingerprints)} fingerprints recovered"
            )
            return True
            
        except Exception as e:
            self.logger.warning(f"Failed to resume from checkpoint: {e}")
            return False
    
    async def _save_checkpoint(self):
        """保存检查点"""
        try:
            # CheckpointManager 已在顶部导入
            spider_name = self.spider.name if self.spider else 'unknown'
            checkpoint_mgr = CheckpointManager(spider_name, self.settings)
            
            if not checkpoint_mgr.enabled:
                return
            
            # 使用初始化时获取的检查点配置
            if not self.checkpoint_save_on_signal:
                return
            
            stats = getattr(self.crawler, 'stats', None)
            await checkpoint_mgr.save(self.scheduler, stats)
            
        except Exception as e:
            self.logger.warning(f"Failed to save checkpoint on shutdown: {e}")
    
    async def _clear_checkpoint(self):
        """清除检查点"""
        try:
            # CheckpointManager 已在顶部导入
            spider_name = self.spider.name if self.spider else 'unknown'
            checkpoint_mgr = CheckpointManager(spider_name, self.settings)
            
            if checkpoint_mgr.enabled:
                await checkpoint_mgr.clear()
                
        except Exception as e:
            self.logger.debug(f"Failed to clear checkpoint: {e}")
    
    def get_generation_stats(self) -> dict:
        """获取生成统计"""
        return {
            **self._generation_stats.to_dict(),
            'queue_size': len(self.scheduler) if self.scheduler else 0,
            'active_tasks': len(self.task_manager.current_task) if self.task_manager else 0,
            'backpressure_stats': self._backpressure_ctrl.get_stats(),
        }