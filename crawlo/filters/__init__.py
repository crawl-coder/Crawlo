#!/usr/bin/python
# -*- coding:UTF-8 -*-
from abc import ABC, abstractmethod

from crawlo import Request
from crawlo.utils.request import request_fingerprint


class BaseFilter(ABC):

    def __init__(self, logger, stats, debug: bool):
        self.logger = logger
        self.stats = stats
        self.debug = debug

    @classmethod
    def create_instance(cls, *args, **kwargs) -> 'BaseFilter':
        return cls(*args, **kwargs)

    def requested(self, request: Request):
        fp = request_fingerprint(request)
        if fp in self:
            return True
        self.add_fingerprint(fp)
        return False

    @abstractmethod
    def add_fingerprint(self, fp) -> None:
        pass

    def log_stats(self, request: Request) -> None:
        if self.debug:
            self.logger.debug(f'Filtered duplicate request: {request}')
        self.stats.inc_value(f'{self}/filtered_count')

    def __str__(self) -> str:
        return f'{self.__class__.__name__}'
