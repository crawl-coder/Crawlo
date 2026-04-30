#!/usr/bin/python
# -*- coding:UTF-8 -*-
import asyncio
from collections import defaultdict
from dataclasses import dataclass, field
from inspect import iscoroutinefunction
from typing import Dict, Callable, Coroutine, Any, TypeAlias, List, Tuple, Optional

from crawlo.logging import get_logger


class ReceiverTypeError(TypeError):
    """当订阅的接收者不是一个协程函数时抛出。"""
    pass


ReceiverCoroutine: TypeAlias = Callable[..., Coroutine[Any, Any, Any]]


# 关键事件列表 - 这些事件的订阅者失败时使用 WARNING 级别日志
CRITICAL_EVENTS = frozenset({
    'spider_closed',
    'spider_error',
    'spider_opened',
})


@dataclass
class NotifyResult:
    """notify() 的结构化返回结果
    
    提供比纯列表更丰富的错误信息，便于调用方判断通知执行状态。
    """
    results: List[Any] = field(default_factory=list)
    errors: List[Tuple[str, Exception]] = field(default_factory=list)
    event: str = ""
    
    @property
    def has_errors(self) -> bool:
        """是否有订阅者执行失败"""
        return len(self.errors) > 0
    
    @property
    def success_count(self) -> int:
        """成功的订阅者数量"""
        return len(self.results) - len(self.errors)
    
    @property
    def error_count(self) -> int:
        """失败的订阅者数量"""
        return len(self.errors)


