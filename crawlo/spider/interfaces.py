#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
爬虫层接口定义
==============
ISpiderLoader（Spider 加载器接口）。
"""
from abc import abstractmethod
from typing import (
    Type, List, Protocol, runtime_checkable, TYPE_CHECKING
)

if TYPE_CHECKING:
    from crawlo.spider import Spider
    from crawlo.http.request import Request


# ==================== 爬虫加载器接口 ====================

@runtime_checkable
class ISpiderLoader(Protocol):
    """
    Spider 加载器接口

    负责发现、加载和管理爬虫类。

    实现示例：
        class FileSystemSpiderLoader(ISpiderLoader):
            def __init__(self, spider_dir: str):
                self.spider_dir = spider_dir
                self._spiders = {}
                self._load_spiders()
    """

    @abstractmethod
    def load(self, spider_name: str) -> Type['Spider']:
        """
        根据名称加载爬虫类

        Args:
            spider_name: 爬虫名称

        Returns:
            Type[Spider]: 爬虫类

        Raises:
            KeyError: 爬虫不存在
        """
        ...

    @abstractmethod
    def list(self) -> List[str]:
        """
        列出所有可用的爬虫名称

        Returns:
            List[str]: 爬虫名称列表
        """
        ...

    @abstractmethod
    def find_by_request(self, request: 'Request') -> List[str]:
        """
        查找能处理指定请求的爬虫名称

        Args:
            request: 请求对象

        Returns:
            List[str]: 能处理该请求的爬虫名称列表
        """
        ...


__all__ = [
    'ISpiderLoader',
]
