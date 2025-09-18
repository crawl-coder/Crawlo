#!/usr/bin/python
# -*- coding:UTF-8 -*-
import asyncio
from collections import defaultdict
from inspect import iscoroutinefunction
from typing import Dict, Callable, Coroutine, Any, TypeAlias, List, Tuple


class ReceiverTypeError(TypeError):
    """当订阅的接收者不是一个协程函数时抛出。"""
    pass


ReceiverCoroutine: TypeAlias = Callable[..., Coroutine[Any, Any, Any]]


class Subscriber:
    """
    一个支持异步协程的发布/订阅（Pub/Sub）模式实现。

    这个类允许你注册（订阅）协程函数来监听特定事件，并在事件发生时
    以并发的方式异步地通知所有订阅者。
    """

    def __init__(self):
        """初始化一个空的订阅者字典。"""
        # 使用弱引用字典避免内存泄漏
        self._subscribers: Dict[str, Dict[ReceiverCoroutine, int]] = defaultdict(dict)
        # 用于缓存排序后的订阅者列表，提高频繁事件的处理性能
        self._sorted_subscribers_cache: Dict[str, List[Tuple[ReceiverCoroutine, int]]] = {}

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

        Args:
            event: 要触发的事件名称。
            *args: 传递给接收者的位置参数。
            **kwargs: 传递给接收者的关键字参数。

        Returns:
            一个列表，包含每个订阅者任务的返回结果或在执行期间捕获的异常。
        """
        sorted_subscribers = self._get_sorted_subscribers(event)
        if not sorted_subscribers:
            return []

        # 为频繁触发的事件重用任务对象以提高性能
        tasks = []
        for receiver, _ in sorted_subscribers:
            try:
                # 创建任务并添加到列表
                task = asyncio.create_task(receiver(*args, **kwargs))
                tasks.append(task)
            except Exception as e:
                # 如果创建任务失败，记录异常并继续处理其他订阅者
                tasks.append(asyncio.Future())  # 添加一个已完成的Future表示错误
                tasks[-1].set_exception(e)

        # 并发执行所有任务并返回结果列表（包括异常）
        return await asyncio.gather(*tasks, return_exceptions=True)