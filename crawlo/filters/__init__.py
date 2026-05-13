#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
Crawlo Filter Module
================
Provides multiple request deduplication filter implementations.

Filter Types:
- MemoryFilter: Memory-based deduplication, suitable for standalone mode
- AioRedisFilter: Redis-based distributed deduplication, suitable for distributed mode
- MemoryFileFilter: Memory + file persistence, suitable for restart recovery scenarios

Core Interface:
- BaseFilter: Base class for all filters
- requested(): Main method for checking request duplication
"""
from abc import ABC, abstractmethod
from typing import Optional

from crawlo.utils.request.fingerprint import FingerprintGenerator


class BaseFilter(ABC):
    """
    Request Deduplication Filter Base Class
    
    Provides unified deduplication interface and statistics functionality.
    All filter implementations should inherit from this class.
    """

    def __init__(self, logger, stats, debug: bool = False):
        """
        Initialize filter
        
        :param logger: Logger instance
        :param stats: Statistics storage
        :param debug: Enable debug logging
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
        Get request fingerprint (internal helper method)
        
        Uses unified FingerprintGenerator to generate request fingerprints.
        Subclasses can call this method directly to avoid duplicate implementation.
        
        :param request: Request object
        :return: Request fingerprint string
        """
        return FingerprintGenerator.request_fingerprint(
            request.method,
            request.url,
            request.body or b'',
            dict(request.headers) if hasattr(request, 'headers') else {},
            request.meta if hasattr(request, 'meta') else {}
        )

    def requested(self, request) -> bool:
        """
        Check if request is duplicate (main interface)
        
        :param request: Request object
        :return: True if duplicate, False if new request
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
        Add request fingerprint (must be implemented by subclass)
        
        :param fp: Request fingerprint string
        """
        pass
    
    @abstractmethod
    def __contains__(self, item: str) -> bool:
        """
        Check if fingerprint exists (supports in operator)
        
        :param item: Fingerprint to check
        :return: Whether exists
        """
        pass

    def log_stats(self, request) -> None:
        """
        Log statistics
        
        :param request: Duplicate request object
        """
        if self.debug:
            self.logger.debug(f'Filtered duplicate request: {request}')
        self.stats.inc_value(f'{self}/filtered_count')
    
    def get_stats(self) -> dict:
        """
        Get filter statistics
        
        :return: Statistics dictionary
        """
        return {
            'total_requests': self._request_count,
            'duplicate_requests': self._duplicate_count,
            'unique_requests': self._request_count - self._duplicate_count,
            'duplicate_rate': f"{self._duplicate_count / max(1, self._request_count) * 100:.2f}%"
        }
    
    def reset_stats(self) -> None:
        """Reset statistics"""
        self._request_count = 0
        self._duplicate_count = 0
    
    def close(self) -> None:
        """Close filter and clean resources"""
        pass

    def __str__(self) -> str:
        return f'{self.__class__.__name__}'


# Export all available filters
__all__ = ['BaseFilter']

# Dynamically import concrete implementations
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

# Provide convenient filter mapping
FILTER_MAP = {
    'memory': MemoryFilter,
    'memory_file': MemoryFileFilter,
    'redis': AioRedisFilter,
    'aioredis': AioRedisFilter,  # 别名
}

# Filter out unavailable filters
FILTER_MAP = {k: v for k, v in FILTER_MAP.items() if v is not None}

def get_filter_class(name: str):
    """Get filter class by name"""
    if name in FILTER_MAP:
        return FILTER_MAP[name]
    raise ValueError(f"Unknown filter type: {name}. Available types: {list(FILTER_MAP.keys())}")