# -*- coding: utf-8 -*-
"""
CSV Pipeline — 重构后继承 FileBasedPipeline
=============================================
- CsvPipeline: 合并 CsvBatchPipeline 的批量缓冲功能
- CsvDictPipeline: 使用 csv.DictWriter，支持字段映射

设计文档：docs/internal/non-db-pipelines-design.md §3.1
"""
import csv
import asyncio
from typing import Optional, List

from crawlo.items import Item
from crawlo.exceptions import ItemDiscard
from crawlo.pipelines.base_pipeline import FileBasedPipeline

# csv.writer 依赖同步文件对象，始终使用同步 I/O
# aiofiles 的 write() 是协程，与 csv.writer 不兼容
AIOfiLES_AVAILABLE = False  # 强制禁用


class CsvPipeline(FileBasedPipeline):
    """CSV 文件输出管道（继承 FileBasedPipeline，支持批量缓冲）"""

    _PREFIX = 'CSV'

    def __init__(self, crawler):
        super().__init__(crawler)
        self.csv_writer = None
        self.headers_written = False

        # CSV 配置
        self.delimiter = self.settings.get('CSV_DELIMITER', ',')
        self.quotechar = self.settings.get('CSV_QUOTECHAR', '"')
        self.include_headers = self.settings.get_bool('CSV_INCLUDE_HEADERS', True)

        # 批量缓冲（合并 CsvBatchPipeline）
        self.buffer_enabled = self.settings.get_bool('CSV_USE_BUFFER', False)
        self.batch_buffer = [] if self.buffer_enabled else []

    # ── 生命周期 ──

    async def _initialize_resources(self):
        """初始化文件资源"""
        self.file_path = self._get_file_path('CSV_FILE', 'csv_data', 'csv')
        await self._open_file('w', newline='', encoding='utf-8')
        # csv.writer 使用同步文件句柄
        self.csv_writer = csv.writer(
            self.file_handle,
            delimiter=self.delimiter,
            quotechar=self.quotechar,
            quoting=csv.QUOTE_MINIMAL,
        )
        self.logger.info(f"CSV file created: {self.file_path}")

    async def _cleanup_resources(self):
        """刷新缓冲区并清理"""
        if self.buffer_enabled and self.batch_buffer:
            await self._flush_buffer()
        if self.csv_writer:
            self.csv_writer = None
        # FileBasedPipeline 的 ResourceManager 自动关闭文件句柄

    # ── 写入逻辑 ──

    async def process_item(self, item: Item, spider, **kwargs) -> Optional[Item]:
        try:
            item_dict = dict(item)

            async with self._file_lock:
                await self._ensure_open()
                # 写入表头
                if not self.headers_written and self.include_headers:
                    self.csv_writer.writerow(list(item_dict.keys()))
                    self.file_handle.flush()
                    self.headers_written = True
                    self.logger.debug(f"CSV headers written")

                # 批量模式
                if self.buffer_enabled:
                    values = [str(v) if v is not None else '' for v in item_dict.values()]
                    self.batch_buffer.append(values)
                    if len(self.batch_buffer) >= self.settings.get_int('CSV_BATCH_SIZE', 100):
                        await self._flush_buffer()
                else:
                    values = [str(v) if v is not None else '' for v in item_dict.values()]
                    self.csv_writer.writerow(values)
                    self.file_handle.flush()

            self.crawler.stats.inc_value('csv_pipeline/items_written')
            return item

        except Exception as e:
            self.crawler.stats.inc_value('csv_pipeline/items_failed')
            self.logger.error(f"CSV write failed: {e}")
            raise ItemDiscard(f"CSV Pipeline failed: {e}")

    async def _ensure_open(self):
        """确保文件句柄可用（FileBasedPipeline 可能在初始化后才打开）"""
        if self.file_handle is None:
            await self._initialize_resources()

    async def _flush_buffer(self):
        """刷新批量缓冲区"""
        if not self.batch_buffer:
            return
        batch = self.batch_buffer[:]
        self.batch_buffer.clear()
        self.csv_writer.writerows(batch)
        self.file_handle.flush()
        self.crawler.stats.inc_value('csv_pipeline/batch_flushed')
        self.crawler.stats.inc_value('csv_pipeline/items_written', count=len(batch))
        self.logger.debug(f"CSV batch flushed: {len(batch)} rows")


class CsvDictPipeline(FileBasedPipeline):
    """CSV 字典写入管道（使用 DictWriter，支持字段映射）"""

    _PREFIX = 'CSV_DICT'

    def __init__(self, crawler):
        super().__init__(crawler)
        self.csv_writer = None
        self.fieldnames = None

        # CSV 配置
        self.delimiter = self.settings.get('CSV_DELIMITER', ',')
        self.quotechar = self.settings.get('CSV_QUOTECHAR', '"')
        self.include_headers = self.settings.get_bool('CSV_INCLUDE_HEADERS', True)
        self.extrasaction = self.settings.get('CSV_EXTRASACTION', 'ignore')

    # ── 生命周期 ──

    async def _initialize_resources(self):
        self.file_path = self._get_file_path('CSV_DICT_FILE', 'csv_dict', 'csv')
        await self._open_file('w', newline='', encoding='utf-8')

    async def _cleanup_resources(self):
        if self.csv_writer:
            self.csv_writer = None

    # ── 字段名获取 ──

    def _get_fieldnames(self, item_dict: dict) -> List[str]:
        configured_fields = self.settings.get('CSV_FIELDNAMES')
        if configured_fields:
            if isinstance(configured_fields, list):
                return configured_fields
            elif isinstance(configured_fields, str):
                return [f.strip() for f in configured_fields.split(',') if f.strip()]

        spider_fields = getattr(self.crawler.spider, 'csv_fieldnames', None)
        if spider_fields:
            if isinstance(spider_fields, list):
                return spider_fields
            elif isinstance(spider_fields, str):
                return [f.strip() for f in spider_fields.split(',') if f.strip()]

        return list(item_dict.keys())

    async def _ensure_open_with_fields(self, item_dict: dict):
        """首次打开时根据字段名初始化 DictWriter"""
        if self.file_handle is None:
            await self._initialize_resources()

        if self.csv_writer is None:
            self.fieldnames = self._get_fieldnames(item_dict)
            self.csv_writer = csv.DictWriter(
                self.file_handle,
                fieldnames=self.fieldnames,
                delimiter=self.delimiter,
                quotechar=self.quotechar,
                quoting=csv.QUOTE_MINIMAL,
                extrasaction=self.extrasaction,
            )
            if self.include_headers:
                self.csv_writer.writeheader()
            self.logger.info(
                f"CSV Dict file created: {self.file_path}, fields: {self.fieldnames}"
            )

    # ── 写入逻辑 ──

    async def process_item(self, item: Item, spider, **kwargs) -> Optional[Item]:
        try:
            item_dict = dict(item)

            async with self._file_lock:
                await self._ensure_open_with_fields(item_dict)
                self.csv_writer.writerow(item_dict)
                self.file_handle.flush()

            self.crawler.stats.inc_value('csv_dict_pipeline/items_written')
            return item

        except Exception as e:
            self.crawler.stats.inc_value('csv_dict_pipeline/items_failed')
            self.logger.error(f"CSV Dict write failed: {e}")
            raise ItemDiscard(f"CSV Dict Pipeline failed: {e}")

    async def _close_file(self, file_handle):
        """关闭文件句柄（同步模式）"""
        if file_handle and not file_handle.closed:
            file_handle.close()
            self.logger.info(f"CSV Dict file closed: {self.file_path}")
