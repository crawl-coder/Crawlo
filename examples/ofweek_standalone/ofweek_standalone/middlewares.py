# -*- coding: UTF-8 -*-
"""
ofweek_standalone.middlewares
============================
自定义中间件示例
"""

from crawlo.network import Request, Response
from crawlo.logging import get_logger


class OfweekStandaloneMiddleware:
    """
    ofweek_standalone 项目的中间件
    """
    
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)

    def process_request(self, request, spider):
        """
        在请求被下载器执行前调用
        """
        self.logger.info(f"处理请求: {request.url}")
        return None

    def process_response(self, request, response, spider):
        """
        在响应被 Spider 处理前调用
        """
        self.logger.info(f"收到响应: {request.url} - 状态码: {response.status_code}")
        return response

    def process_exception(self, request, exception, spider):
        """
        在下载或处理过程中发生异常时调用
        """
        self.logger.error(f"请求异常: {request.url} - {exception}")
        return None