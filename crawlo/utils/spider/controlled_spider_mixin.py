#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
受控爬虫混入类
解决 start_requests() yield 上万个请求时的并发控制问题
"""
import asyncio
import time
from collections import deque
from typing import Generator, Optional

from crawlo import Request
from crawlo.logging import get_logger


class ControlledRequestMixin:
    """
    受控请求生成混入类
    
    解决问题：
    1. start_requests() 同时yield上万个请求导致内存爆炸
    2. 不遵守CONCURRENCY设置，无限制创建请求
    3. 队列积压过多请求影响性能
    
    解决方案：
    1. 按需生成请求，根据实际并发能力控制
    2. 动态监控队列状态，智能调节生成速度
    3. 支持背压控制，避免队列积压
    """
    
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        
        # 受控生成配置
        self.max_pending_requests = 100     # 最大待处理请求数
        self.batch_size = 50               # 每批生成请求数
        self.generation_interval = 0.1      # 生成间隔（秒）
        self.backpressure_threshold = 200   # 背压阈值
        
        # 内部状态
        self._original_start_requests = None
        self._pending_count = 0
        self._total_generated = 0
        self._generation_paused = False
        
        # 性能监控
        self._last_generation_time = 0
        self._generation_stats = {
            'generated': 0,
            'skipped': 0,
            'backpressure_events': 0
        }
    
    def start_requests(self) -> Generator[Request, None, None]:
        """
        受控的 start_requests 实现
        
        注意：这个方法会替换原始的 start_requests，
        原始请求将通过 _original_start_requests() 提供
        """
        # 保存原始的请求生成器
        if hasattr(self, '_original_start_requests') and self._original_start_requests:
            original_generator = self._original_start_requests()
        else:
            # 如果子类没有定义 _original_start_requests，尝试调用原始方法
            original_generator = self._get_original_requests()
        
        # 使用受控生成器包装原始生成器
        yield from self._controlled_request_generator(original_generator)
    
    def _original_start_requests(self) -> Generator[Request, None, None]:
        """
        子类应该实现这个方法，提供原始的请求生成逻辑
        
        示例：
        def _original_start_requests(self):
            for i in range(50000):  # 5万个请求
                yield Request(url=f"https://example.com/page/{i}")
        """
        raise NotImplementedError(
            "子类必须实现 _original_start_requests() 方法，"
            "或者确保原始的 start_requests() 方法存在"
        )
    
    def _get_original_requests(self) -> Generator[Request, None, None]:
        """尝试获取原始请求（向后兼容）"""
        # 这里可以尝试调用父类的 start_requests 或其他方式
        # 具体实现取决于你的需求
        return iter([])  # 默认返回空生成器
    
    def _controlled_request_generator(self, original_generator) -> Generator[Request, None, None]:
        """Controlled request generator"""
        self.logger.info(f"Starting controlled request generator (max pending: {self.max_pending_requests})")
        
        request_buffer = deque()
        batch_count = 0
        
        try:
            # 分批处理原始请求
            for request in original_generator:
                request_buffer.append(request)
                
                # 当缓冲区达到批次大小时，进行控制检查
                if len(request_buffer) >= self.batch_size:
                    yield from self._yield_controlled_batch(request_buffer)
                    batch_count += 1
                    
                    # 每批次后检查是否需要暂停
                    if self._should_pause_generation():
                        self._wait_for_capacity()
            
            # 处理剩余的请求
            if request_buffer:
                yield from self._yield_controlled_batch(request_buffer)
        
        except Exception as e:
            self.logger.error(f"Controlled request generation failed: {e}")
            raise
        
        self.logger.info(
            f"Controlled request generation completed!"
            f"总计: {self._generation_stats['generated']}, "
            f"跳过: {self._generation_stats['skipped']}, "
            f"背压事件: {self._generation_stats['backpressure_events']}"
        )
    
    def _yield_controlled_batch(self, request_buffer: deque) -> Generator[Request, None, None]:
        """分批受控 yield 请求"""
        while request_buffer:
            # 检查当前系统负载
            if self._should_pause_generation():
                self.logger.debug("检测到系统负载过高，暂停生成")
                self._generation_stats['backpressure_events'] += 1
                self._wait_for_capacity()
            
            # yield 一个请求
            request = request_buffer.popleft()
            
            # 可以在这里添加额外的请求处理逻辑
            processed_request = self._process_request_before_yield(request)
            if processed_request:
                self._total_generated += 1
                self._generation_stats['generated'] += 1
                self._last_generation_time = time.time()
                yield processed_request
            else:
                self._generation_stats['skipped'] += 1
            
            # 控制生成速度
            if self.generation_interval > 0:
                time.sleep(self.generation_interval)
    
    def _should_pause_generation(self) -> bool:
        """判断是否应该暂停请求生成"""
        # 检查队列大小（如果可以访问scheduler的话）
        if hasattr(self, 'crawler') and self.crawler:
            engine = getattr(self.crawler, 'engine', None)
            if engine and engine.scheduler:
                queue_size = len(engine.scheduler)
                if queue_size > self.backpressure_threshold:
                    return True
        
        # 检查任务管理器负载
        if hasattr(self, 'crawler') and self.crawler:
            engine = getattr(self.crawler, 'engine', None)
            if engine and engine.task_manager:
                current_tasks = len(engine.task_manager.current_task)
                concurrency = getattr(engine.task_manager, 'semaphore', None)
                if concurrency and hasattr(concurrency, '_initial_value'):
                    max_concurrency = concurrency._initial_value
                    # 如果当前任务数接近最大并发数，暂停生成
                    if current_tasks >= max_concurrency * 0.8:  # 80% 阈值
                        return True
        
        return False
    
    def _wait_for_capacity(self):
        """Wait for system to have sufficient capacity"""
        wait_time = 0.1
        max_wait = 5.0
        
        while self._should_pause_generation() and wait_time < max_wait:
            time.sleep(wait_time)
            wait_time = min(wait_time * 1.2, max_wait)  # 指数退避
    
    def _process_request_before_yield(self, request: Request) -> Optional[Request]:
        """
        在 yield 请求前进行处理
        子类可以重写这个方法来添加自定义逻辑
        
        返回 None 表示跳过这个请求
        """
        return request
    
    def get_generation_stats(self) -> dict:
        """获取生成统计信息"""
        return {
            **self._generation_stats,
            'total_generated': self._total_generated,
            'last_generation_time': self._last_generation_time
        }


class AsyncControlledRequestMixin:
    """
    异步版本的受控请求混入类
    
    使用asyncio来实现更精确的并发控制
    """
    
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        
        # 异步控制配置
        self.max_concurrent_generations = 10   # 最大同时生成数
        self.generation_semaphore = None
        self.queue_monitor_interval = 1.0       # 队列监控间隔
        
        # 异步状态
        self._generation_tasks = set()
        self._monitoring_task = None
        self._stop_generation = False
    
    def _original_start_requests(self) -> Generator[Request, None, None]:
        """
        子类应该实现这个方法，提供原始的请求生成逻辑
        
        示例：
        def _original_start_requests(self):
            for i in range(50000):  # 5万个请求
                yield Request(url=f"https://example.com/page/{i}")
        """
        raise NotImplementedError(
            "子类必须实现 _original_start_requests() 方法，"
            "或者确保原始的 start_requests() 方法存在"
        )
    
    def _get_original_requests(self) -> Generator[Request, None, None]:
        """尝试获取原始请求（向后兼容）"""
        # 这里可以尝试调用父类的 start_requests 或其他方式
        # 具体实现取决于你的需求
        return iter([])  # 默认返回空生成器
    
    def _should_pause_generation(self) -> bool:
        """判断是否应该暂停请求生成"""
        # 检查队列大小（如果可以访问scheduler的话）
        if hasattr(self, 'crawler') and self.crawler:
            engine = getattr(self.crawler, 'engine', None)
            if engine and engine.scheduler:
                queue_size = len(engine.scheduler)
                if queue_size > 200:  # 背压阈值
                    return True
        
        # 检查任务管理器负载
        if hasattr(self, 'crawler') and self.crawler:
            engine = getattr(self.crawler, 'engine', None)
            if engine and engine.task_manager:
                current_tasks = len(engine.task_manager.current_task)
                concurrency = getattr(engine.task_manager, 'semaphore', None)
                if concurrency and hasattr(concurrency, '_initial_value'):
                    max_concurrency = concurrency._initial_value
                    # 如果当前任务数接近最大并发数，暂停生成
                    if current_tasks >= max_concurrency * 0.8:  # 80% 阈值
                        return True
        
        return False
    
    def _process_request_before_yield(self, request: Request) -> Optional[Request]:
        """
        在 yield 请求前进行处理
        子类可以重写这个方法来添加自定义逻辑
        
        返回 None 表示跳过这个请求
        """
        return request
    
    async def start_requests_async(self) -> Generator[Request, None, None]:
        """异步版本的受控请求生成"""
        # 初始化信号量
        self.generation_semaphore = asyncio.Semaphore(self.max_concurrent_generations)
        
        # 启动队列监控
        self._monitoring_task = asyncio.create_task(self._monitor_queue_load())
        
        try:
            # 获取原始请求
            original_requests = self._original_start_requests()
            
            # 分批异步处理
            batch = []
            async for request in self._async_request_wrapper(original_requests):
                batch.append(request)
                
                if len(batch) >= 50:  # 批次大小
                    async for request in self._process_async_batch(batch):
                        yield request
                    batch = []
            
            # 处理剩余请求
            if batch:
                async for request in self._process_async_batch(batch):
                    yield request
        
        finally:
            # 清理
            self._stop_generation = True
            if self._monitoring_task:
                self._monitoring_task.cancel()
            
            # 等待所有生成任务完成
            if self._generation_tasks:
                await asyncio.gather(*self._generation_tasks, return_exceptions=True)
    
    async def _async_request_wrapper(self, sync_generator):
        """将同步生成器包装为异步"""
        for request in sync_generator:
            yield request
            await asyncio.sleep(0)  # 让出控制权
    
    async def _process_async_batch(self, batch):
        """异步处理批次请求"""
        async def process_single_request(request):
            async with self.generation_semaphore:
                # 等待合适的时机
                while self._should_pause_generation() and not self._stop_generation:
                    await asyncio.sleep(0.1)
                
                if not self._stop_generation:
                    return self._process_request_before_yield(request)
                return None
        
        # 并发处理批次中的请求
        tasks = [process_single_request(req) for req in batch]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # yield 处理完的请求
        for result in results:
            if result and not isinstance(result, Exception):
                yield result
    
    async def _monitor_queue_load(self):
        """监控队列负载"""
        while not self._stop_generation:
            try:
                # 这里可以添加队列负载监控逻辑
                await asyncio.sleep(self.queue_monitor_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.warning(f"队列监控异常: {e}")
                await asyncio.sleep(1.0)


# 使用示例和文档
USAGE_EXAMPLE = '''
# 同步版本使用示例：

class MyControlledSpider(Spider, ControlledRequestMixin):
    name = 'controlled_spider'
    
    def __init__(self):
        Spider.__init__(self)
        ControlledRequestMixin.__init__(self)
        
        # 配置受控生成参数
        self.max_pending_requests = 200
        self.batch_size = 100
        self.generation_interval = 0.05
    
    def _original_start_requests(self):
        """提供原始的大量请求"""
        for i in range(50000):  # 5万个请求
            yield Request(url=f"https://example.com/page/{i}")
    
    def _process_request_before_yield(self, request):
        """可选：在yield前处理请求"""
        # 可以添加去重、优先级设置等逻辑
        return request
    
    async def parse(self, response):
        # 解析逻辑
        yield {"url": response.url}

# 异步版本使用示例：

class MyAsyncControlledSpider(Spider, AsyncControlledRequestMixin):
    name = 'async_controlled_spider'
    
    def __init__(self):
        Spider.__init__(self)
        AsyncControlledRequestMixin.__init__(self)
        
        # 配置异步控制参数
        self.max_concurrent_generations = 15
        self.queue_monitor_interval = 0.5
    
    def _original_start_requests(self):
        """提供原始的大量请求"""
        categories = ['tech', 'finance', 'sports']
        for category in categories:
            for page in range(1, 10000):  # 每个分类1万页
                yield Request(
                    url=f"https://news-site.com/{category}?page={page}",
                    meta={'category': category}
                )
    
    def _process_request_before_yield(self, request):
        """异步版本的请求预处理"""
        # 根据分类设置优先级
        category = request.meta.get('category', '')
        if category == 'tech':
            request.priority = 10
        return request
    
    async def parse(self, response):
        # 异步解析逻辑
        yield {
            "url": response.url,
            "category": response.meta['category']
        }

# 使用时：
from crawlo.crawler import CrawlerProcess
from crawlo.config import CrawloConfig

# 同步版本
config = CrawloConfig.standalone(concurrency=16)
process = CrawlerProcess(config)
process.crawl(MyControlledSpider)
process.start()

# 异步版本
async_config = CrawloConfig.standalone(
    concurrency=30,
    downloader='httpx'  # 推荐使用支持异步的下载器
)
async_process = CrawlerProcess(async_config)
async_process.crawl(MyAsyncControlledSpider)
async_process.start()
'''