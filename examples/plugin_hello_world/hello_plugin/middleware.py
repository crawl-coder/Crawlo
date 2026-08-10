"""自定义中间件：请求/响应日志 + 计数。"""

from crawlo.middleware import BaseMiddleware


class HelloMiddleware(BaseMiddleware):
    """最小中间件：给每个请求打点，响应时记录状态码。"""

    @classmethod
    def create_instance(cls, crawler):
        instance = cls()
        instance.crawler = crawler
        instance.request_count = 0
        return instance

    async def process_request(self, request, spider):
        self.request_count += 1
        return None  # 继续下载

    async def process_response(self, request, response, spider):
        return response
