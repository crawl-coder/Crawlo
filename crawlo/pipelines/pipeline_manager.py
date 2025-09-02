#!/usr/bin/python
# -*- coding:UTF-8 -*-
from typing import List
from pprint import pformat
from asyncio import create_task


from crawlo.utils.log import get_logger
from crawlo.event import item_successful, item_discard
from crawlo.project import load_class, common_call
from crawlo.exceptions import PipelineInitError, ItemDiscard, InvalidOutputError


class PipelineManager:

    def __init__(self, crawler):
        self.crawler = crawler
        self.pipelines: List = []
        self.methods: List = []

        self.logger = get_logger(self.__class__.__name__, self.crawler.settings.get('LOG_LEVEL'))
        pipelines = self.crawler.settings.get_list('PIPELINES')
        self._add_pipelines(pipelines)
        self._add_methods()

    @classmethod
    def from_crawler(cls, *args, **kwargs):
        o = cls(*args, **kwargs)
        return o

    def _add_pipelines(self, pipelines):
        for pipeline in pipelines:
            pipeline_cls = load_class(pipeline)
            if not hasattr(pipeline_cls, 'from_crawler'):
                raise PipelineInitError(
                    f"Pipeline init failed, must inherit from `BasePipeline` or have a `create_instance` method"
                )
            self.pipelines.append(pipeline_cls.from_crawler(self.crawler))
        if pipelines:
            self.logger.info(f"enabled pipelines: \n {pformat(pipelines)}")

    def _add_methods(self):
        for pipeline in self.pipelines:
            if hasattr(pipeline, 'process_item'):
                self.methods.append(pipeline.process_item)

    async def process_item(self, item):
        try:
            for method in self.methods:
                item = await common_call(method, item, self.crawler.spider)
                if item is None:
                    raise InvalidOutputError(f"{method.__qualname__} return None is not supported.")
        except ItemDiscard as exc:
            create_task(self.crawler.subscriber.notify(item_discard, item, exc, self.crawler.spider))
        else:
            create_task(self.crawler.subscriber.notify(item_successful, item, self.crawler.spider))
