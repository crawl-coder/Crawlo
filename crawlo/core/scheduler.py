#!/usr/bin/python
# -*- coding:UTF-8 -*-
import asyncio
from typing import Optional
from asyncio import PriorityQueue, TimeoutError

from crawlo.utils.pqueue import SpiderPriorityQueue


class Scheduler:
    def __init__(self):
        self.request_queue: Optional[SpiderPriorityQueue] = None

    def open(self):
        self.request_queue = SpiderPriorityQueue()

    async def next_request(self):
        request = await self.request_queue.get()
        return request

    async def enqueue_request(self, request):
        await self.request_queue.put(request)

    def idle(self) -> bool:
        return len(self) == 0

    def __len__(self):
        return self.request_queue.qsize()
