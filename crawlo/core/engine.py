#!/usr/bin/python
# -*- coding:UTF-8 -*-
import asyncio
import time
from inspect import iscoroutine, isasyncgen, isgenerator
from typing import Optional, Callable, Any, Union, Dict, Iterator

from crawlo import Request, Item
from crawlo.spider import Spider
from crawlo.event import CrawlerEvent
from crawlo.project import common_call
from crawlo.failure import Failure
from crawlo.logging import get_logger
from crawlo.exceptions import OutputError
from crawlo.error_types import ErrorClassifier
from crawlo.task_manager import TaskManager
from crawlo.downloader import DownloaderBase
from crawlo.core.processor import Processor
from crawlo.core.scheduler import Scheduler
from crawlo.core.engine_helpers import GenerationStats, BackpressureController
from crawlo.utils.misc import load_object
from crawlo.utils.misc import safe_get_config
from crawlo.utils.func_tools import transform
from crawlo.__version__ import __version__


class Engine(object):
    
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
        self.start_requests: Optional[Iterator] = None
        self._close_reason: str = 'finished'  # 关闭原因：finished / shutdown
        self._spider_closed: bool = False  # 防止 close_spider 重复调用
        
        # ========== 统一配置获取（集中在初始化阶段） ==========
        
        # 并发控制配置
        concurrency = safe_get_config(self.settings, 'CONCURRENCY', 8, int)
        self.task_manager: Optional[TaskManager] = TaskManager(concurrency)
        
        # 请求生成配置
        self.max_queue_size = safe_get_config(self.settings, 'SCHEDULER_MAX_QUEUE_SIZE', 200, int)
        self.generation_batch_size = safe_get_config(self.settings, 'REQUEST_GENERATION_BATCH_SIZE', 10, int)
        self.generation_interval = safe_get_config(self.settings, 'REQUEST_GENERATION_INTERVAL', 0.01, float)
        self.backpressure_ratio = safe_get_config(self.settings, 'BACKPRESSURE_RATIO', 0.9, float)
        self.enable_controlled_generation = safe_get_config(
            self.settings, 'ENABLE_CONTROLLED_REQUEST_GENERATION', False, bool
        )
        
        # 版本配置（直接从 __version__.py 导入，不从配置文件获取）
        self.version = __version__
        
        # 检查点配置
        self.checkpoint_save_on_signal = safe_get_config(
            self.settings, 'CHECKPOINT_SAVE_ON_SIGNAL', True, bool
        )
        
        # 下载器配置
        self.downloader_type = safe_get_config(self.settings, 'DOWNLOADER_TYPE')
        self.downloader_path = safe_get_config(self.settings, 'DOWNLOADER')
        
        # 初始化辅助工具类
        self._generation_stats = GenerationStats()
        self._backpressure_ctrl = BackpressureController(
            max_queue_size=self.max_queue_size,
            backpressure_ratio=self.backpressure_ratio
        )

        self.logger = get_logger(name=self.__class__.__name__)

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

        # 检查点恢复：如果存在检查点且 resume=True，从检查点恢复
        checkpoint_resumed = False
        if resume:
            checkpoint_resumed = await self._try_resume_from_checkpoint(spider)

        if not checkpoint_resumed:
            # 正常流程：从 start_requests 开始
            self.logger.debug("开始创建start_requests迭代器")
            try:
                # 先收集所有请求到列表中，避免在检查时消耗迭代器
                requests_list = list(spider.start_requests())
                self.logger.debug(f"收集到 {len(requests_list)} 个请求")
                self.start_requests = iter(requests_list)
                self.logger.debug("start_requests迭代器创建成功")
            except Exception as e:
                self.logger.error(f"创建start_requests迭代器失败: {e}")
                import traceback
                self.logger.error(traceback.format_exc())
        
        await self._open_spider()

    async def crawl(self):
        """
        支持智能请求生成和背压控制
        """
        generation_task = None
        
        try:
            # 启动请求生成任务（使用初始化时获取的配置）
            if self.start_requests and self.enable_controlled_generation:
                self.logger.debug("创建受控请求生成任务")
                generation_task = asyncio.create_task(
                    self._controlled_request_generation()
                )
            else:
                # 传统方式处理启动请求
                self.logger.debug("创建传统请求生成任务")
                generation_task = asyncio.create_task(
                    self._traditional_request_generation()
                )
            
            self.logger.debug("请求生成任务创建完成")
            
            # 主爬取循环
            loop_count = 0
            last_exit_check = 0  # 记录上次检查退出条件的循环次数
            last_component_states = None  # 记录上次的组件状态，用于减少冗余日志
            batch_size = 5  # 批量获取请求的数量
            idle_count = 0  # 连续空闲计数
            
            # 动态退出检查间隔
            exit_check_interval = 10
            min_check_interval = 5  # 最小检查间隔
            max_check_interval = 20  # 最大检查间隔
            
            while self.running:
                loop_count += 1
                
                # 批量获取请求
                requests = []
                for _ in range(batch_size):
                    if request := await self._get_next_request():
                        requests.append(request)
                    else:
                        break
                
                # 批量处理请求
                if requests:
                    idle_count = 0  # 重置空闲计数
                    # 并发处理批量请求
                    tasks = [self._crawl(req) for req in requests]
                    await asyncio.gather(*tasks, return_exceptions=True)
                    
                    # 有请求处理时，增加检查间隔（减少开销）
                    exit_check_interval = min(exit_check_interval + 1, max_check_interval)
                else:
                    idle_count += 1
                    
                    # 首次检测到空闲时，立即检查退出条件
                    if idle_count == 1:
                        should_exit, last_component_states = await self._should_exit(last_component_states)
                        if should_exit:
                            # 添加短暂等待，避免瞬时空闲误判
                            await asyncio.sleep(0.001)
                            # 再次确认所有组件仍然空闲
                            if await self._check_all_idle():
                                self.logger.debug("二次确认所有组件空闲，准备退出循环")
                                break
                        last_exit_check = loop_count
                    
                    # 空闲状态，减少检查间隔（加快退出）
                    exit_check_interval = max(exit_check_interval - 1, min_check_interval)
                
                # 优化退出条件检查频率
                if loop_count - last_exit_check >= exit_check_interval:
                    should_exit, last_component_states = await self._should_exit(last_component_states)
                    if should_exit:
                        self.logger.debug("满足退出条件，准备退出循环")
                        break
                    last_exit_check = loop_count
                
                # 动态调整 sleep 时间，根据负载情况
                if requests:
                    # 有请求处理，极短休息
                    await asyncio.sleep(0.000001)
                elif idle_count > 10:
                    # 连续空闲，增加休息时间
                    await asyncio.sleep(0.01)
                else:
                    # 短暂休息
                    await asyncio.sleep(0.001)
            
            self.logger.debug(f"主爬取循环结束，总共执行了 {loop_count} 次")
        
        finally:
            # 确保请求生成任务完成
            if generation_task and not generation_task.done():
                try:
                    await generation_task
                except asyncio.CancelledError:
                    self.logger.debug("Generation task cancelled")
            
            # 优雅关闭爬虫（reason 已经在 signal handler 中设置）
            try:
                await self.close_spider()
            except asyncio.CancelledError:
                self.logger.debug("close_spider cancelled")

    async def _traditional_request_generation(self):
        """传统请求生成方法（兼容旧版本）"""
        self.logger.debug("开始处理传统请求生成")
        processed_count = 0
        while self.running and self.start_requests is not None:
            try:
                start_request = next(self.start_requests)
                # 请求入队
                await self.enqueue_request(start_request)
                processed_count += 1
            except StopIteration:
                self.logger.debug("所有起始请求处理完成")
                self.start_requests = None
                break
            except Exception as exp:
                self.logger.error(f"处理请求时发生异常: {exp}")
                import traceback
                self.logger.error(traceback.format_exc())
                if not await self._exit():
                    continue
                self.running = False
                if self.start_requests is not None:
                    self.logger.error(f"Error occurred while starting request: {str(exp)}")
            # 减少等待时间以提高效率
            await asyncio.sleep(0.00001)  # 从0.0001减少到0.00001
        self.logger.debug(f"传统请求生成完成，总共处理了 {processed_count} 个请求")

    async def _controlled_request_generation(self):
        """Controlled request generation (enhanced features)"""
        self.logger.debug("Starting controlled request generation")
        
        if self.start_requests is None:
            return
            
        batch = []
        total_generated = 0
        
        try:
            for request in self.start_requests:
                batch.append(request)
                
                # 批量处理
                if len(batch) >= self.generation_batch_size:
                    generated = await self._process_generation_batch(batch)
                    total_generated += generated
                    batch = []
                
                # 背压检查
                if await self._should_pause_generation():
                    await self._wait_for_capacity()
            
            # 处理剩余请求
            if batch:
                generated = await self._process_generation_batch(batch)
                total_generated += generated
        
        except Exception as e:
            self.logger.error(f"Request generation failed: {e}")
        
        finally:
            self.start_requests = None
            self.logger.debug(f"Request generation completed, total: {total_generated}")

    async def _process_generation_batch(self, batch) -> int:
        """
        处理一批请求
               
        优化点：
        - 使用 asyncio.gather 并发入队，减少串行等待
        - 动态调整生成间隔，避免过度限流
        - 添加批量统计信息
        """
        generated = 0
        
        # 优化：如果队列有足够空间，批量并发入队
        queue_size = len(self.scheduler) if self.scheduler else 0
        available_space = self.max_queue_size - queue_size
        
        if available_space >= len(batch):
            # 队列有足够空间，并发入队
            tasks = []
            for request in batch:
                if not self.running:
                    break
                tasks.append(self._enqueue_single_request(request))
            
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for result in results:
                    if isinstance(result, bool) and result:
                        generated += 1
                        self._generation_stats.increment_generated()
        else:
            # 队列空间不足，逐个入队并等待
            for request in batch:
                if not self.running:
                    break
                
                # 等待队列有空间
                wait_count = 0
                while await self._is_queue_full() and self.running:
                    await asyncio.sleep(0.005)  # 减少等待间隔
                    wait_count += 1
                    if wait_count > 200:  # 最多等待1秒
                        self.logger.warning("Queue full timeout, skipping remaining requests")
                        break
                
                if self.running:
                    success = await self._enqueue_single_request(request)
                    if success:
                        generated += 1
                        self._generation_stats.increment_generated()
                
                # 动态调整生成间隔：根据队列使用率调整
                if self.generation_interval > 0:
                    queue_usage = queue_size / max(1, self.max_queue_size)
                    # 队列使用率高时增加间隔，低时减少间隔
                    adaptive_interval = self.generation_interval * (0.5 + queue_usage)
                    await asyncio.sleep(adaptive_interval)
        
        return generated
    
    async def _enqueue_single_request(self, request) -> bool:
        """
        单个请求入队
        
        Returns:
            bool: 是否成功入队
        """
        try:
            await self.enqueue_request(request)
            return True
        except Exception as e:
            self.logger.debug(f"Failed to enqueue request {request.url}: {e}")
            return False

    async def _should_pause_generation(self) -> bool:
        """Determine whether generation should be paused"""
        # 使用背压控制器检查
        return self._backpressure_ctrl.should_pause(
            self.scheduler, 
            self.task_manager
        )

    async def _is_queue_full(self) -> bool:
        """Check if queue is full"""
        return self._backpressure_ctrl.is_queue_full(self.scheduler)

    async def _wait_for_capacity(self):
        """Wait for system to have sufficient capacity"""
        self._generation_stats.increment_backpressure()
        self.logger.debug("Backpressure triggered, pausing request generation")
        
        wait_time = 0.01  # 减少初始等待时间
        max_wait = 1.0  # 减少最大等待时间
        
        while await self._should_pause_generation() and self.running:
            await asyncio.sleep(wait_time)
            wait_time = min(wait_time * 1.1, max_wait)

    async def _open_spider(self):
        asyncio.create_task(self.crawler.subscriber.notify(CrawlerEvent.SPIDER_OPENED))
        # 直接调用crawl方法而不是创建任务，确保等待完成
        await self.crawl()

    async def _crawl(self, request):
        async def crawl_task():
            start_time = time.time()
            # 记录请求标记（flags）用于调试追踪
            if getattr(request, 'flags', None):
                self.logger.debug(
                    f"Processing request with flags: {request.flags} -> {request.url}"
                )
            try:
                outputs = await self._fetch(request)
                # 记录响应时间
                response_time = time.time() - start_time
                if self.task_manager:
                    self.task_manager.record_response_time(response_time)
                
                if outputs:
                    await self._handle_spider_output(outputs)
                
                # 由于我们不再使用处理队列，不再需要确认任务完成
                # 任务在从主队列取出时就已经被认为是完成的
            except asyncio.CancelledError:
                # 正确处理取消异常（静默处理，避免重复日志）
                # 日志已在上面的task_manager.create_task处打印
                raise
            except Exception as e:
                # 记录详细的异常信息
                self.logger.error(
                    f"处理请求失败: {getattr(request, 'url', 'Unknown URL')} - {type(e).__name__}: {e}"
                )
                self.logger.debug(f"详细异常信息", exc_info=True)
                
                # 发送统计事件
                if hasattr(self.crawler, 'stats'):
                    self.crawler.stats.inc_value('downloader/exception_count')
                    self.crawler.stats.inc_value(f'downloader/exception_type_count/{type(e).__name__}')
                    if hasattr(request, 'url'):
                        self.crawler.stats.inc_value(f'downloader/failed_urls_count')
                
                # ========== 调用用户定义的 errback ==========
                errback = getattr(request, 'errback', None)
                if errback and callable(errback):
                    try:
                        errback_result = await common_call(errback, Failure(e, request=request))
                        if errback_result is not None:
                            await self._handle_errback_output(errback_result)
                    except Exception as errback_error:
                        self.logger.error(
                            f"errback 执行失败 [{getattr(request, 'url', 'Unknown URL')}]: "
                            f"{type(errback_error).__name__}: {errback_error}"
                        )
                # ==========================================
                
                # 关键错误需要重新抛出，避免系统处于不稳定状态
                if ErrorClassifier.is_critical(e):
                    self.logger.critical(f"遇到关键错误，停止爬虫: {type(e).__name__}: {e}")
                    raise
                
                # 非关键错误继续处理下一个请求
                return None

        # 使用异步任务创建，遵守并发限制
        if self.task_manager:
            coro = crawl_task()
            try:
                await self.task_manager.create_task(coro)
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
        async def _successful(_response):
            if self.spider is None:
                return None
            callback: Callable = request.callback or self.spider.parse
            _outputs = callback(_response, **request.cb_kwargs)
            
            if _outputs is None:
                return None
            
            # 异步生成器（async def + yield） - 最常见且正确的用法
            if isasyncgen(_outputs):
                return transform(_outputs, _response)
            
            # 同步生成器（def + yield）
            if isgenerator(_outputs):
                return transform(_outputs, _response)
            
            # 协程（async def 不使用 yield） - await 获取结果后再判断
            if iscoroutine(_outputs):
                result = await _outputs
                if result is None:
                    return None
                # await 后的结果可能是生成器或单个值
                if isasyncgen(result):
                    return transform(result, _response)
                if isgenerator(result):
                    return transform(result, _response)
                # 单个 Request/Item 返回值，包装为异步生成器
                if isinstance(result, (Request, Item)):
                    async def _single_output():
                        yield result
                    return transform(_single_output(), _response)
                # 列表/元组返回值
                if isinstance(result, (list, tuple)):
                    async def _list_output():
                        for item in result:
                            if isinstance(item, (Request, Item)):
                                yield item
                    return transform(_list_output(), _response)
                # 其他类型结果，记录警告
                self.logger.warning(
                    f"Callback {callback.__name__} returned unexpected type "
                    f"{type(result).__name__} from coroutine. "
                    f"Use 'yield' instead of 'return' for producing output."
                )
                return None
            
            # 同步函数返回单个 Request/Item（非生成器）
            if isinstance(_outputs, (Request, Item)):
                async def _sync_single_output():
                    yield _outputs
                return transform(_sync_single_output(), _response)
            
            # 同步函数返回列表/元组
            if isinstance(_outputs, (list, tuple)):
                async def _sync_list_output():
                    for item in _outputs:
                        if isinstance(item, (Request, Item)):
                            yield item
                return transform(_sync_list_output(), _response)
            
            # 其他未知类型，记录警告
            self.logger.warning(
                f"Callback {callback.__name__} returned unexpected type "
                f"{type(_outputs).__name__}. Expected generator, async generator, "
                f"Request, Item, or list/tuple of them."
            )
            return None

        if self.downloader is None:
            return None
        _response = await self.downloader.fetch(request)
        if _response is None:
            return None
        output = await _successful(_response)
        return output

    async def enqueue_request(self, start_request):
        if self.scheduler is not None:
            await self._schedule_request(start_request)

    async def _schedule_request(self, request):
        if self.scheduler is not None and await self.scheduler.enqueue_request(request):
            if self.crawler is not None and self.crawler.spider is not None:
                asyncio.create_task(self.crawler.subscriber.notify(CrawlerEvent.REQUEST_SCHEDULED, request, self.crawler.spider))

    async def _get_next_request(self):
        if self.scheduler is not None:
            return await self.scheduler.next_request()
        return None

    async def _handle_spider_output(self, outputs):
        if self.processor is None:
            return
        async for spider_output in outputs:
            if isinstance(spider_output, (Request, Item)):
                await self.processor.enqueue(spider_output)
            elif isinstance(spider_output, Exception):
                if self.crawler is not None and self.spider is not None:
                    asyncio.create_task(
                        self.crawler.subscriber.notify(CrawlerEvent.SPIDER_ERROR, spider_output, self.spider)
                    )
                raise spider_output
            else:
                raise OutputError(f'{type(self.spider)} must return `Request` or `Item`.')

    async def _handle_errback_output(self, result):
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
            await self._handle_spider_output(_gen())
        elif isinstance(result, (list, tuple)):
            async def _gen():
                for item in result:
                    if isinstance(item, (Request, Item)):
                        yield item
            await self._handle_spider_output(_gen())
        elif isasyncgen(result):
            await self._handle_spider_output(result)
        elif isgenerator(result):
            async def _wrap_sync_gen():
                for item in result:
                    if isinstance(item, (Request, Item)):
                        yield item
            await self._handle_spider_output(_wrap_sync_gen())
        elif iscoroutine(result):
            awaited = await result
            if awaited is not None:
                await self._handle_errback_output(awaited)
        else:
            self.logger.warning(
                f"errback returned unexpected type {type(result).__name__}, ignored"
            )

    async def _exit(self):
        # 使用异步 idle 检查，避免非原子状态检查的竞态条件
        scheduler_idle = False
        downloader_idle = False
        task_manager_done = False
        processor_idle = False
        
        if self.scheduler is not None:
            scheduler_idle = await self.scheduler.async_idle() if hasattr(self.scheduler, 'async_idle') else self.scheduler.idle()
        if self.downloader is not None:
            downloader_idle = self.downloader.idle()
        if self.task_manager is not None:
            task_manager_done = self.task_manager.all_done()
        if self.processor is not None:
            processor_idle = await self.processor.idle_async()
        
        if (scheduler_idle and downloader_idle and task_manager_done and processor_idle):
            return True
        return False
    
    async def _check_all_idle(self) -> bool:
        """二次确认所有组件是否仍然空闲
        
        用于在退出前添加短暂等待后再次确认，避免瞬时空闲误判。
        
        Returns:
            bool: 所有组件是否都空闲
        """
        return await self._exit()

    async def _should_exit(self, last_component_states=None) -> tuple[bool, tuple]:
        """检查是否应该退出
        
        Args:
            last_component_states: 上次的组件状态元组，用于减少冗余日志
            
        Returns:
            tuple: (should_exit, current_states)
        """
        # 没有启动请求，且所有队列都空闲
        if self.start_requests is None:
            # 使用异步的idle检查方法以获得更精确的结果
            scheduler_idle = False
            downloader_idle = False
            task_manager_done = False
            processor_idle = False
            
            if self.scheduler is not None:
                scheduler_idle = await self.scheduler.async_idle() if hasattr(self.scheduler, 'async_idle') else self.scheduler.idle()
            if self.downloader is not None:
                downloader_idle = self.downloader.idle()
            if self.task_manager is not None:
                task_manager_done = self.task_manager.all_done()
            if self.processor is not None:
                processor_idle = await self.processor.idle_async()
            
            current_states = (scheduler_idle, downloader_idle, task_manager_done, processor_idle)
            
            # 只在组件状态发生变化时输出日志
            if current_states != last_component_states:
                self.logger.debug(
                    f"组件状态变化 - Scheduler: {scheduler_idle}, "
                    f"Downloader: {downloader_idle}, "
                    f"TaskManager: {task_manager_done}, "
                    f"Processor: {processor_idle}"
                )
            
            if (scheduler_idle and 
                downloader_idle and 
                task_manager_done and 
                processor_idle):
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
        
        # 关闭下载器（带超时保护）
        if self.downloader is not None and hasattr(self.downloader, 'close'):
            try:
                close_result = self.downloader.close()
                # 如果是协程，使用超时等待
                if asyncio.iscoroutine(close_result):
                    await asyncio.wait_for(close_result, timeout=5.0)
            except asyncio.TimeoutError:
                self.logger.warning("下载器关闭超时，强制清理资源")
            except Exception as e:
                self.logger.debug(f"下载器关闭时发生错误: {e}")
        
        # 关闭调度器
        if self.scheduler is not None:
            try:
                await asyncio.wait_for(self.scheduler.close(), timeout=5.0)
            except asyncio.TimeoutError:
                self.logger.warning("调度器关闭超时")
            except Exception as e:
                self.logger.debug(f"调度器关闭时发生错误: {e}")
    
    async def _try_resume_from_checkpoint(self, spider) -> bool:
        """尝试从检查点恢复爬取状态
        
        Args:
            spider: 爬虫实例
            
        Returns:
            bool: 是否成功从检查点恢复
        """
        try:
            from crawlo.checkpoint import CheckpointManager
            
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
            self.start_requests = None
            
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
            from crawlo.checkpoint import CheckpointManager
            
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
            from crawlo.checkpoint import CheckpointManager
            
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