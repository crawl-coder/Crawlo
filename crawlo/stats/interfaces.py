#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
统计层接口定义
==============
IStatsCollector（统计收集器接口）。
"""
from abc import abstractmethod
from typing import (
    Dict, Any, Protocol, runtime_checkable
)


# ==================== 统计收集器接口 ====================

@runtime_checkable
class IStatsCollector(Protocol):
    """
    统计收集器接口

    负责收集和存储爬虫运行期间的统计信息。
    支持多种后端实现：内存、Redis、Prometheus 等。

    实现示例：
        class RedisStatsCollector(IStatsCollector):
            def inc_value(self, key: str, count: int = 1) -> None:
                self.redis.hincrby(self.key, key, count)

            def get_value(self, key: str, default: Any = None) -> Any:
                value = self.redis.hget(self.key, key)
                return int(value) if value else default
    """

    @abstractmethod
    def inc_value(self, key: str, count: int = 1) -> None:
        """
        增加计数器值

        Args:
            key: 统计键名
            count: 增量，默认为 1
        """
        ...

    @abstractmethod
    def get_value(self, key: str, default: Any = None) -> Any:
        """
        获取统计值

        Args:
            key: 统计键名
            default: 默认值

        Returns:
            Any: 统计值
        """
        ...

    @abstractmethod
    def set_value(self, key: str, value: Any) -> None:
        """
        设置统计值

        Args:
            key: 统计键名
            value: 统计值
        """
        ...

    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """
        获取所有统计信息

        Returns:
            Dict[str, Any]: 统计信息字典
        """
        ...

    @abstractmethod
    def clear(self) -> None:
        """
        清空所有统计信息
        """
        ...


__all__ = [
    'IStatsCollector',
]
