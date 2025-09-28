#!/usr/bin/python
# -*- coding:UTF-8 -*-
from crawlo import Request, Response


class BaseMiddleware(object):
    def process_request(self, request, spider) -> None | Request | Response:
        # 请求预处理
        pass

    def process_response(self, request, response, spider) -> Request | Response:
        # 响应预处理
        pass

    def process_exception(self, request, exp, spider) -> None | Request | Response:
        # 异常预处理
        pass

    @classmethod
    def create_instance(cls, crawler):
        return cls()
