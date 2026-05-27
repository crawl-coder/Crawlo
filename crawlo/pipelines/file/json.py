# -*- coding: utf-8 -*-
"""
JSON Pipeline — 重构后继承 FileBasedPipeline
=============================================
- JsonLinesPipeline: 合并原 JsonPipeline，支持紧凑格式 + 可选元数据 + 计数
- JsonArrayPipeline: 所有 item 组成 JSON 数组输出，异步 I/O

设计文档：docs/internal/non-db-pipelines-design.md §3.1, §3.5
"""
import json
import asyncio
from pathlib import Path
from typing import Optional, List
from datetime import datetime

from crawlo.items import Item
from crawlo.exceptions import ItemDiscard
from crawlo.pipelines.base_pipeline import FileBasedPipeline

# 尝试导入 aiofiles
try:
    import aiofiles
    AIOFILES_AVAILABLE = True
except ImportError:
    AIOFILES_AVAILABLE = False


class JsonLinesPipeline(FileBasedPipeline):
    """
    JSON Lines 格式输出管道（每行一个 JSON 对象）

    合并原 JsonPipeline + JsonLinesPipeline：
    - 默认使用紧凑格式（separators=(',', ':')）
    - 可选元数据（JSON_ADD_METADATA=True）
    - 内置计数 + 定期日志
    """

    _PREFIX = 'JSON'

    def __init__(self, crawler):
        super().__init__(crawler)
        self.items_count = 0
        self.add_metadata = self.settings.get_bool('JSON_ADD_METADATA', False)

    # ── 生命周期 ──

    async def _initialize_resources(self):
        self.file_path = self._get_file_path('JSON_FILE', 'json_data', 'jsonl')
        await self._open_file('w', encoding='utf-8')
        self.logger.info(f"JSON Lines file created: {self.file_path}")

    async def _cleanup_resources(self):
        if self.file_handle:
            self.logger.info(
                f"JSON Lines file closed: {self.file_path} ({self.items_count} items)"
            )

    # ── 写入逻辑 ──

    async def process_item(self, item: Item, spider, **kwargs) -> Optional[Item]:
        try:
            async with self._file_lock:
                await self._ensure_open()
                item_dict = dict(item)

                # 可选元数据
                if self.add_metadata:
                    item_dict['_crawl_time'] = datetime.now().isoformat()
                    item_dict['_spider_name'] = spider.name

                # 紧凑 JSON 格式
                json_line = json.dumps(
                    item_dict, ensure_ascii=False, separators=(',', ':')
                )

                if AIOFILES_AVAILABLE:
                    await self.file_handle.write(json_line + '\n')
                else:
                    self.file_handle.write(json_line + '\n')
                    self.file_handle.flush()

                self.items_count += 1
                self.crawler.stats.inc_value('json_pipeline/items_written')

                if self.items_count % 100 == 0:
                    self.logger.info(f"Written {self.items_count} JSON objects")

            return item

        except Exception as e:
            self.crawler.stats.inc_value('json_pipeline/items_failed')
            self.logger.error(f"JSON write failed: {e}")
            raise ItemDiscard(f"JSON Pipeline failed: {e}")

    async def _ensure_open(self):
        if self.file_handle is None:
            await self._initialize_resources()


class JsonArrayPipeline(FileBasedPipeline):
    """JSON 数组格式输出管道（所有 item 组成一个 JSON 数组）"""

    _PREFIX = 'JSON_ARRAY'

    def __init__(self, crawler):
        super().__init__(crawler)
        self.items = []  # 内存中暂存
        self.max_items = self.settings.get_int('JSON_ARRAY_MAX_ITEMS', 100000)
        self.temp_files = []
        self.temp_counter = 0

    # ── 生命周期 ──

    async def _initialize_resources(self):
        # 文件路径延迟到最终写入时确定
        self.file_path = self._get_file_path(
            'JSON_ARRAY_FILE', 'json_array', 'json'
        )

    async def _cleanup_resources(self):
        """最终合并写入 JSON 数组"""
        # 1. 刷新剩余内存数据
        if self.items:
            await self._flush_to_temp_file()

        # 2. 合并临时文件 + 写入最终文件
        await self._write_final_array()

    # ── 写入逻辑 ──

    async def process_item(self, item: Item, spider, **kwargs) -> Optional[Item]:
        try:
            async with self._file_lock:
                item_dict = dict(item)
                self.items.append(item_dict)
                self.crawler.stats.inc_value('json_array_pipeline/items_collected')

                if len(self.items) >= self.max_items:
                    await self._flush_to_temp_file()

            return item

        except Exception as e:
            self.crawler.stats.inc_value('json_array_pipeline/items_failed')
            self.logger.error(f"JSON Array collect failed: {e}")
            raise ItemDiscard(f"JSON Array Pipeline failed: {e}")

    # ── 临时文件 + 合并（异步化）──

    async def _flush_to_temp_file(self):
        """内存数据刷新到临时文件（异步 I/O）"""
        if not self.items:
            return

        temp_path = self.file_path.with_name(
            f"{self.file_path.stem}_temp_{self.temp_counter}{self.file_path.suffix}"
        )
        self.temp_counter += 1
        data = self.items[:]
        self.items.clear()

        if AIOFILES_AVAILABLE:
            async with aiofiles.open(temp_path, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(data, ensure_ascii=False, indent=2))
        else:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._sync_write_json, temp_path, data)

        self.temp_files.append(temp_path)
        self.logger.info(f"Flushed {len(data)} items to temp file: {temp_path}")

    @staticmethod
    def _sync_write_json(path: Path, data: list):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    async def _write_final_array(self):
        """合并临时文件写入最终 JSON 数组（异步 I/O）"""
        all_items = []

        # 合并临时文件
        for temp_path in self.temp_files:
            if AIOFILES_AVAILABLE:
                async with aiofiles.open(temp_path, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    all_items.extend(json.loads(content))
            else:
                loop = asyncio.get_event_loop()
                items = await loop.run_in_executor(None, self._sync_read_json, temp_path)
                all_items.extend(items)
            temp_path.unlink()

        self.temp_files.clear()

        # 写入最终文件
        if all_items:
            if AIOFILES_AVAILABLE:
                async with aiofiles.open(self.file_path, 'w', encoding='utf-8') as f:
                    await f.write(json.dumps(all_items, ensure_ascii=False, indent=2))
            else:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None, self._sync_write_json, self.file_path, all_items
                )

            self.logger.info(
                f"JSON array saved: {len(all_items)} items -> {self.file_path}"
            )
            self.crawler.stats.set_value('json_array_pipeline/total_items', len(all_items))
        else:
            self.logger.warning("No items to save in JSON array")
        # 注意：文件句柄由 ResourceManager 自动关闭

    @staticmethod
    def _sync_read_json(path: Path) -> list:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
