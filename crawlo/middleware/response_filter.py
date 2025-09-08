#!/usr/bin/python
# -*- coding:UTF-8 -*-
from crawlo.utils.log import get_logger
from crawlo.exceptions import IgnoreRequestError


class ResponseFilterMiddleware:

    def __init__(self, allowed_codes, log_level):
        self.allowed_codes = allowed_codes
        self.logger = get_logger(self.__class__.__name__, log_level)

    @classmethod
    def create_instance(cls, crawler):
        o = cls(
            allowed_codes=crawler.settings.get_list('ALLOWED_CODES'),
            log_level=crawler.settings.get('LOG_LEVEL')
        )
        return o

    def process_response(self, request, response, spider):
        if 200 <= response.status_code < 300:
            return response
        if response.status_code in self.allowed_codes:
            return response
        raise IgnoreRequestError(f"response status_code/non-200")
