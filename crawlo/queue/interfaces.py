#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
统一的队列接口定义

提供所有队列实现的抽象基类，确保不同队列类型有一致的接口。

包含两套接口：
  - IQueue (ABC)：通用队列抽象基类（完整接口，含背压、close、wait 等）
  - IRequestQueue (Protocol)：请求队列 Protocol 接口（结构类型，最小化接口）
"""
import asyncio
import time
from abc import ABC, abstractmethod
from typing import Optional, Any, AsyncIterator, Protocol, runtime_checkable, TYPE_CHECKING

from crawlo.queue.queue_types import QueueStats
from crawlo.queue.exceptions import QueueClosedError, QueueFullError, QueueEmptyError

if TYPE_CHECKING:
    from crawlo.http.request import Request

# 注意：所有 IRequestQueue 签名使用 ``'Request'`` 字符串注解。
# 不在 TYPE_CHECKING 中 ``from crawlo.network.request import Request``，
# 避免 lint-imports 计为 crawlo.queue -> crawlo.network 违规。


class IQueue(ABC):
    """
    统一的队列接口
    
    所有队列实现必须继承此接口并实现其方法。
    
    使用示例：
        class MemoryQueue(IQueue):
            async def put(self, item, priority=0):
                # 实现入队逻辑
                pass
            
            async def get(self, timeout=None):
                # 实现出队逻辑
                pass
            
            async def size(self) -> int:
                # 返回队列大小
                pass
    """
    
    def __init__(self, max_size: int = 0, name: str = "default"):
        """
        初始化队列
        
        Args:
            max_size: 最大队列大小，0 表示无限制
            name: 队列名称
        """
        self._max_size = max_size
        self._name = name
        self._stats = QueueStats()
        self._closed = False
    
    @property
    def max_size(self) -> int:
        """获取最大队列大小"""
        return self._max_size
    
    @property
    def name(self) -> str:
        """获取队列名称"""
        return self._name
    
    @property
    def stats(self) -> QueueStats:
        """获取队列统计信息"""
        return self._stats
    
    @property
    def is_closed(self) -> bool:
        """检查队列是否已关闭"""
        return self._closed
    
    @abstractmethod
    async def put(self, item: Any, priority: int = 0) -> bool:
        """
        入队操作
        
        Args:
            item: 要入队的元素
            priority: 优先级，数值越小越优先（与 asyncio.PriorityQueue 最小堆语义一致）
            
        Returns:
            bool: 入队是否成功
            
        Raises:
            QueueClosedError: 队列已关闭时抛出
        """
    
    @abstractmethod
    async def get(self, timeout: Optional[float] = None) -> Optional[Any]:
        """
        出队操作
        
        Args:
            timeout: 超时时间（秒），None 表示无限等待
            
        Returns:
            出队的元素，如果超时返回 None
            
        Raises:
            QueueClosedError: 队列已关闭时抛出
        """
    
    @abstractmethod
    async def size(self) -> int:
        """
        获取队列大小
        
        Returns:
            int: 当前队列中的元素数量
        """
    
    @abstractmethod
    async def empty(self) -> bool:
        """
        检查队列是否为空
        
        Returns:
            bool: 队列是否为空
        """
    
    async def close(self) -> None:
        """
        关闭队列
        
        关闭后队列将不再接受新的入队操作，
        但可以继续出队直到队列为空。
        """
        self._closed = True
        self._stats.mark_end()
    
    async def clear(self) -> None:
        """
        清空队列
        
        删除队列中的所有元素。
        """
        while not await self.empty():
            await self.get(timeout=0.01)
    
    async def wait_until_empty(self, timeout: Optional[float] = None) -> bool:
        """
        等待队列变空
        
        Args:
            timeout: 超时时间（秒）
            
        Returns:
            bool: 队列是否已变空（True）或超时（False）
        """
        start_time = time.time()
        while not await self.empty():
            if timeout and (time.time() - start_time) > timeout:
                return False
            await asyncio.sleep(0.1)
        return True
    
    async def wait_until_full(self, timeout: Optional[float] = None) -> bool:
        """
        等待队列变满
        
        Args:
            timeout: 超时时间（秒）
            
        Returns:
            bool: 队列是否已变满（True）或超时（False）
        """
        if self._max_size <= 0:
            return False
        
        start_time = time.time()
        while await self.size() < self._max_size:
            if timeout and (time.time() - start_time) > timeout:
                return False
            await asyncio.sleep(0.1)
        return True
    
    def __len__(self) -> int:
        """同步获取队列大小（可能不准确，取决于实现）"""
        return 0  # 默认返回 0，子类可以重写
    
    def __aiter__(self) -> AsyncIterator:
        """异步迭代器支持"""
        return self
    
    async def __anext__(self) -> Any:
        """异步迭代器下一步"""
        if self._closed and await self.empty():
            raise StopAsyncIteration
        
        result = await self.get(timeout=1.0)
        if result is None and self._closed:
            raise StopAsyncIteration
        return result


class BackpressureableQueueMixin(ABC):
    """
    支持背压的队列混入类
    
    提供背压控制的回退基础设施。
    当 QueueManager 已配置了统一的 BackpressureController 时，
    通过设置 _bp_delegate 委托给它，避免重复计算。
    """
    
    def __init__(self, *args, max_size: int = 0, **kwargs):
        # 转发到 MRO 中的下一个基类（如 IQueue.__init__，负责 _stats/_name 等）
        super().__init__(*args, **kwargs)  # type: ignore[call-overload]
        self._max_size = max_size
        self._backpressure_enabled = True
        self._backpressure_threshold = 0.8  # 回退阈值
        self._backpressure_active = False
        self._last_backpressure_check: float = 0
        self._backpressure_check_interval = 0.1
        self._bp_delegate = None  # 可由 QueueManager 注入统一的 BackpressureController

    size: Any  # 由具体队列后端（IQueue 等）实现
    
    @property
    def max_size(self) -> int:
        """获取最大队列大小"""
        return self._max_size
    
    @property
    def backpressure_enabled(self) -> bool:
        """是否启用背压"""
        return self._backpressure_enabled
    
    @backpressure_enabled.setter
    def backpressure_enabled(self, value: bool) -> None:
        """设置背压启用状态"""
        self._backpressure_enabled = value
    
    @property
    def backpressure_threshold(self) -> float:
        """获取背压触发阈值"""
        return self._backpressure_threshold
    
    @backpressure_threshold.setter
    def backpressure_threshold(self, value: float) -> None:
        """设置背压触发阈值"""
        if 0 < value <= 1.0:
            self._backpressure_threshold = value
    
    @property
    def backpressure_active(self) -> bool:
        """是否正在应用背压"""
        return self._backpressure_active
    
    async def should_apply_backpressure(self) -> bool:
        """
        检查是否应该应用背压
        
        优先委托给 QueueManager 注入的统一 BackpressureController，
        避免与 QueueSizeStrategy 重复计算。
        
        Returns:
            bool: 是否应该应用背压
        """
        if not self._backpressure_enabled:
            return False

        # 如果 QueueManager 注入了统一控制器，委托给它
        if self._bp_delegate is not None:
            return await self._bp_delegate.should_apply(self)

        # 回退：使用内置简单逻辑
        current_time = time.time()
        if current_time - self._last_backpressure_check < self._backpressure_check_interval:
            return self._backpressure_active

        self._last_backpressure_check = current_time

        if self._max_size <= 0:
            return False

        queue_size = await self.size()
        utilization = queue_size / self._max_size
        should_backpressure = utilization >= self._backpressure_threshold

        if should_backpressure != self._backpressure_active:
            self._backpressure_active = should_backpressure
            self._on_backpressure_state_change(should_backpressure)

        return self._backpressure_active
    
    def _on_backpressure_state_change(self, active: bool) -> None:
        """
        背压状态变更回调
        
        子类可以重写此方法来处理背压状态变更。
        
        Args:
            active: 新的背压状态
        """
    
    async def calculate_backpressure_delay(self) -> float:
        """
        计算背压延迟
        
        优先委托给 QueueManager 注入的统一 BackpressureController。
        
        Returns:
            float: 延迟时间（秒），0 表示不需要延迟
        """
        # 如果 QueueManager 注入了统一控制器，委托给它
        if self._bp_delegate is not None:
            if await self._bp_delegate.should_apply(self):
                return await self._bp_delegate.calculate_delay(self)
            return 0.0

        # 回退：使用内置简单逻辑
        if not await self.should_apply_backpressure():
            return 0.0

        if self._max_size <= 0:
            return 0.0

        queue_size = await self.size()
        utilization = queue_size / self._max_size

        if utilization >= 0.95:
            return 2.0
        elif utilization >= 0.90:
            return 1.0
        elif utilization >= self._backpressure_threshold:
            ratio = (utilization - self._backpressure_threshold) / (0.95 - self._backpressure_threshold)
            return 0.1 + ratio * 0.9
        else:
            return 0.0


__all__ = [
    'IQueue',
    'QueueClosedError',
    'QueueFullError',
    'QueueEmptyError',
    'BackpressureableQueueMixin',
    # Protocol 版最小化请求队列接口（原 crawlo.interfaces.IQueue）
    'IRequestQueue',
]


# ==================== 请求队列 Protocol 接口 ====================
# （原 crawlo.interfaces.IQueue，结构类型，最小化 4 方法契约）

@runtime_checkable
class IRequestQueue(Protocol):
    """
    请求队列接口（Protocol 版本，结构类型）

    负责请求的存储和获取，支持多种后端实现。

    实现示例：
        class RedisQueue(IRequestQueue):
            async def put(self, request: "Request") -> None:
                await self.redis.lpush(self.key, serialize(request))

            async def get(self) -> "Optional[Request]":
                data = await self.redis.rpop(self.key)
                return deserialize(data) if data else None
    """

    async def put(self, request: 'Request') -> None:
        """
        将请求加入队列

        Args:
            request: 请求对象
        """
        ...

    async def get(self) -> 'Optional[Request]':
        """
        从队列获取请求

        Returns:
            Optional[Request]: 请求对象，队列为空时返回 None
        """
        ...

    def qsize(self) -> int:
        """
        获取队列大小

        Returns:
            int: 队列中请求数量
        """
        ...

    async def clear(self) -> None:
        """
        清空队列
        """
        ...
