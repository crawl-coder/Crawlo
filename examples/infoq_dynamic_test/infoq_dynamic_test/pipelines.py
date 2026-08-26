# -*- coding: UTF-8 -*-
"""
管道定义
"""
import json
import os

from crawlo.pipelines import BasePipeline


class ConsolePipeline(BasePipeline):
    """控制台输出管道"""

    @classmethod
    def from_crawler(cls, crawler):
        """从Crawler创建Pipeline实例"""
        return cls()

    async def process_item(self, item, spider):
        """处理数据项"""
        print(f"\n{'='*50}")
        print(f"标题: {item.get('title', 'N/A')}")
        print(f"链接: {item.get('url', 'N/A')}")
        print(f"作者: {item.get('author', 'N/A')}")
        print(f"摘要: {item.get('summary', 'N/A')[:100]}..." if item.get('summary') else "摘要: N/A")
        print(f"{'='*50}\n")
        return item


class JsonlPipeline(BasePipeline):
    """JSONL 落盘管道（长跑测试用，避免控制台刷屏）"""

    @classmethod
    def from_crawler(cls, crawler):
        inst = cls()
        inst.path = os.environ.get('LONGRUN_OUT', 'logs/longrun_items.jsonl')
        return inst

    async def open_spider(self, spider):
        os.makedirs(os.path.dirname(self.path) or '.', exist_ok=True)
        self._f = open(self.path, 'a', encoding='utf-8')

    async def process_item(self, item, spider):
        self._f.write(json.dumps(dict(item), ensure_ascii=False) + '\n')
        self._f.flush()
        return item

    async def close_spider(self, spider):
        self._f.close()
