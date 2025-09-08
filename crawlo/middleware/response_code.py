#!/usr/bin/python
# -*- coding:UTF-8 -*-
from crawlo.utils.log import get_logger


class ResponseCodeMiddleware(object):
    def __init__(self, stats, log_level):
        self.logger = get_logger(self.__class__.__name__, log_level)
        self.stats = stats

    @classmethod
    def create_instance(cls, crawler):
        o = cls(stats=crawler.stats, log_level=crawler.settings.get('LOG_LEVEL'))
        return o

    def process_response(self, request, response, spider):
        self.stats.inc_value(f'stats_code/count/{response.status_code}')
        self.logger.debug(f'Got response from <{response.status_code} {response.url}>')
        return response