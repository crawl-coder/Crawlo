#!/usr/bin/python
# -*- coding:UTF-8 -*-
import os
import threading
from weakref import WeakSet
from typing import Set, TextIO, Optional

from crawlo import Request
from crawlo.filters import BaseFilter
from crawlo.utils.log import get_logger
from crawlo.utils.request import request_fingerprint


class MemoryFilter(BaseFilter):
    """基于内存的高效请求去重过滤器，适用于单机爬虫"""

    def __init__(self, crawler):
        """
        初始化内存过滤器

        :param crawler: 爬虫实例，用于获取配置
        """
        self.fingerprints: Set[str] = set()  # 主指纹存储
        self._temp_weak_refs = WeakSet()  # 弱引用临时存储（可选）

        debug = crawler.settings.get_bool('FILTER_DEBUG', False)
        logger = get_logger(
            self.__class__.__name__,  # 使用类名替代字符串
            crawler.settings.get('LOG_LEVEL', 'INFO')
        )
        super().__init__(logger, crawler.stats, debug)

        # 性能计数器
        self._dupe_count = 0
        self._unique_count = 0

    def add_fingerprint(self, fp: str) -> None:
        """
        添加请求指纹

        :param fp: 请求指纹字符串
        :raises TypeError: 如果指纹不是字符串类型
        """
        if not isinstance(fp, str):
            raise TypeError(f"指纹必须是字符串类型，得到 {type(fp)}")

        self.fingerprints.add(fp)
        self._unique_count += 1
        # self.logger.debug(f"添加指纹: {fp[:10]}...")  # 日志截断防止过长

    def requested(self, request: Request) -> bool:
        """
        检查请求是否重复（主要接口）

        :param request: 请求对象
        :return: 是否重复
        """
        fp = request_fingerprint(request)
        if fp in self:
            self._dupe_count += 1
            # self.logger.debug(f"发现重复请求: {fp[:10]}...")
            return True

        self.add_fingerprint(fp)
        return False

    def __contains__(self, item: str) -> bool:
        """
        支持 in 操作符检查

        :param item: 要检查的指纹
        :return: 是否已存在
        """
        return item in self.fingerprints

    @property
    def stats_summary(self) -> dict:
        """获取过滤器统计信息"""
        return {
            'capacity': len(self.fingerprints),
            'duplicates': self._dupe_count,
            'uniques': self._unique_count,
            'memory_usage': self._estimate_memory()
        }

    def _estimate_memory(self) -> str:
        """估算内存使用量（近似值）"""
        avg_item_size = sum(len(x) for x in self.fingerprints) / max(1, len(self.fingerprints))
        total = len(self.fingerprints) * (avg_item_size + 50)  # 50字节额外开销
        return f"{total / (1024 * 1024):.2f} MB"

    def clear(self) -> None:
        """清空所有指纹数据"""
        self.fingerprints.clear()
        self._dupe_count = 0
        self._unique_count = 0

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
        :param crawler: Scrapy Crawler对象，用于获取配置
        """
        self.fingerprints: Set[str] = set()  # 主存储集合
        self._lock = threading.RLock()  # 线程安全锁
        self._file: Optional[TextIO] = None  # 文件句柄

        debug = crawler.settings.get_bool("FILTER_DEBUG", False)
        logger = get_logger(
            self.__class__.__name__,  # 使用类名作为日志标识
            crawler.settings.get("LOG_LEVEL", "INFO")
        )
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
