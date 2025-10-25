#!/usr/bin/python
# -*- coding:UTF-8 -*-
from typing import List
from pprint import pformat
from asyncio import create_task

from crawlo.logging import get_logger
from crawlo.event import CrawlerEvent
from crawlo.utils.misc import load_object
from crawlo.project import common_call
from crawlo.exceptions import PipelineInitError, ItemDiscard, InvalidOutputError


def get_dedup_pipeline_classes():
    """获取所有已知的去重管道类名"""
    return [
        'crawlo.pipelines.memory_dedup_pipeline.MemoryDedupPipeline',
        'crawlo.pipelines.redis_dedup_pipeline.RedisDedupPipeline',
        'crawlo.pipelines.bloom_dedup_pipeline.BloomDedupPipeline',
        'crawlo.pipelines.database_dedup_pipeline.DatabaseDedupPipeline'
    ]


def remove_dedup_pipelines(pipelines: List[str]) -> List[str]:
    """从管道列表中移除所有去重管道"""
    dedup_classes = get_dedup_pipeline_classes()
    return [pipeline for pipeline in pipelines if pipeline not in dedup_classes]


class PipelineManager:

    def __init__(self, crawler):
        self.crawler = crawler
        self.pipelines: List = []
        self.methods: List = []

        self.logger = get_logger(self.__class__.__name__)
        pipelines = self.crawler.settings.get_list('PIPELINES')
        dedup_pipeline = self.crawler.settings.get('DEFAULT_DEDUP_PIPELINE')

        # 添加调试信息
        self.logger.debug(f"PIPELINES from settings: {pipelines}")
        self.logger.debug(f"DEFAULT_DEDUP_PIPELINE from settings: {dedup_pipeline}")

        # 确保DEFAULT_DEDUP_PIPELINE被添加到管道列表开头
        if dedup_pipeline:
            # 移除所有去重管道实例（如果存在）
            pipelines = remove_dedup_pipelines(pipelines)
            # 在开头插入去重管道
            self.logger.debug(f"{dedup_pipeline} insert successful")
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
                pipeline_cls = load_object(pipeline)
                if not hasattr(pipeline_cls, 'from_crawler'):
                    raise PipelineInitError(
                        f"Pipeline init failed, must inherit from `BasePipeline` or have a `from_crawler` method"
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
            for i, method in enumerate(self.methods):
                self.logger.debug(f"Processing item with pipeline method {i}: {method.__qualname__}")
                try:
                    item = await common_call(method, item, self.crawler.spider)
                    if item is None:
                        raise InvalidOutputError(f"{method.__qualname__} return None is not supported.")
                except ItemDiscard as exc:
                    self.logger.debug(f"Item discarded by pipeline: {exc}")
                    create_task(self.crawler.subscriber.notify(CrawlerEvent.ITEM_DISCARD, item, exc, self.crawler.spider))
                    # 重新抛出异常，确保上层调用者也能捕获到，并停止执行后续管道
                    raise
        except ItemDiscard:
            # 异常已经被处理和通知，这里只需要重新抛出
            raise
        else:
            create_task(self.crawler.subscriber.notify(CrawlerEvent.ITEM_SUCCESSFUL, item, self.crawler.spider))
