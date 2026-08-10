# -*- coding: UTF-8 -*-
"""极简管道：把 item 追加写入 JSONL（默认 output/items.jsonl）。"""

import json
from pathlib import Path

from crawlo.pipelines import BasePipeline


class JsonlPipeline(BasePipeline):
    @classmethod
    def from_crawler(cls, crawler):
        inst = cls()
        inst.path = Path("output/items.jsonl")
        return inst

    async def open_spider(self, spider):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._f = self.path.open("a", encoding="utf-8")

    async def process_item(self, item, spider):
        self._f.write(json.dumps(dict(item), ensure_ascii=False) + "\n")
        return item

    async def close_spider(self, spider):
        self._f.close()
