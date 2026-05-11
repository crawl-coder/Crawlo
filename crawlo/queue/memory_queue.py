#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
内存队列实现

基于 asyncio.PriorityQueue 的内存优先队列实现。
提供两套队列系统：
- MemoryQueue / DomainAwareQueue：完整 IQueue 实现，支持背压控制、域名感知
- SpiderPriorityQueue：轻量级 PriorityQueue 封装，供 QueueManager 内存模式使用
"""
import asyncio
import time
import logging
from typing import Optional, Any, Dict, List

from crawlo.queue.queue_types import QueueType
from crawlo.queue.interfaces import IQueue, BackpressureableQueueMixin

# 智能背压组件（可选导入）
try:
    from crawlo.backpressure.metrics_collector import BackpressureMetricsCollector
    from crawlo.backpressure.intelligent_calculator import IntelligentBackpressureCalculator
    from crawlo.backpressure.monitor import BackpressureMonitor
    INTELLIGENT_BP_AVAILABLE = True
except ImportError:
    INTELLIGENT_BP_AVAILABLE = False
    logger.debug("Intelligent backpressure not available: crawlo.backpressure module not found")

logger = logging.getLogger(__name__)


class QueueItem:
    """
    队列项包装器
    
    用于在优先级队列中存储元素及其元数据。
    支持任意可序列化对象，不依赖对象自身的比较能力。
    """
    
    __slots__ = ('priority', 'item', 'timestamp', 'sequence')
    
    def __init__(self, priority: int, item: Any, sequence: int = 0):
        """
        初始化队列项
        
        Args:
            priority: 优先级
            item: 实际元素
            sequence: 序列号，用于同优先级元素的排序
        """
        self.priority = priority
        self.item = item
        self.timestamp = time.time()
        self.sequence = sequence
    
    def __lt__(self, other: 'QueueItem') -> bool:
        """
        比较操作，支持优先级队列
        
        优先级相同时按序列号排序，确保 FIFO 顺序
        """
        if self.priority != other.priority:
            return self.priority < other.priority  # 数值越小越优先（与 Request 约定一致）
        return self.sequence < other.sequence  # 先入队的在前
    
    def __repr__(self) -> str:
        item_repr = repr(self.item)[:50]
        return f"QueueItem(priority={self.priority}, item={item_repr})"


class MemoryQueue(BackpressureableQueueMixin, IQueue):
    """
    内存优先队列
    
    特点：
    - 基于 asyncio.PriorityQueue 实现
    - 支持优先级队列
    - 支持背压控制
    - 支持批量操作
    - 线程安全（asyncio 层面）
    
    使用示例：
        queue = MemoryQueue(max_size=1000)
        await queue.put(request, priority=5)
        request = await queue.get(timeout=1.0)
    """
    
    def __init__(
        self,
        max_size: int = 0,
        name: str = "memory",
        backpressure_enabled: bool = True,
        backpressure_threshold: float = 0.8,
        intelligent_backpressure: bool = True,
        backpressure_config: Optional[Dict[str, Any]] = None,
    ):
        """
        初始化内存队列
        
        Args:
            max_size: 最大队列大小，0 表示无限制
            name: 队列名称
            backpressure_enabled: 是否启用背压
            backpressure_threshold: 背压触发阈值 (0-1)
            intelligent_backpressure: 是否启用智能背压（多维度自适应）
            backpressure_config: 背压配置字典
        """
        super().__init__(max_size=max_size, name=name)
        self._queue: Optional[asyncio.PriorityQueue] = None
        self._backpressure_enabled = backpressure_enabled
        self._backpressure_threshold = backpressure_threshold
        self._intelligent_backpressure_enabled = intelligent_backpressure and INTELLIGENT_BP_AVAILABLE
        
        # 智能背压组件
        self._metrics_collector: Optional[BackpressureMetricsCollector] = None
        self._intelligent_calculator: Optional[IntelligentBackpressureCalculator] = None
        self._backpressure_monitor: Optional[BackpressureMonitor] = None
        
        # 初始化智能背压（如果启用）
        if self._intelligent_backpressure_enabled:
            self._init_intelligent_backpressure(backpressure_config or {})
        
        # 序列号生成器，用于保证 FIFO 顺序
        self._sequence_counter = 0
        self._sequence_lock = asyncio.Lock()
        
        # 内部状态
        self._total_puts = 0
        self._total_gets = 0
        self._rejected_puts = 0
        
        # 元数据存储（用于存储与请求相关的元信息）
        self._metadata: Dict[str, Any] = {}
    
    def _init_intelligent_backpressure(self, config: Dict[str, Any]):
        """
        初始化智能背压组件
        
        Args:
            config: 背压配置
        """
        try:
            # 创建指标采集器（带资源优化参数）
            self._metrics_collector = BackpressureMetricsCollector(
                window_size=config.get('window_size', 30),
                collect_interval=config.get('collect_interval', 1),
                queue_weights=config.get('queue_weights', (0.4, 0.3, 0.3)),
                score_thresholds=config.get('score_thresholds', (50, 70, 85)),
                queue_size_func=lambda: len(self) if self._queue else 0,
                queue_max_size_func=lambda: self._max_size if self._max_size > 0 else 1,
                max_history=config.get('max_history', 1000),
                max_response_times=config.get('max_response_times', 1000)
            )
            
            # 创建智能延迟计算器（带缓存优化）
            self._intelligent_calculator = IntelligentBackpressureCalculator(
                metrics_collector=self._metrics_collector,
                base_delay=config.get('base_delay', 0.5),
                max_delay=config.get('max_delay', 5.0),
                enable_prediction=config.get('enable_prediction', True),
                enable_smoothing=config.get('enable_smoothing', True),
                cache_ttl=config.get('cache_ttl', 0.1)
            )
            
            # 创建背压监控器
            self._backpressure_monitor = BackpressureMonitor(
                metrics_collector=self._metrics_collector,
                check_interval=config.get('monitor_interval', 10)
            )
            
            logger.debug(f"MemoryQueue '{self._name}': 智能背压已启用")
            
        except Exception as e:
            logger.error(f"初始化智能背压失败: {e}")
            self._intelligent_backpressure_enabled = False
    
    async def open(self) -> None:
        """
        打开队列
        
        初始化 asyncio.PriorityQueue 和智能背压组件。
        """
        if self._queue is None:
            # 使用 max_size=0 创建无界队列，实际限制通过逻辑控制
            self._queue = asyncio.PriorityQueue(maxsize=self._max_size if self._max_size > 0 else 0)
            self._stats.mark_start()
            
            # 启动智能背压组件
            if self._intelligent_backpressure_enabled:
                if self._metrics_collector:
                    await self._metrics_collector.start()
                if self._backpressure_monitor:
                    await self._backpressure_monitor.start()
            
            logger.debug(f"MemoryQueue '{self._name}' opened with max_size={self._max_size}")
    
    async def put(self, item: Any, priority: int = 0) -> bool:
        """
        入队操作
        
        Args:
            item: 要入队的元素
            priority: 优先级（数值越小越优先，与 Request 内部存储值一致）
            
        Returns:
            bool: 入队是否成功
        """
        if self._closed:
            logger.warning(f"Attempt to put item to closed queue '{self._name}'")
            self._stats.record_reject()
            return False
        
        if self._queue is None:
            await self.open()
        
        # 检查队列大小限制
        if self._max_size > 0:
            current_size = await self.size()
            if current_size >= self._max_size:
                logger.warning(
                    f"Queue '{self._name}' is full ({current_size}/{self._max_size}), "
                    f"rejecting item"
                )
                self._stats.record_reject()
                self._rejected_puts += 1
                return False
        
        # 应用背压控制
        if self._backpressure_enabled:
            should_backpressure = await self.should_apply_backpressure()
            if should_backpressure:
                delay = await self.calculate_backpressure_delay()
                if delay > 0:
                    logger.debug(
                        f"Backpressure: sleeping {delay:.3f}s before put, "
                        f"queue_size={await self.size()}"
                    )
                    await asyncio.sleep(delay)
        
        start_time = time.time()
        
        try:
            # 生成序列号以保证 FIFO 顺序
            async with self._sequence_lock:
                self._sequence_counter += 1
                sequence = self._sequence_counter
            
            # 使用 QueueItem 包装元素，避免依赖元素的比较能力
            queue_item = QueueItem(priority, item, sequence)
            await self._queue.put(queue_item)
            self._total_puts += 1
            wait_time = time.time() - start_time
            self._stats.record_enqueue(wait_time=wait_time)
            
            # 记录智能背压指标
            if self._intelligent_backpressure_enabled and self._metrics_collector:
                self._metrics_collector.record_enqueue()
            
            # 更新最大队列大小
            current_size = await self.size()
            self._stats.update_max_size(current_size)
            
            return True
            
        except asyncio.CancelledError:
            self._stats.record_reject()
            raise
        except Exception as e:
            logger.error(f"Error putting item to queue '{self._name}': {e}")
            self._stats.record_reject()
            return False
    
    async def get(self, timeout: Optional[float] = None) -> Optional[Any]:
        """
        出队操作
        
        Args:
            timeout: 超时时间（秒），None 表示无限等待
            
        Returns:
            出队的元素，如果超时返回 None
        """
        if self._closed and await self.empty():
            return None
        
        if self._queue is None:
            await self.open()
        
        timeout_value = timeout if timeout is not None else 0
        
        try:
            # 使用 async with asyncio.timeout 处理超时
            async with asyncio.timeout(timeout_value if timeout_value > 0 else None):
                queue_item = await self._queue.get()
            self._total_gets += 1
            self._stats.record_dequeue()
            
            # 记录智能背压指标
            if self._intelligent_backpressure_enabled and self._metrics_collector:
                self._metrics_collector.record_dequeue()
            
            # 返回 QueueItem 中包装的实际元素
            return queue_item.item if isinstance(queue_item, QueueItem) else queue_item
            
        except asyncio.TimeoutError:
            # 记录超时
            if self._intelligent_backpressure_enabled and self._metrics_collector:
                self._metrics_collector.record_response(
                    response_time=timeout_value if timeout_value else 5.0,
                    is_timeout=True,
                    is_success=False
                )
            return None
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Error getting item from queue '{self._name}': {e}")
            return None
    
    async def get_batch(self, batch_size: int, timeout: Optional[float] = 1.0) -> List[Any]:
        """
        批量出队
        
        Args:
            batch_size: 最大批量大小
            timeout: 获取单个元素超时时间
            
        Returns:
            List: 出队的元素列表
        """
        items = []
        
        for _ in range(batch_size):
            item = await self.get(timeout=timeout)
            if item is None:
                break
            items.append(item)
        
        return items
    
    async def put_batch(self, items: List[Any], default_priority: int = 0) -> int:
        """
        批量入队
        
        Args:
            items: 要入队的元素列表
            default_priority: 默认优先级
            
        Returns:
            int: 成功入队的数量
        """
        success_count = 0
        
        for item in items:
            if await self.put(item, priority=default_priority):
                success_count += 1
        
        return success_count
    
    async def size(self) -> int:
        """
        获取队列大小
        
        Returns:
            int: 当前队列中的元素数量
        """
        if self._queue is None:
            return 0
        
        try:
            return self._queue.qsize()
        except Exception:
            return 0
    
    async def empty(self) -> bool:
        """
        检查队列是否为空
        
        Returns:
            bool: 队列是否为空
        """
        if self._queue is None:
            return True
        
        try:
            return self._queue.empty()
        except Exception:
            return True
    
    async def close(self) -> None:
        """
        关闭队列
        
        关闭后队列将不再接受新的入队操作，
        但可以继续出队直到队列为空。
        """
        self._closed = True
        self._stats.mark_end()
        
        # 停止智能背压组件
        if self._intelligent_backpressure_enabled:
            if self._backpressure_monitor:
                await self._backpressure_monitor.stop()
            if self._metrics_collector:
                await self._metrics_collector.stop()
        
        if self._queue is not None:
            # 清空队列
            while not self._queue.empty():
                try:
                    self._queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
        
        logger.debug(
            f"MemoryQueue '{self._name}' closed. "
            f"Total puts: {self._total_puts}, gets: {self._total_gets}, "
            f"rejected: {self._rejected_puts}"
        )
    
    async def clear(self) -> None:
        """清空队列"""
        if self._queue is not None:
            while not self._queue.empty():
                try:
                    self._queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
        
        logger.debug(f"MemoryQueue '{self._name}' cleared")
    
    def get_extended_stats(self) -> Dict[str, Any]:
        """
        获取扩展统计信息
        
        Returns:
            Dict: 扩展统计信息
        """
        stats = {
            'queue_type': QueueType.MEMORY.value,
            'name': self._name,
            'max_size': self._max_size,
            'total_puts': self._total_puts,
            'total_gets': self._total_gets,
            'rejected_puts': self._rejected_puts,
            'backpressure_enabled': self._backpressure_enabled,
            'backpressure_threshold': self._backpressure_threshold,
            'backpressure_active': self._backpressure_active,
            'intelligent_backpressure_enabled': self._intelligent_backpressure_enabled,
            'base_stats': self._stats.to_dict(),
        }
        
        # 添加智能背压指标
        if self._intelligent_backpressure_enabled and self._backpressure_monitor:
            stats['intelligent_bp'] = self._backpressure_monitor.get_current_status()
            stats['alert_summary'] = self._backpressure_monitor.get_alert_summary()
        
        return stats
    
    async def calculate_backpressure_delay(self) -> float:
        """
        计算背压延迟
        
        如果启用了智能背压，使用智能计算器；
        否则使用父类的默认实现。
        
        Returns:
            float: 延迟时间（秒）
        """
        # 如果启用了智能背压，使用智能计算器
        if self._intelligent_backpressure_enabled and self._intelligent_calculator:
            try:
                delay = await self._intelligent_calculator.calculate_delay()
                return delay
            except Exception as e:
                logger.error(f"智能背压计算失败，回退到默认: {e}")
        
        # 回退到父类的默认实现
        return await super().calculate_backpressure_delay()
    
    def _on_backpressure_state_change(self, active: bool) -> None:
        """
        背压状态变更回调
        
        Args:
            active: 新的背压状态
        """
        if active:
            logger.info(
                f"Queue '{self._name}': Backpressure activated "
                f"(utilization >= {self._backpressure_threshold:.0%})"
            )
        else:
            logger.info(f"Queue '{self._name}': Backpressure deactivated")
    
    def __len__(self) -> int:
        """同步获取队列大小"""
        if self._queue is None:
            return 0
        try:
            return self._queue.qsize()
        except Exception:
            return 0


class DomainAwareQueue(MemoryQueue):
    """
    域名感知队列
    
    在 MemoryQueue 基础上增加了域名维度的流量控制，
    可以限制每个域名的并发请求数。
    
    特点：
    - 按域名分组请求
    - 支持域名级别的并发限制
    - 支持域名级别的速率限制
    """
    
    def __init__(
        self,
        max_size: int = 0,
        name: str = "domain_aware",
        max_per_domain: int = 2,
        domain_time_window: float = 1.0,
        backpressure_enabled: bool = True,
        backpressure_threshold: float = 0.8,
    ):
        """
        初始化域名感知队列
        
        Args:
            max_size: 最大队列大小
            name: 队列名称
            max_per_domain: 每个域名的最大并发数
            domain_time_window: 域名时间窗口（秒）
            backpressure_enabled: 是否启用背压
            backpressure_threshold: 背压触发阈值
        """
        super().__init__(
            max_size=max_size,
            name=name,
            backpressure_enabled=backpressure_enabled,
            backpressure_threshold=backpressure_threshold,
        )
        
        self._max_per_domain = max_per_domain
        self._domain_time_window = domain_time_window
        
        # 域名状态
        self._domain_last_request: Dict[str, float] = {}
        self._domain_request_count: Dict[str, int] = {}
        self._domain_semaphores: Dict[str, asyncio.Semaphore] = {}
        
        # 全局信号量用于限制总并发
        self._global_semaphore: Optional[asyncio.Semaphore] = None
    
    async def open(self) -> None:
        """打开队列"""
        await super().open()
        
        # 初始化全局信号量
        if self._max_size > 0:
            self._global_semaphore = asyncio.Semaphore(self._max_size)
    
    def _extract_domain(self, url: str) -> str:
        """提取 URL 中的域名"""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc or "unknown"
        except Exception:
            return "unknown"
    
    def _get_domain_semaphore(self, domain: str) -> asyncio.Semaphore:
        """获取域名的信号量"""
        if domain not in self._domain_semaphores:
            self._domain_semaphores[domain] = asyncio.Semaphore(self._max_per_domain)
        return self._domain_semaphores[domain]
    
    async def put(self, item: Any, priority: int = 0) -> bool:
        """
        入队操作
        
        对于 Request 对象，会检查域名并发限制。
        """
        # 检查是否为 Request 对象
        url = None
        if hasattr(item, 'url'):
            url = item.url
        elif isinstance(item, dict) and 'url' in item:
            url = item['url']
        
        if url:
            domain = self._extract_domain(url)
            
            # 检查域名时间窗口
            current_time = time.time()
            last_time = self._domain_last_request.get(domain, 0)
            time_since_last = current_time - last_time
            
            if time_since_last < self._domain_time_window:
                # 在时间窗口内，检查请求计数
                count = self._domain_request_count.get(domain, 0)
                if count >= self._max_per_domain:
                    # 需要等待
                    wait_time = self._domain_time_window - time_since_last
                    logger.debug(
                        f"Domain '{domain}' rate limited, waiting {wait_time:.2f}s"
                    )
                    await asyncio.sleep(wait_time)
            
            # 更新域名状态
            self._domain_last_request[domain] = time.time()
            self._domain_request_count[domain] = self._domain_request_count.get(domain, 0) + 1
        
        return await super().put(item, priority)
    
    async def get(self, timeout: Optional[float] = None) -> Optional[Any]:
        """
        出队操作
        
        获取请求时会释放对应的域名信号量。
        """
        item = await super().get(timeout=timeout)
        
        if item is not None:
            # 检查是否为 Request 对象
            url = None
            if hasattr(item, 'url'):
                url = item.url
            elif isinstance(item, dict) and 'url' in item:
                url = item['url']
            
            if url:
                domain = self._extract_domain(url)
                # 减少域名请求计数
                if domain in self._domain_request_count:
                    self._domain_request_count[domain] = max(
                        0, self._domain_request_count[domain] - 1
                    )
        
        return item
    
    def get_domain_stats(self) -> Dict[str, Any]:
        """
        获取域名统计信息
        
        Returns:
            Dict: 域名统计信息
        """
        return {
            'domain_counts': dict(self._domain_request_count),
            'domain_last_request': {
                k: round(v, 2) for k, v in self._domain_last_request.items()
            },
            'max_per_domain': self._max_per_domain,
            'time_window': self._domain_time_window,
        }


class SpiderPriorityQueue(asyncio.PriorityQueue):
    """带超时功能的异步优先级队列（MemoryQueue 的轻量级替代）"""

    def __init__(self, maxsize: int = 0) -> None:
        """初始化队列，maxsize为0表示无大小限制"""
        super().__init__(maxsize)

    async def put(self, item: Any, priority: int = 0) -> None:
        """
        放入元素到队列
        
        Args:
            item: 要入队的元素
            priority: 优先级（数值越小越优先）
        """
        # 包装为 (priority, item) 元组，利用 asyncio.PriorityQueue 的排序特性
        await super().put((priority, item))

    async def get(self, timeout: float = 0.01) -> Optional[Any]:
        """
        异步获取队列元素，带超时功能

        Args:
            timeout: 超时时间（秒），默认0.01秒

        Returns:
            队列元素或None(超时)
        """
        try:
            async with asyncio.timeout(timeout if timeout > 0 else None):
                _, item = await super().get()
                return item
        except asyncio.TimeoutError:
            return None

    async def size(self) -> int:
        """
        异步获取队列大小（与 MemoryQueue API 保持一致）
        
        Returns:
            int: 队列中的元素数量
        """
        return super().qsize()

    def qsize(self) -> int:
        """
        同步获取队列大小（asyncio.PriorityQueue 原生方法）
        
        注意：此方法是同步的，因为 asyncio.PriorityQueue.qsize() 不涉及 I/O。
        推荐使用异步的 size() 方法以保持 API 一致性。
        
        Returns:
            int: 队列中的元素数量
        """
        return super().qsize()

    async def close(self) -> None:
        """关闭队列（空实现，用于与Redis队列接口保持一致）"""
        pass


__all__ = [
    'MemoryQueue',
    'DomainAwareQueue',
    'SpiderPriorityQueue',
]
