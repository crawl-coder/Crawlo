# -*- coding: UTF-8 -*-
"""
管道定义
"""
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
