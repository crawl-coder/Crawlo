"""自定义管道：统计并打印 item 字段。"""

from crawlo.pipelines import BasePipeline


class HelloPipeline(BasePipeline):
    """最小管道：打印 item 并计数。"""

    @classmethod
    def from_crawler(cls, crawler):
        instance = cls()
        instance.crawler = crawler
        instance.processed = 0
        return instance

    async def process_item(self, item, spider):
        self.processed += 1
        print(f"[hello_pipe] item #{self.processed}: {dict(item) if item else item}")
        return item
