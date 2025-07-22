#!/usr/bin/python
# -*- coding:UTF-8 -*-
import asyncio
from collections import defaultdict
from inspect import iscoroutinefunction
from typing import Dict, Set, Callable, Coroutine, Any, TypeAlias, List


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
        self._subscribers: Dict[str, Set[ReceiverCoroutine]] = defaultdict(set)

    def subscribe(self, receiver: ReceiverCoroutine, *, event: str) -> None:
        """
        订阅一个事件。

        Args:
            receiver: 一个协程函数 (例如 async def my_func(...))。
            event: 要订阅的事件名称。

        Raises:
            ReceiverTypeError: 如果提供的 `receiver` 不是一个协程函数。
        """
        if not iscoroutinefunction(receiver):
            raise ReceiverTypeError(f"接收者 '{receiver.__qualname__}' 必须是一个协程函数。")
        self._subscribers[event].add(receiver)

    def unsubscribe(self, receiver: ReceiverCoroutine, *, event: str) -> None:
        """
        取消订阅一个事件。

        如果事件或接收者不存在，将静默处理。

        Args:
            receiver: 要取消订阅的协程函数。
            event: 事件名称。
        """
        if event in self._subscribers:
            self._subscribers[event].discard(receiver)

    async def notify(self, event: str, *args, **kwargs) -> List[Any]:
        """
        异步地、并发地通知所有订阅了该事件的接收者。

        此方法会等待所有订阅者任务完成后再返回，并收集所有结果或异常。

        Args:
            event: 要触发的事件名称。
            *args: 传递给接收者的位置参数。
            **kwargs: 传递给接收者的关键字参数。

        Returns:
            一个列表，包含每个订阅者任务的返回结果或在执行期间捕获的异常。
        """
        receivers = self._subscribers.get(event, set())
        if not receivers:
            return []

        tasks = [asyncio.create_task(receiver(*args, **kwargs)) for receiver in receivers]

        # 并发执行所有任务并返回结果列表（包括异常）
        return await asyncio.gather(*tasks, return_exceptions=True)

# #!/usr/bin/python
# # -*- coding:UTF-8 -*-
# import asyncio
# from collections import defaultdict
# from inspect import iscoroutinefunction
# from typing import Dict, Set, Callable, Coroutine
#
# from crawlo.exceptions import ReceiverTypeError
#
#
# class Subscriber:
#
#     def __init__(self):
#         self._subscribers: Dict[str, Set[Callable[..., Coroutine]]] = defaultdict(set)
#
#     def subscribe(self, receiver: Callable[..., Coroutine], *, event: str) -> None:
#         if not iscoroutinefunction(receiver):
#             raise ReceiverTypeError(f"{receiver.__qualname__} must be a coroutine function")
#         self._subscribers[event].add(receiver)
#
#     def unsubscribe(self, receiver: Callable[..., Coroutine], *, event: str) -> None:
#         self._subscribers[event].discard(receiver)
#
#     async def notify(self, event: str, *args, **kwargs) -> None:
#         for receiver in self._subscribers[event]:
#             # 不能 await
#             asyncio.create_task(receiver(*args, **kwargs))
