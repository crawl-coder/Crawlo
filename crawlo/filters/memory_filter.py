#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
内存过滤器实现
================
提供基于内存的高效请求去重功能。

支持的过滤器:
- MemoryFilter: 纯内存去重，性能最佳
- MemoryFileFilter: 内存+文件持久化，支持重启恢复
"""
import os
import threading
from weakref import WeakSet
from typing import Set, TextIO, Optional

from crawlo.filters import BaseFilter
from crawlo.logging import get_logger


class MemoryFilter(BaseFilter):
    """
    基于内存的高效请求去重过滤器
    
    特点:
    - 高性能: 基于 Python set() 的 O(1) 查找效率
    - 内存优化: 支持弱引用临时存储
    - 统计信息: 提供详细的性能统计
    - 线程安全: 支持多线程并发访问
    
    适用场景:
    - 单机爬虫
    - 中小规模数据集
    - 对性能要求较高的场景
    """

    def __init__(self, crawler):
        """
        初始化内存过滤器

        :param crawler: 爬虫实例，用于获取配置
        """
        self.fingerprints: Set[str] = set()  # 主指纹存储
        self._temp_weak_refs = WeakSet()     # 弱引用临时存储
        self._lock = threading.RLock()       # 线程安全锁

        # 安全初始化日志和统计
        debug = False
        if crawler and crawler.settings is not None:
            from crawlo.utils.misc import safe_get_config
            debug = safe_get_config(crawler.settings, 'FILTER_DEBUG', False, bool)
        else:
            debug = False
            
        logger = get_logger(self.__class__.__name__)
        super().__init__(logger, getattr(crawler, 'stats', None), debug)

        # 性能计数器
        self._dupe_count = 0
        self._unique_count = 0
        
        # 安全获取内存优化配置
        from crawlo.utils.misc import safe_get_config
        max_capacity = safe_get_config(crawler.settings, 'MEMORY_FILTER_MAX_CAPACITY', 1000000, int)
        cleanup_threshold = safe_get_config(crawler.settings, 'MEMORY_FILTER_CLEANUP_THRESHOLD', 0.8, float)
            
        self._max_capacity = max_capacity
        self._cleanup_threshold = cleanup_threshold

    def add_fingerprint(self, fp: str) -> None:
        """
        线程安全地添加请求指纹

        :param fp: 请求指纹字符串
        :raises TypeError: 如果指纹不是字符串类型
        """
        if not isinstance(fp, str):
            raise TypeError(f"指纹必须是字符串类型，得到 {type(fp)}")

        with self._lock:
            if fp not in self.fingerprints:
                # 检查容量限制
                if len(self.fingerprints) >= self._max_capacity:
                    self._cleanup_old_fingerprints()
                
                self.fingerprints.add(fp)
                self._unique_count += 1
                
                if self.debug:
                    self.logger.debug(f"添加指纹: {fp[:20]}...")
    
    def _cleanup_old_fingerprints(self) -> None:
        """清理老旧指纹释放内存空间"""
        cleanup_count = int(len(self.fingerprints) * (1 - self._cleanup_threshold))
        if cleanup_count > 0:
            # 随机清理一部分指纹（简单策略）
            fingerprints_list = list(self.fingerprints)
            import random
            to_remove = random.sample(fingerprints_list, cleanup_count)
            self.fingerprints.difference_update(to_remove)
            self.logger.info(f"清理了 {cleanup_count} 个老旧指纹")

    def requested(self, request) -> bool:
        """
        线程安全地检查请求是否重复（主要接口）

        :param request: 请求对象
        :return: 是否重复
        """
        with self._lock:
            # 使用基类的指纹生成方法
            fp = self._get_fingerprint(request)
            if fp in self.fingerprints:
                self._dupe_count += 1
                return True

            self.add_fingerprint(fp)
            return False

    def __contains__(self, item: str) -> bool:
        """
        线程安全地支持 in 操作符检查

        :param item: 要检查的指纹
        :return: 是否已存在
        """
        with self._lock:
            return item in self.fingerprints

    @property
    def stats_summary(self) -> dict:
        """获取过滤器统计信息"""
        with self._lock:
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
        """估算内存使用量（近似值）"""
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
        """线程安全地清空所有指纹数据"""
        with self._lock:
            self.fingerprints.clear()
            self._dupe_count = 0
            self._unique_count = 0
            if self.debug:
                self.logger.debug("已清空所有指纹")

    def close(self) -> None:
        """关闭过滤器（清理资源）"""
        self.clear()

    # 兼容旧版异步接口
    async def closed(self):
        """兼容异步接口"""
        self.close()


class MemoryFileFilter(BaseFilter):
    """基于内存的请求指纹过滤器，支持原子化文件持久化"""

    def __init__(self, crawler):
        """
        初始化过滤器
        :param crawler: 爬虫框架Crawler对象，用于获取配置
        """
        self.fingerprints: Set[str] = set()  # 主存储集合
        self._lock = threading.RLock()  # 线程安全锁
        self._file: Optional[TextIO] = None  # 文件句柄

        debug = crawler.settings.get_bool("FILTER_DEBUG", False)
        logger = get_logger(self.__class__.__name__)
        super().__init__(logger, crawler.stats, debug)

        # 初始化文件存储
        request_dir = crawler.settings.get("REQUEST_DIR")
        if request_dir:
            self._init_file_store(request_dir)

    def _init_file_store(self, request_dir: str) -> None:
        """原子化初始化文件存储"""
        with self._lock:
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
        线程安全的指纹添加操作
        :param fp: 请求指纹字符串
        """
        with self._lock:
            if fp not in self.fingerprints:
                self.fingerprints.add(fp)
                self._persist_fp(fp)

    def _persist_fp(self, fp: str) -> None:
        """持久化指纹到文件（需在锁保护下调用）"""
        if self._file:
            try:
                self._file.write(f"{fp}\n")
                self._file.flush()
                os.fsync(self._file.fileno())  # 确保写入磁盘
            except IOError as e:
                self.logger.error(f"Failed to persist fingerprint: {str(e)}")

    def __contains__(self, item: str) -> bool:
        """
        线程安全的指纹检查
        :param item: 要检查的指纹
        :return: 是否已存在
        """
        with self._lock:
            return item in self.fingerprints

    def close(self) -> None:
        """安全关闭资源（同步方法）"""
        with self._lock:
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
