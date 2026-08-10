# -*- coding: UTF-8 -*-
"""Catalog 管道：JSONL 文件存储（开箱即用）。"""

import json
from pathlib import Path

from crawlo.pipelines import BasePipeline
from crawlo.utils.misc import safe_get_config


class JsonlCatalogPipeline(BasePipeline):
    """把 item 逐行写入 JSONL 文件（UTF-8，追加模式）。"""

    @classmethod
    def from_crawler(cls, crawler):
        instance = cls()
        instance.crawler = crawler
        instance.output_path = Path(
            safe_get_config(crawler.settings, "CATALOG_OUTPUT_PATH", "catalog.jsonl", str)
        )
        instance.written = 0
        return instance

    async def open_spider(self, spider):
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self._file = self.output_path.open("a", encoding="utf-8")

    async def process_item(self, item, spider):
        self._file.write(json.dumps(dict(item), ensure_ascii=False) + "\n")
        self._file.flush()
        self.written += 1
        return item

    async def close_spider(self, spider):
        if getattr(self, "_file", None) is not None:
            self._file.close()
        self.crawler.stats.inc_value("catalog/jsonl_written", self.written)
