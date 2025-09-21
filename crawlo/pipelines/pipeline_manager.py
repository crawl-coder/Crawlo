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
        dedup_pipeline = self.crawler.settings.get('DEFAULT_DEDUP_PIPELINE')

        # 添加调试信息
        self.logger.debug(f"PIPELINES from settings: {pipelines}")
        self.logger.debug(f"DEFAULT_DEDUP_PIPELINE from settings: {dedup_pipeline}")

        # 确保DEFAULT_DEDUP_PIPELINE被添加到管道列表开头
        if dedup_pipeline:
            # 移除所有去重管道实例（如果存在）
            pipelines = [item for item in pipelines if item != dedup_pipeline]
            # 在开头插入去重管道
            pipelines.insert(0, dedup_pipeline)

        self._add_pipelines(pipelines)
        self._add_methods()

    @classmethod
    def from_crawler(cls, *args, **kwargs):
        o = cls(*args, **kwargs)
        return o

    def _add_pipelines(self, pipelines):
        for pipeline in pipelines:
            try:
                pipeline_cls = load_class(pipeline)
                if not hasattr(pipeline_cls, 'from_crawler'):
                    raise PipelineInitError(
                        f"Pipeline init failed, must inherit from `BasePipeline` or have a `create_instance` method"
                    )
                self.pipelines.append(pipeline_cls.from_crawler(self.crawler))
            except Exception as e:
                self.logger.error(f"Failed to load pipeline {pipeline}: {e}")
                # 可以选择继续加载其他管道或抛出异常
                raise
        if pipelines:
            # 恢复INFO级别日志，保留关键的启用信息
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
