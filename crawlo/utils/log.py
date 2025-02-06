#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
# @Time    :    2024-04-11 09:03
# @Author  :   oscar
# @Desc    :   None
"""
from logging import Formatter, StreamHandler, Logger, INFO

LOG_FORMAT = '%(asctime)s - [%(name)s] - %(levelname)s： %(message)s'


class LoggerManager(object):
    logger_cache = {}

    def __init__(self):
        pass

    @classmethod
    def get_logger(cls, name: str = 'default', level=None, log_format: str = LOG_FORMAT):
        #
        key = (name, level)

        def gen_logger():
            log_formatter = Formatter(log_format)
            handler = StreamHandler()
            handler.setFormatter(log_formatter)
            handler.setLevel(level or INFO)

            _logger = Logger(name=name)
            _logger.addHandler(handler)
            _logger.setLevel(level or INFO)
            cls.logger_cache[key] = _logger
            return _logger

        return cls.logger_cache.get(key, None) or gen_logger()


get_logger = LoggerManager.get_logger

