#!/usr/bin/python
# -*- coding:UTF-8 -*-
from typing import List, Any
from pprint import pformat

from crawlo.utils.log import get_logger
from crawlo.project import load_class
from crawlo.exceptions import ExtensionInitError


class ExtensionManager(object):

    def __init__(self, crawler: Any):
        self.crawler = crawler
        self.extensions: List = []
        extensions = self.crawler.settings.get_list('EXTENSIONS')
        self.logger = get_logger(self.__class__.__name__, crawler.settings.get('LOG_LEVEL'))
        self._add_extensions(extensions)

    @classmethod
    def create_instance(cls, *args: Any, **kwargs: Any) -> 'ExtensionManager':
        return cls(*args, **kwargs)

    def _add_extensions(self, extensions: List[str]) -> None:
        for extension_path in extensions:
            try:
                extension_cls = load_class(extension_path)
                if not hasattr(extension_cls, 'create_instance'):
                    raise ExtensionInitError(
                        f"Extension '{extension_path}' init failed: Must have method 'create_instance()'"
                    )
                self.extensions.append(extension_cls.create_instance(self.crawler))
            except Exception as e:
                self.logger.error(f"Failed to load extension '{extension_path}': {e}")
                raise ExtensionInitError(f"Failed to load extension '{extension_path}': {e}")
        
        if extensions:
            self.logger.info(f"Enabled extensions: \n{pformat(extensions)}")