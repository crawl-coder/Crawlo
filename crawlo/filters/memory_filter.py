#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
Memory Filter Implementation
================
Provides efficient request deduplication based on memory.

Supported Filters:
- MemoryFilter: Pure memory deduplication, best performance
- MemoryFileFilter: Memory + file persistence, supports restart recovery
"""
import os
import random
import asyncio
import warnings
from weakref import WeakSet
from typing import Set, TextIO, Optional, Dict, Any

from crawlo.filters import BaseFilter
from crawlo.logging import get_logger
from crawlo.utils.misc import safe_get_config
from crawlo.utils.async_lock import AsyncRLock


class MemoryFilter(BaseFilter):
    """
    Efficient memory-based request deduplication filter
    
    Features:
    - High Performance: O(1) lookup with Python set()
    - Memory Optimized: Supports weak reference temporary storage
    - Statistics: Provides detailed performance stats
    - Thread Safe: Supports multi-threaded concurrent access
    
    Use Cases:
    - Single-machine crawler
    - Small to medium datasets
    - High performance requirements
    """

    def __init__(self, crawler):
        """
        Initialize memory filter

        :param crawler: Crawler instance for configuration
        """
        self.fingerprints: Set[str] = set()  # 主指纹存储
        self._temp_weak_refs = WeakSet()     # 弱引用临时存储
        self._lock = AsyncRLock()            # 异步安全锁（替代 threading.RLock）

        # 安全初始化日志和统计
        debug = False
        if crawler and crawler.settings is not None:
            debug = safe_get_config(crawler.settings, 'FILTER_DEBUG', False, bool)
        else:
            debug = False
            
        logger = get_logger(self.__class__.__name__)
        super().__init__(logger, getattr(crawler, 'stats', None), debug)

        # Performance counters
        self._dupe_count = 0
        self._unique_count = 0
        
        # Safely get memory optimization configuration
        max_capacity = safe_get_config(crawler.settings, 'MEMORY_FILTER_MAX_CAPACITY', 1000000, int)
        cleanup_threshold = safe_get_config(crawler.settings, 'MEMORY_FILTER_CLEANUP_THRESHOLD', 0.8, float)
            
        self._max_capacity = max_capacity
        self._cleanup_threshold = cleanup_threshold

    def add_fingerprint(self, fp: str) -> None:
        """
        Add request fingerprint (sync method, for backward compatibility only)

        :param fp: Request fingerprint string
        :raises TypeError: If fingerprint is not string type
        :deprecated: Use add_fingerprint_async
        """
        warnings.warn(
            "add_fingerprint() is deprecated, use add_fingerprint_async() instead",
            DeprecationWarning,
            stacklevel=2
        )
        if not isinstance(fp, str):
            raise TypeError(f"Fingerprint must be string type, got {type(fp)}")

        # Simple sync implementation
        if fp not in self.fingerprints:
            # Check capacity limit
            if len(self.fingerprints) >= self._max_capacity:
                self._cleanup_old_fingerprints()
            
            self.fingerprints.add(fp)
            self._unique_count += 1
            
            if self.debug:
                self.logger.debug(f"Added fingerprint: {fp[:20]}...")

    async def add_fingerprint_async(self, fp: str) -> None:
        """
        Async safely add request fingerprint

        :param fp: Request fingerprint string
        :raises TypeError: If fingerprint is not string type
        """
        if not isinstance(fp, str):
            raise TypeError(f"Fingerprint must be string type, got {type(fp)}")

        async with self._lock:
            if fp not in self.fingerprints:
                # 检查容量限制
                if len(self.fingerprints) >= self._max_capacity:
                    self._cleanup_old_fingerprints()
                
                self.fingerprints.add(fp)
                self._unique_count += 1
                
                if self.debug:
                    self.logger.debug(f"Added fingerprint: {fp[:20]}...")
    
    def _cleanup_old_fingerprints(self) -> None:
        """Clean old fingerprints to free memory"""
        cleanup_count = int(len(self.fingerprints) * (1 - self._cleanup_threshold))
        if cleanup_count > 0:
            # Random cleanup some fingerprints (simple strategy)
            fingerprints_list = list(self.fingerprints)
            # random 已在顶部导入
            to_remove = random.sample(fingerprints_list, cleanup_count)
            self.fingerprints.difference_update(to_remove)
            self.logger.info(f"Cleaned {cleanup_count} old fingerprints")

    def requested(self, request) -> bool:
        """
        Check if request is duplicate (sync method, for backward compatibility only)

        :param request: Request object
        :return: Whether duplicate
        :deprecated: Use requested_async
        """
        warnings.warn(
            "MemoryFilter.requested() is deprecated, use requested_async() instead",
            DeprecationWarning,
            stacklevel=2
        )
        # 同步实现
        fp = self._get_fingerprint(request)
        if fp in self.fingerprints:
            self._dupe_count += 1
            return True

        self.add_fingerprint(fp)
        return False

    async def requested_async(self, request) -> bool:
        """
        Async safely check if request is duplicate

        :param request: Request object
        :return: Whether duplicate
        """
        async with self._lock:
            fp = self._get_fingerprint(request)
            if fp in self.fingerprints:
                self._dupe_count += 1
                return True

            # 检查容量限制
            if len(self.fingerprints) >= self._max_capacity:
                self._cleanup_old_fingerprints()
            
            self.fingerprints.add(fp)
            self._unique_count += 1
            return False

    def __contains__(self, item: str) -> bool:
        """
        支持 in 操作符检查（同步方法）

        :param item: 要检查的指纹
        :return: 是否已存在
        """
        # 简单的同步实现
        return item in self.fingerprints

    async def contains_async(self, item: str) -> bool:
        """
        异步安全地支持 in 操作符检查

        :param item: 要检查的指纹
        :return: 是否已存在
        """
        async with self._lock:
            return item in self.fingerprints

    @property
    def stats_summary(self) -> Dict[str, Any]:
        """Get filter statistics"""
        return {
            'filter_type': 'MemoryFilter',
            'capacity': len(self.fingerprints),
            'max_capacity': self._max_capacity,
            'duplicates': self._dupe_count,
            'uniques': self._unique_count,
            'total_processed': self._dupe_count + self._unique_count,
            'duplicate_rate': f"{self._dupe_count / max(1, self._dupe_count + self._unique_count) * 100:.2f}%",
            'memory_usage': self._estimate_memory(),
            'capacity_usage': f"{len(self.fingerprints) / self._max_capacity * 100:.2f}%"
        }

    def _estimate_memory(self) -> str:
        """Estimate memory usage (approximate)"""
        if not self.fingerprints:
            return "0 MB"
        
        avg_item_size = sum(len(x) for x in self.fingerprints) / len(self.fingerprints)
        total = len(self.fingerprints) * (avg_item_size + 50)  # 50字节额外开销
        
        if total < 1024:
            return f"{total:.1f} B"
        elif total < 1024 * 1024:
            return f"{total / 1024:.1f} KB" 
        else:
            return f"{total / (1024 * 1024):.2f} MB"

    def clear(self) -> None:
        """
        Clear all fingerprint data
        """
        self.fingerprints.clear()
        self._dupe_count = 0
        self._unique_count = 0
        if self.debug:
            self.logger.debug("已清空所有指纹")

    async def clear_async(self) -> None:
        """
        Async safely clear all fingerprint data
        """
        async with self._lock:
            self.fingerprints.clear()
            self._dupe_count = 0
            self._unique_count = 0
            if self.debug:
                self.logger.debug("Cleared all fingerprints")

    def close(self) -> None:
        """Close filter (clean resources)"""
        self.clear()

    # Compatible with old async interface
    async def closed(self):
        """Compatible async interface"""
        self.close()


class MemoryFileFilter(BaseFilter):
    """基于内存的请求指纹过滤器，支持原子化文件持久化"""

    def __init__(self, crawler):
        """
        初始化过滤器
        :param crawler: 爬虫框架Crawler对象，用于获取配置
        """
        self.fingerprints: Set[str] = set()  # 主存储集合
        self._lock = AsyncRLock()            # 异步安全锁（替代 threading.RLock）
        self._file: Optional[TextIO] = None  # 文件句柄

        debug = crawler.settings.get_bool("FILTER_DEBUG", False)
        logger = get_logger(self.__class__.__name__)
        super().__init__(logger, crawler.stats, debug)

        # 初始化文件存储
        request_dir = crawler.settings.get("REQUEST_DIR")
        if request_dir:
            self._init_file_store(request_dir)

    def _init_file_store(self, request_dir: str) -> None:
        """初始化文件存储（同步方法，仅用于初始化）"""
        try:
            os.makedirs(request_dir, exist_ok=True)
            file_path = os.path.join(request_dir, 'request_fingerprints.txt')

            # 原子化操作：读取现有指纹
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.fingerprints.update(
                        line.strip() for line in f
                        if line.strip()
                    )

            # 以追加模式打开文件
            self._file = open(file_path, 'a+', encoding='utf-8')
            self.logger.info(f"Initialized fingerprint file: {file_path}")

        except Exception as e:
            self.logger.error(f"Failed to init file store: {str(e)}")
            raise

    def add_fingerprint(self, fp: str) -> None:
        """
        添加指纹（同步方法，仅用于向后兼容）
        :param fp: 请求指纹字符串
        :deprecated: 请使用 add_fingerprint_async
        """
        warnings.warn(
            "MemoryFileFilter.add_fingerprint() is deprecated, use add_fingerprint_async() instead",
            DeprecationWarning,
            stacklevel=2
        )
        if fp not in self.fingerprints:
            self.fingerprints.add(fp)
            self._persist_fp(fp)

    async def add_fingerprint_async(self, fp: str) -> None:
        """
        异步安全地添加指纹
        :param fp: 请求指纹字符串
        """
        async with self._lock:
            if fp not in self.fingerprints:
                self.fingerprints.add(fp)
                self._persist_fp(fp)

    def _persist_fp(self, fp: str) -> None:
        """持久化指纹到文件"""
        if self._file:
            try:
                self._file.write(f"{fp}\n")
                self._file.flush()
                os.fsync(self._file.fileno())  # 确保写入磁盘
            except IOError as e:
                self.logger.error(f"Failed to persist fingerprint: {str(e)}")

    def __contains__(self, item: str) -> bool:
        """
        支持 in 操作符检查（同步方法）
        :param item: 要检查的指纹
        :return: 是否已存在
        """
        return item in self.fingerprints

    async def contains_async(self, item: str) -> bool:
        """
        异步安全地支持 in 操作符检查
        :param item: 要检查的指纹
        :return: 是否已存在
        """
        async with self._lock:
            return item in self.fingerprints

    def close(self) -> None:
        """关闭资源（同步方法）"""
        if self._file and not self._file.closed:
            try:
                self._file.flush()
                os.fsync(self._file.fileno())
            finally:
                self._file.close()
            self.logger.info(f"Closed fingerprint file: {self._file.name}")

    async def close_async(self) -> None:
        """异步安全地关闭资源"""
        async with self._lock:
            await self._close_file()

    async def _close_file(self) -> None:
        """关闭文件（需在锁保护下调用）"""
        if self._file and not self._file.closed:
            try:
                self._file.flush()
                os.fsync(self._file.fileno())
            finally:
                self._file.close()
            self.logger.info(f"Closed fingerprint file: {self._file.name}")

    def __del__(self):
        """析构函数双保险"""
        self.close()

    # 兼容异步接口
    async def closed(self):
        """标准的关闭入口"""
        self.close()
