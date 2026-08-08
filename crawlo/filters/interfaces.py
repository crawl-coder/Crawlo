#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
过滤器层接口定义
================
IFilter（请求去重过滤器接口）。
"""
from abc import abstractmethod
from typing import (
    Protocol, runtime_checkable, TYPE_CHECKING
)

# 注意：所有使用 Request 作签名的位置都使用 ``'Request'`` 字符串注解，
# 避免在 TYPE_CHECKING 中 ``from crawlo.network.request import Request``
# 被 lint-imports 计入 crawlo.filters -> crawlo.network 违规。


# ==================== 过滤器接口 ====================

@runtime_checkable
class IFilter(Protocol):
    """
    请求去重过滤器接口

    负责识别和过滤重复请求。

    实现示例：
        class MemoryFilter(IFilter):
            def __init__(self):
                self._fingerprints = set()

            def requested(self, request: "Request") -> bool:
                fp = self._get_fingerprint(request)
                if fp in self._fingerprints:
                    return True
                self._fingerprints.add(fp)
                return False
    """

    @abstractmethod
    def requested(self, request: 'Request') -> bool:
        """
        检查请求是否重复

        Args:
            request: 请求对象

        Returns:
            bool: True 表示重复（已请求过），False 表示新请求
        """
        ...

    @abstractmethod
    def add_fingerprint(self, fp: str) -> None:
        """
        添加请求指纹

        Args:
            fp: 请求指纹字符串
        """
        ...

    @abstractmethod
    def __contains__(self, fp: str) -> bool:
        """
        检查指纹是否存在

        Args:
            fp: 请求指纹字符串

        Returns:
            bool: 是否已存在
        """
        ...

    def close(self) -> None:
        """
        关闭过滤器并清理资源（可选实现）
        """
        ...

    @classmethod
    def create_instance(cls, *args, **kwargs) -> 'IFilter':
        """
        创建过滤器实例的工厂方法
        """
        ...


__all__ = [
    'IFilter',
]
