#!/usr/bin/python
# -*- coding:UTF-8 -*-
from pprint import pformat
from types import MethodType
from asyncio import create_task
from collections import defaultdict
from typing import List, Dict, Callable, Optional

from crawlo import Request, Response
from crawlo.utils.log import get_logger
from crawlo.project import load_class
from crawlo.middleware import BaseMiddleware
from crawlo.project import common_call
from crawlo.event import ignore_request, response_received
from crawlo.exceptions import MiddlewareInitError, InvalidOutputError, RequestMethodError, IgnoreRequestError, \
    NotConfiguredError


class MiddlewareManager:

    def __init__(self, crawler):
        self.crawler = crawler
        self.logger = get_logger(self.__class__.__name__, crawler.settings.get('LOG_LEVEL'))
        self.middlewares: List = []
        self.methods: Dict[str, List[MethodType]] = defaultdict(list)
        middlewares = self.crawler.settings.get_list('MIDDLEWARES')
        self._add_middleware(middlewares)
        self._add_method()

        self.download_method: Callable = crawler.engine.downloader.download
        self._stats = crawler.stats

    async def _process_request(self, request: Request):
        for method in self.methods['process_request']:
            result = await common_call(method, request, self.crawler.spider)
            if result is None:
                continue
            if isinstance(result, (Request, Response)):
                return result
            raise InvalidOutputError(
                f"{method.__self__.__class__.__name__}. must return None or Request or Response, got {type(result).__name__}"
            )
        return await self.download_method(request)

    async def _process_response(self, request: Request, response: Response):
        for method in reversed(self.methods['process_response']):
            try:
                response = await common_call(method, request, response, self.crawler.spider)
            except IgnoreRequestError as exp:
                create_task(self.crawler.subscriber.notify(ignore_request, exp, request, self.crawler.spider))
            if isinstance(response, Request):
                return response
            if isinstance(response, Response):
                continue
            raise InvalidOutputError(
                f"{method.__self__.__class__.__name__}. must return Request or Response, got {type(response).__name__}"
            )
        return response

    async def _process_exception(self, request: Request, exp: Exception):
        for method in self.methods['process_exception']:
            response = await common_call(method, request, exp, self.crawler.spider)
            if response is None:
                continue
            if isinstance(response, (Request, Response)):
                return response
            if response:
                break
            raise InvalidOutputError(
                f"{method.__self__.__class__.__name__}. must return None or Request or Response, got {type(response).__name__}"
            )
        else:
            raise exp

    async def download(self, request) -> Optional[Response]:
        """ called in the download method. """
        try:
            response = await self._process_request(request)
        except KeyError:
            raise RequestMethodError(f"{request.method.lower()} is not supported")
        except IgnoreRequestError as exp:
            create_task(self.crawler.subscriber.notify(ignore_request, exp, request, self.crawler.spider))
            response = await self._process_exception(request, exp)
        except Exception as exp:
            self._stats.inc_value(f'download_error/{exp.__class__.__name__}')
            response = await self._process_exception(request, exp)
        else:
            create_task(self.crawler.subscriber.notify(response_received, response, self.crawler.spider))
            # self.crawler.stats.inc_value('response_received_count')
        if isinstance(response, Response):
            response = await self._process_response(request, response)
        if isinstance(response, Request):
            await self.crawler.engine.enqueue_request(request)
            return None
        return response

    @classmethod
    def create_instance(cls, *args, **kwargs):
        return cls(*args, **kwargs)

    def _add_middleware(self, middlewares):
        enabled_middlewares = [m for m in middlewares if self._validate_middleware(m)]
        if enabled_middlewares:
            self.logger.info(f'enabled middleware：\n {pformat(enabled_middlewares)}')

    def _validate_middleware(self, middleware):
        middleware_cls = load_class(middleware)
        if not hasattr(middleware_cls, 'create_instance'):
            raise MiddlewareInitError(
                f"Middleware init failed, must inherit from `BaseMiddleware` or have a `create_instance` method"
            )
        try:
            instance = middleware_cls.create_instance(self.crawler)
            self.middlewares.append(instance)
            return True
        except NotConfiguredError:
            return False

    def _add_method(self):
        for middleware in self.middlewares:
            if hasattr(middleware, 'process_request'):
                if self._validate_middleware_method(method_name='process_request', middleware=middleware):
                    self.methods['process_request'].append(middleware.process_request)
            if hasattr(middleware, 'process_response'):
                if self._validate_middleware_method(method_name='process_response', middleware=middleware):
                    self.methods['process_response'].append(middleware.process_response)
            if hasattr(middleware, 'process_exception'):
                if self._validate_middleware_method(method_name='process_exception', middleware=middleware):
                    self.methods['process_exception'].append(middleware.process_exception)

    @staticmethod
    def _validate_middleware_method(method_name, middleware) -> bool:
        method = getattr(type(middleware), method_name)
        base_method = getattr(BaseMiddleware, method_name)
        return False if method == base_method else True
