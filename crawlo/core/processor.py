#!/usr/bin/python
# -*- coding:UTF-8 -*-
from asyncio import Queue, create_task
from typing import Union, Optional

from crawlo import Request, Item
from crawlo.pipelines.pipeline_manager import PipelineManager
from crawlo.exceptions import ItemDiscard
from crawlo.event import item_discard


class Processor(object):

    def __init__(self, crawler):
        self.crawler = crawler
        self.queue: Queue = Queue()
        self.pipelines: Optional[PipelineManager] = None

    def open(self):
        self.pipelines = PipelineManager.from_crawler(self.crawler)

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
            # Item was discarded by a pipeline (e.g., deduplication pipeline)
            # We simply ignore this item and don't pass it to subsequent pipelines
            # The statistics system has already been notified in PipelineManager, so we don't need to notify again
            pass

    async def enqueue(self, output: Union[Request, Item]):
        await self.queue.put(output)
        await self.process()

    def idle(self) -> bool:
        return len(self) == 0

    def __len__(self):
        return self.queue.qsize()