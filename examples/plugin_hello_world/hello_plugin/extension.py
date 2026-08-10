"""自定义扩展：spider 生命周期钩子。"""


class HelloExtension:
    """最小扩展：订阅 spider 打开/关闭事件。"""

    @classmethod
    def create_instance(cls, crawler):
        instance = cls()
        instance.crawler = crawler
        return instance

    async def spider_opened(self, spider):
        print(f"[hello_ext] spider opened: {getattr(spider, 'name', spider)}")

    async def spider_closed(self, spider):
        print(f"[hello_ext] spider closed: {getattr(spider, 'name', spider)}")
