#!/usr/bin/python
# -*- coding:UTF-8 -*-
import asyncio
from collections import defaultdict
from inspect import iscoroutinefunction
from typing import Dict, Set, Callable, Coroutine

from crawlo.exceptions import ReceiverTypeError


class Subscriber:

    def __init__(self):
        self._subscribers: Dict[str, Set[Callable[..., Coroutine]]] = defaultdict(set)

    def subscribe(self, receiver: Callable[..., Coroutine], *, event: str) -> None:
        if not iscoroutinefunction(receiver):
            raise ReceiverTypeError(f"{receiver.__qualname__} must be a coroutine function")
        self._subscribers[event].add(receiver)

    def unsubscribe(self, receiver: Callable[..., Coroutine], *, event: str) -> None:
        self._subscribers[event].discard(receiver)

    async def notify(self, event: str, *args, **kwargs) -> None:
        for receiver in self._subscribers[event]:
            # 不能 await
            asyncio.create_task(receiver(*args, **kwargs))
