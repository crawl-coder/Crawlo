#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
Crawlo过滤器模块
================
提供多种请求去重过滤器实现。

过滤器类型:
- MemoryFilter: 基于内存的高效去重，适合单机模式
- AioRedisFilter: 基于Redis的分布式去重，适合分布式模式
- MemoryFileFilter: 内存+文件持久化，适合需要重启恢复的场景

核心接口:
- BaseFilter: 所有过滤器的基类
- requested(): 检查请求是否重复的主要方法
"""
from abc import ABC, abstractmethod
from typing import Optional

from crawlo.utils.fingerprint import FingerprintGenerator


class BaseFilter(ABC):
    """
    请求去重过滤器基类
    
    提供统一的去重接口和统计功能。
    所有过滤器实现都应该继承此类。
    """

    def __init__(self, logger, stats, debug: bool = False):
        """
        初始化过滤器
        
        :param logger: 日志器实例
        :param stats: 统计信息存储
        :param debug: 是否启用调试日志
        """
        self.logger = logger
        self.stats = stats
        self.debug = debug
        self._request_count = 0
        self._duplicate_count = 0

    @classmethod
    def create_instance(cls, *args, **kwargs) -> 'BaseFilter':
        return cls(*args, **kwargs)

    def _get_fingerprint(self, request) -> str:
        """
        获取请求指纹（内部辅助方法）
        
        使用统一的 FingerprintGenerator 生成请求指纹。
        子类可以直接调用此方法，避免重复实现。
        
        :param request: 请求对象
        :return: 请求指纹字符串
        """
        return FingerprintGenerator.request_fingerprint(
            request.method,
            request.url,
            request.body or b'',
            dict(request.headers) if hasattr(request, 'headers') else {}
        )

    def requested(self, request) -> bool:
        """
        检查请求是否重复（主要接口）
        
        :param request: 请求对象
        :return: True 表示重复，False 表示新请求
        """
        self._request_count += 1
        fp = self._get_fingerprint(request)
        
        if fp in self:
            self._duplicate_count += 1
            self.log_stats(request)
            return True
            
        self.add_fingerprint(fp)
        return False

    @abstractmethod
    def add_fingerprint(self, fp: str) -> None:
        """
        添加请求指纹（子类必须实现）
        
        :param fp: 请求指纹字符串
        """
        pass
    
    @abstractmethod
    def __contains__(self, item: str) -> bool:
        """
        检查指纹是否存在（支持 in 操作符）
        
        :param item: 要检查的指纹
        :return: 是否已存在
        """
        pass

    def log_stats(self, request) -> None:
        """
        记录统计信息
        
        :param request: 重复的请求对象
        """
        if self.debug:
            self.logger.debug(f'过滤重复请求: {request}')
        self.stats.inc_value(f'{self}/filtered_count')
    
    def get_stats(self) -> dict:
        """
        获取过滤器统计信息
        
        :return: 统计信息字典
        """
        return {
            'total_requests': self._request_count,
            'duplicate_requests': self._duplicate_count,
            'unique_requests': self._request_count - self._duplicate_count,
            'duplicate_rate': f"{self._duplicate_count / max(1, self._request_count) * 100:.2f}%"
        }
    
    def reset_stats(self) -> None:
        """重置统计信息"""
        self._request_count = 0
        self._duplicate_count = 0
    
    def close(self) -> None:
        """关闭过滤器并清理资源"""
        pass

    def __str__(self) -> str:
        return f'{self.__class__.__name__}'


# 导出所有可用的过滤器
__all__ = ['BaseFilter']

# 动态导入具体实现
try:
    from .memory_filter import MemoryFilter, MemoryFileFilter
    __all__.extend(['MemoryFilter', 'MemoryFileFilter'])
except ImportError:
    MemoryFilter = None
    MemoryFileFilter = None

try:
    from .aioredis_filter import AioRedisFilter
    __all__.append('AioRedisFilter')
except ImportError:
    AioRedisFilter = None

# 提供便捷的过滤器映射
FILTER_MAP = {
    'memory': MemoryFilter,
    'memory_file': MemoryFileFilter,
    'redis': AioRedisFilter,
    'aioredis': AioRedisFilter,  # 别名
}

# 过滤掉不可用的过滤器
FILTER_MAP = {k: v for k, v in FILTER_MAP.items() if v is not None}

def get_filter_class(name: str):
    """根据名称获取过滤器类"""
    if name in FILTER_MAP:
        return FILTER_MAP[name]
    raise ValueError(f"未知的过滤器类型: {name}。可用类型: {list(FILTER_MAP.keys())}")