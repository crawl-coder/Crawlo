#!/usr/bin/python
# -*- coding:UTF-8 -*-
from typing import List
from pprint import pformat

from crawlo.utils.log import get_logger
from crawlo.project import load_class
from crawlo.exceptions import ExtensionInitError


class ExtensionManager(object):

    def __init__(self, crawler):
        self.crawler = crawler
        self.extensions: List = []
        extensions = self.crawler.settings.get_list('EXTENSIONS')
        self.logger = get_logger(self.__class__.__name__, crawler.settings.get('LOG_LEVEL'))
        self._add_extensions(extensions)

    @classmethod
    def create_instance(cls, *args, **kwargs):
        return cls(*args, **kwargs)

    def _add_extensions(self, extensions):
        for extension in extensions:
            extension_cls = load_class(extension)
            if not hasattr(extension_cls, 'create_instance'):
                raise ExtensionInitError(f"extension init failed, Must have method 'create_instance()")
            self.extensions.append(extension_cls.create_instance(self.crawler))
        if extensions:
            self.logger.info(f"enabled extensions: \n {pformat(extensions)}")
