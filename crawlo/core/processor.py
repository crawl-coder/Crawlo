#!/usr/bin/python
# -*- coding:UTF-8 -*-
from asyncio import Queue
from typing import Union, Optional

from crawlo import Request, Item
from crawlo.exceptions import ItemDiscard
from crawlo.pipelines.pipeline_manager import PipelineManager


class Processor(object):

    def __init__(self, crawler):
        self.crawler = crawler
        self.queue: Queue = Queue()
        self.pipelines: Optional[PipelineManager] = None

    async def open(self):
        self.pipelines = await PipelineManager.from_crawler(self.crawler)

    async def process(self):
        while not self.idle():
            result = await self.queue.get()
            if isinstance(result, Request):
                await self.crawler.engine.enqueue_request(result)
            else:
                assert isinstance(result, Item)
                await self._process_item(result)

    async def _process_item(self, item):
        try:
            await self.pipelines.process_item(item=item)
        except ItemDiscard as exc:
            # 项目被管道丢弃（例如，去重管道）
            # 我们忽略这个项目，不传递给后续管道
            # 统计系统已在PipelineManager中通知，无需再次通知
            pass

    async def enqueue(self, output: Union[Request, Item]):
        await self.queue.put(output)
        await self.process()

    def idle(self) -> bool:
        return len(self) == 0

    def __len__(self):
        return self.queue.qsize()