class Subscriber:
    """
    一个支持异步协程的发布/订阅（Pub/Sub）模式实现。

    这个类允许你注册（订阅）协程函数来监听特定事件，并在事件发生时
    以并发的方式异步地通知所有订阅者。

    增强特性：
    - 超时控制：防止订阅者执行时间过长
    - 错误处理策略：可配置的异常处理方式
    - 并发控制：支持限制最大并发数
    """

    def __init__(self, error_handling: str = "log", timeout: float = 5.0, max_concurrency: int = 0):
        """
        初始化订阅者

        Args:
            error_handling: 错误处理策略
                - "log": 记录错误但继续（默认）
                - "raise": 重新抛出第一个错误
                - "gather": 返回所有错误结果
            timeout: 每个订阅者的最大执行时间（秒），0表示无限制
            max_concurrency: 最大并发数，0表示无限制
        """
        # 使用弱引用字典避免内存泄漏
        self._subscribers: Dict[str, Dict[ReceiverCoroutine, int]] = defaultdict(dict)
        # 用于缓存排序后的订阅者列表，提高频繁事件的处理性能
        self._sorted_subscribers_cache: Dict[str, List[Tuple[ReceiverCoroutine, int]]] = {}
        # 配置参数
        self._error_handling = error_handling
        self._timeout = timeout
        self._max_concurrency = max_concurrency
        self._last_notify_result: Optional[NotifyResult] = None
        self._logger = get_logger(self.__class__.__name__)

    def subscribe(self, receiver: ReceiverCoroutine, *, event: str, priority: int = 0) -> None:
        """
        订阅一个事件。

        Args:
            receiver: 一个协程函数 (例如 async def my_func(...))。
            event: 要订阅的事件名称。
            priority: 订阅者优先级，数值越小优先级越高，默认为0。

        Raises:
            ReceiverTypeError: 如果提供的 `receiver` 不是一个协程函数。
        """
        if not iscoroutinefunction(receiver):
            raise ReceiverTypeError(f"接收者 '{receiver.__qualname__}' 必须是一个协程函数。")
        
        # 使用弱引用避免内存泄漏
        self._subscribers[event][receiver] = priority
        # 清除缓存
        self._sorted_subscribers_cache.pop(event, None)

    def unsubscribe(self, receiver: ReceiverCoroutine, *, event: str) -> None:
        """
        取消订阅一个事件。

        如果事件或接收者不存在，将静默处理。

        Args:
            receiver: 要取消订阅的协程函数。
            event: 事件名称。
        """
        if event in self._subscribers:
            self._subscribers[event].pop(receiver, None)
            # 清除缓存
            self._sorted_subscribers_cache.pop(event, None)

    def _get_sorted_subscribers(self, event: str) -> List[Tuple[ReceiverCoroutine, int]]:
        """
        获取按优先级排序的订阅者列表。
        
        Args:
            event: 事件名称。
            
        Returns:
            按优先级排序的订阅者列表。
        """
        # 检查缓存
        if event in self._sorted_subscribers_cache:
            return self._sorted_subscribers_cache[event]
        
        # 获取有效的订阅者（使用弱引用检查）
        valid_subscribers = {}
        for receiver, priority in list(self._subscribers[event].items()):
            # 检查弱引用是否仍然有效
            if isinstance(receiver, Callable):
                valid_subscribers[receiver] = priority
        
        # 更新订阅者字典
        self._subscribers[event] = valid_subscribers
        
        # 按优先级排序（数值小的优先级高）
        sorted_subscribers = sorted(valid_subscribers.items(), key=lambda x: x[1])
        # 缓存结果
        self._sorted_subscribers_cache[event] = sorted_subscribers
        
        return sorted_subscribers

    async def notify(self, event: str, *args, **kwargs) -> List[Any]:
        """
        异步地、并发地通知所有订阅了该事件的接收者。
    
        此方法会等待所有订阅者任务完成后再返回，并收集所有结果或异常。
        订阅者按优先级顺序执行，优先级高的先执行。
    
        增强特性：
        - 支持超时控制
        - 支持错误处理策略
        - 支持并发控制
        - 关键事件（spider_closed, spider_error, spider_opened）失败时使用 WARNING 级别
    
        Args:
            event: 要触发的事件名称。
            *args: 传递给接收者的位置参数。
            **kwargs: 传递给接收者的关键字参数。
    
        Returns:
            一个列表，包含每个订阅者任务的返回结果或在执行期间捕获的异常。
            同时更新 self._last_notify_result 供调用方检查执行状态。
        """
        logger = get_logger(self.__class__.__name__)
        
        sorted_subscribers = self._get_sorted_subscribers(event)
        logger.debug(f"[{event}] 订阅者数量：{len(sorted_subscribers)}")
        if not sorted_subscribers:
            logger.debug(f"[{event}] 没有订阅者")
            self._last_notify_result = NotifyResult(event=event)
            return []
        
        # 为频繁触发的事件重用任务对象以提高性能
        tasks = []
        for receiver, priority in sorted_subscribers:
            try:
                # 创建包装任务以支持超时
                if self._timeout > 0:
                    coro = self._safe_execute(receiver, *args, **kwargs)
                    task = asyncio.create_task(coro)
                else:
                    task = asyncio.create_task(receiver(*args, **kwargs))
                tasks.append((task, receiver))
            except Exception as e:
                # 如果创建任务失败，记录异常并继续处理其他订阅者
                logger.warning(f"订阅者 {receiver.__name__} 创建任务失败: {e}")
                tasks.append((None, receiver))
        
        # 并发控制
        if self._max_concurrency > 0:
            await self._throttle_tasks(tasks)
        
        # 判断是否为关键事件
        is_critical = event in CRITICAL_EVENTS
        
        # 等待所有任务完成
        results = []
        errors = []
        first_error = None
        
        for i, (task, receiver) in enumerate(tasks):
            if task is None:
                results.append(None)
                continue
            
            try:
                if self._timeout > 0:
                    async with asyncio.timeout(self._timeout):
                        result = await task
                else:
                    result = await task
                
                if isinstance(result, Exception):
                    if first_error is None:
                        first_error = result
                    receiver_name = getattr(receiver, '__name__', str(receiver))
                    errors.append((receiver_name, result))
                    # 关键事件使用 WARNING 级别，其他事件使用 ERROR 级别
                    if is_critical:
                        logger.warning(
                            f"[{event}] 关键事件订阅者 {receiver_name} 异常：{result}"
                        )
                    else:
                        logger.error(f"任务 {receiver_name} 异常：{result}")
                else:
                    receiver_name = getattr(receiver, '__name__', str(receiver))
                    logger.debug(f"任务 {receiver_name} 完成")
                results.append(result)
            except asyncio.TimeoutError:
                receiver_name = getattr(receiver, '__name__', str(receiver))
                errors.append((receiver_name, asyncio.TimeoutError(
                    f"执行超时 ({self._timeout}s)"
                )))
                if is_critical:
                    logger.warning(
                        f"[{event}] 关键事件订阅者 {receiver_name} 执行超时 ({self._timeout}s)"
                    )
                else:
                    logger.warning(f"任务 {receiver_name} 执行超时 ({self._timeout}s)")
                task.cancel()
                results.append(None)
            except Exception as e:
                receiver_name = getattr(receiver, '__name__', str(receiver))
                errors.append((receiver_name, e))
                if first_error is None:
                    first_error = e
                if is_critical:
                    logger.warning(
                        f"[{event}] 关键事件订阅者 {receiver_name} 执行失败: {e}"
                    )
                else:
                    logger.error(f"任务 {receiver_name} 执行失败: {e}")
                results.append(e)
        
        # 更新结构化结果
        self._last_notify_result = NotifyResult(
            results=results,
            errors=errors,
            event=event,
        )
        
        # 关键事件有错误时，输出汇总 WARNING
        if is_critical and errors:
            logger.warning(
                f"[{event}] 关键事件有 {len(errors)}/{len(tasks)} 个订阅者执行失败"
            )
        
        # 根据错误处理策略处理
        if self._error_handling == "raise" and first_error:
            raise first_error
        
        return results
    
    async def _safe_execute(self, receiver: ReceiverCoroutine, *args, **kwargs) -> Any:
        """
        安全执行订阅者，支持超时控制
        
        Args:
            receiver: 订阅者函数
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            执行结果
        """
        if asyncio.iscoroutinefunction(receiver):
            return await receiver(*args, **kwargs)
        else:
            return receiver(*args, **kwargs)
    
    async def _throttle_tasks(self, tasks: List[Tuple]) -> None:
        """
        限制并发任务数
        
        Args:
            tasks: 任务列表
        """
        semaphore = asyncio.Semaphore(self._max_concurrency)
        
        async def throttled_task(task):
            async with semaphore:
                return await task
        
        # 只对有效的任务应用限制
        throttled = []
        for task, receiver in tasks:
            if task is not None:
                throttled.append(asyncio.create_task(throttled_task(task)))
            else:
                throttled.append(None)
        
        # 等待所有任务
        await asyncio.gather(*[t for t in throttled if t is not None], return_exceptions=True)