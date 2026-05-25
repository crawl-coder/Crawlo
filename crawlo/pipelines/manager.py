#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
Pipeline 管理器
===============
支持字典格式（带优先级）和列表格式（向后兼容）。

配置格式：
    # 推荐：字典格式（数字越小越先执行）
    PIPELINES = {
        'crawlo.pipelines.MemoryDedupPipeline': 100,  # 去重，最先执行
        'crawlo.pipelines.ConsolePipeline': 500,      # 输出
        'myproject.pipelines.MySQLPipeline': 800,     # 存储，最后执行
    }
    
    # 兼容：列表格式（按顺序执行）
    PIPELINES = [
        'crawlo.pipelines.MemoryDedupPipeline',
        'crawlo.pipelines.ConsolePipeline',
    ]
"""
from typing import List, Dict, Union
from asyncio import create_task

from crawlo.logging import get_logger
from crawlo.event import CrawlerEvent
from crawlo.utils.misc import load_object
from crawlo.project import common_call
from crawlo.exceptions import PipelineInitError, ItemDiscard, InvalidOutputError


def get_dedup_pipeline_classes():
    """获取所有已知的去重管道类名（含子包路径和短路径）"""
    return [
        'crawlo.pipelines.dedup.memory.MemoryDedupPipeline',
        'crawlo.pipelines.MemoryDedupPipeline',
        'crawlo.pipelines.dedup.redis.RedisDedupPipeline',
        'crawlo.pipelines.RedisDedupPipeline',
        'crawlo.pipelines.dedup.bloom.BloomDedupPipeline',
        'crawlo.pipelines.BloomDedupPipeline',
        'crawlo.pipelines.dedup.mysql.DatabaseDedupPipeline',
        'crawlo.pipelines.dedup.mysql.MySQLDedupPipeline',
    ]


def normalize_pipelines_config(
    config: Union[Dict, List, None]
) -> List[tuple]:
    """
    将管道配置标准化为 (path, priority) 元组列表
    
    Args:
        config: 管道配置（字典/列表）
        
    Returns:
        List[tuple]: 按优先级排序的 (path, priority) 列表
    """
    if not config:
        return []
    
    if isinstance(config, dict):
        # 验证字典格式配置
        _validate_pipeline_priorities(config)
        
        # 字典格式：按优先级排序（数字越小越先执行）
        items = [(path, priority) for path, priority in config.items()]
        items.sort(key=lambda x: x[1])  # 升序，数字小的先执行
        return items
    else:
        # 列表格式：保持顺序，默认优先级 500
        return [(path, 500 + i) for i, path in enumerate(config) if isinstance(path, str)]


def _validate_pipeline_priorities(config: dict):
    """
    验证管道优先级配置
    
    Args:
        config: 字典格式的管道配置
        
    Raises:
        ValueError: 优先级配置无效
    """
    logger = get_logger('PipelineManager')
    priorities = {}
    
    for path, priority in config.items():
        # 验证优先级类型
        if not isinstance(priority, (int, float)):
            raise ValueError(
                f"Pipeline priority must be numeric, got {type(priority).__name__} "
                f"for {path}: {priority}"
            )
        
        # 验证优先级范围
        if priority < 0:
            raise ValueError(
                f"Pipeline priority must be non-negative, got {priority} for {path}"
            )
        
        # 检查重复优先级
        if priority in priorities:
            logger.warning(
                f"Duplicate pipeline priority {priority}: "
                f"{priorities[priority]} and {path}"
            )
        else:
            priorities[priority] = path


class PipelineManager:

    def __init__(self, crawler):
        self.crawler = crawler
        self.pipelines: List = []
        self.methods: List = []

        self.logger = get_logger(self.__class__.__name__)
        # 支持字典和列表两种格式
        self.pipelines_settings = self.crawler.settings.get('PIPELINES', {})
        self.dedup_pipeline = self.crawler.settings.get('DEFAULT_DEDUP_PIPELINE')

        # 添加调试信息
        self.logger.debug(f"PIPELINES from settings: {self.pipelines_settings}")

    async def _initialize(self):
        """异步初始化管道"""
        # 标准化配置
        pipelines = normalize_pipelines_config(self.pipelines_settings)
        
        # 处理去重管道
        if self.dedup_pipeline:
            # 移除所有去重管道实例
            dedup_classes = get_dedup_pipeline_classes()
            pipelines = [(p, pri) for p, pri in pipelines if p not in dedup_classes]
            # 在开头插入去重管道（最高优先级：1）
            pipelines.insert(0, (self.dedup_pipeline, 1))
            self.logger.debug(f"{self.dedup_pipeline} inserted with priority 1")
        
        await self._add_pipelines(pipelines)
        self._add_methods()

    @classmethod
    async def from_crawler(cls, *args, **kwargs):
        o = cls(*args, **kwargs)
        await o._initialize()
        return o

    async def _add_pipelines(self, pipelines: List[tuple]):
        """加载并初始化管道"""
        for pipeline_path, priority in pipelines:
            try:
                pipeline_cls = load_object(pipeline_path)
                if not hasattr(pipeline_cls, 'from_crawler'):
                    raise PipelineInitError(
                        f"Pipeline init failed, must inherit from `BasePipeline` or have a `from_crawler` method"
                    )
                # 处理同步和异步的from_crawler方法
                result = pipeline_cls.from_crawler(self.crawler)
                # 检查是否是协程对象
                if hasattr(result, '__await__'):
                    instance = await result
                else:
                    instance = result
                self.pipelines.append(instance)
            except Exception as e:
                self.logger.error(f"Failed to load pipeline {pipeline_path}: {e}")
                raise
        
        if pipelines:
            # 显示加载的管道及优先级（类似中间件的多行字典格式）
            if len(pipelines) == 1:
                pipeline_path, priority = pipelines[0]
                self.logger.info(f"enabled pipelines: {{{pipeline_path!r}: {priority}}}")
            else:
                formatted_output = '{\n'
                for i, (pipeline_path, priority) in enumerate(pipelines):
                    is_last = (i == len(pipelines) - 1)
                    comma = ',' if not is_last else ''
                    formatted_output += f"  {pipeline_path!r}: {priority}{comma}\n"
                formatted_output += '}'
                self.logger.info(f"enabled pipelines:\n{formatted_output}")

    def _add_methods(self):
        for pipeline in self.pipelines:
            if hasattr(pipeline, 'process_item'):
                self.methods.append(pipeline.process_item)

    async def process_item(self, item):
        try:
            for method in self.methods:
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

    async def close(self):
        """关闭所有 pipeline，清理资源（防重复清理）"""
        for pipeline in self.pipelines:
            try:
                # 防重复清理（_on_spider_closed 可能已触发过）
                if getattr(pipeline, '_cleaned_up', False):
                    continue

                # 1. 调用 pipeline 的自定义清理逻辑
                if hasattr(pipeline, '_cleanup_resources'):
                    await pipeline._cleanup_resources()
                elif hasattr(pipeline, 'close_spider'):
                    await pipeline.close_spider(self.crawler.spider)

                # 2. 触发 ResourceManager 清理注册的资源
                if hasattr(pipeline, '_resource_manager'):
                    await pipeline._resource_manager.cleanup_all()

                pipeline._cleaned_up = True
            except Exception as e:
                self.logger.error(f"Error closing pipeline {pipeline.__class__.__name__}: {e}")