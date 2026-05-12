#!/usr/bin/python
# -*- coding:UTF-8 -*-
from pprint import pformat
from types import MethodType
from asyncio import create_task
import asyncio
from collections import defaultdict
from typing import List, Dict, Callable, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from crawlo import Request, Response
else:
    # Import actual classes for isinstance checks
    from crawlo.network.request import Request
    from crawlo.network.response import Response
from crawlo.logging import get_logger
from crawlo.utils.misc import load_object
from crawlo.middleware import BaseMiddleware
from crawlo.project import common_call
from crawlo.event import CrawlerEvent
from crawlo.utils.misc import safe_get_config
from crawlo.exceptions import MiddlewareInitError, InvalidOutputError, RequestMethodError, IgnoreRequestError, \
    NotConfiguredError


class MiddlewareManager:
    # Class-level flag to ensure middleware enabled log is printed only once
    _logged_enabled = False
    
    # 重试保护配置
    MAX_RETRY_DEPTH = 5  # 最大重试深度
    RETRY_BACKOFF_BASE = 1.0  # 基础退避时间（秒）
    RETRY_BACKOFF_MAX = 30.0  # 最大退避时间（秒）

    def __init__(self, crawler, download_func: Callable = None):
        self.crawler = crawler
        self.logger = get_logger(self.__class__.__name__)
        self.middlewares: List = []
        self.methods: Dict[str, List[MethodType]] = defaultdict(list)
        self._initialized = False  # 生命周期状态标记
        
        # Safely get MIDDLEWARES configuration
        middlewares = safe_get_config(self.crawler.settings, 'MIDDLEWARES', [], list)
            
        self._add_middleware(middlewares)
        self._add_method()

        # 使用延迟绑定避免循环依赖
        # 如果提供了 download_func，直接使用
        # 否则在首次调用时通过 crawler.engine.downloader 获取
        if download_func is not None:
            self._download_func = download_func
        else:
            self._download_func = None
        
        self._stats = crawler.stats
        self._background_tasks: set = set()  # Track fire-and-forget tasks
    
    def _create_background_task(self, coro):
        """创建带引用追踪的后台任务，防止 fire-and-forget 任务泄漏"""
        task = create_task(coro)
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)
        return task
    
    @property
    def download_method(self) -> Callable:
        """
        获取下载方法（延迟绑定）
        
        避免在 __init__ 时直接引用 downloader.download，
        从而解决循环依赖问题
        """
        if self._download_func is not None:
            return self._download_func
        
        # 首次访问时获取下载方法
        if hasattr(self.crawler, 'engine') and self.crawler.engine is not None:
            downloader = getattr(self.crawler.engine, 'downloader', None)
            if downloader is not None:
                self._download_func = downloader.download
                return self._download_func
        
        raise RuntimeError(
            "无法获取下载方法: crawler.engine.downloader 未初始化。\n"
            "请确保在调用中间件之前先初始化下载器。"
        )
    
    @download_method.setter
    def download_method(self, func: Callable):
        """设置下载方法"""
        self._download_func = func
    
    async def open(self) -> None:
        """
        中间件管理器初始化（生命周期方法）
        
        在爬虫启动时调用，初始化所有中间件。
        支持中间件的 open() 生命周期钩子。
        """
        if self._initialized:
            self.logger.debug("MiddlewareManager already initialized")
            return
        
        self.logger.debug(f"Initializing {len(self.middlewares)} middlewares...")
        
        for middleware in self.middlewares:
            try:
                # 调用中间件的 open 生命周期方法（如果存在）
                if hasattr(middleware, 'open'):
                    open_method = middleware.open
                    if asyncio.iscoroutinefunction(open_method):
                        await open_method()
                    else:
                        result = open_method()
                        if asyncio.iscoroutine(result):
                            await result
                    
                    self.logger.debug(f"Middleware {middleware.__class__.__name__} opened")
            except Exception as e:
                self.logger.error(
                    f"Failed to open middleware {middleware.__class__.__name__}: {e}"
                )
                raise
        
        self._initialized = True
        self.logger.info(f"MiddlewareManager initialized with {len(self.middlewares)} middlewares")
    
    async def close(self) -> None:
        """
        中间件管理器关闭（生命周期方法）
        
        在爬虫关闭时调用，清理所有中间件资源。
        支持中间件的 close() 生命周期钩子。
        """
        if not self._initialized:
            self.logger.debug("MiddlewareManager not initialized, skipping close")
            return
        
        self.logger.debug(f"Closing {len(self.middlewares)} middlewares...")
        
        # 反向关闭（与初始化顺序相反）
        for middleware in reversed(self.middlewares):
            try:
                # 调用中间件的 close 生命周期方法（如果存在）
                if hasattr(middleware, 'close'):
                    close_method = middleware.close
                    if asyncio.iscoroutinefunction(close_method):
                        await close_method()
                    else:
                        result = close_method()
                        if asyncio.iscoroutine(result):
                            await result
                    
                    self.logger.debug(f"Middleware {middleware.__class__.__name__} closed")
            except Exception as e:
                self.logger.warning(
                    f"Error closing middleware {middleware.__class__.__name__}: {e}"
                )
        
        self._initialized = False
        self.logger.info("MiddlewareManager closed")

    async def _process_request(self, request: 'Request'):
        for idx, method in enumerate(self.methods['process_request']):
            try:
                result = await common_call(method, request, self.crawler.spider)
                
                if result is None:
                    continue
                if isinstance(result, (Request, Response)):
                    return result
                raise InvalidOutputError(
                    f"{self._get_method_class_name(method)}. must return None or Request or Response, got {type(result).__name__}"
                )
            except asyncio.CancelledError:
                # Handle cancellation properly（只打印一次，避免重复）
                if not getattr(self, '_cancel_logged', False):
                    self.logger.info("Request processing cancelled")
                    self._cancel_logged = True
                raise
            except Exception as e:
                self.logger.error(f"Error processing request: {e}")
                raise
        
        # 使用属性获取下载方法，支持延迟绑定
        download_fn = self.download_method
        
        return await download_fn(request)

    async def _process_response(self, request: 'Request', response: 'Response'):
        for method in reversed(self.methods['process_response']):
            try:
                response = await common_call(method, request, response, self.crawler.spider)
            except IgnoreRequestError as exp:
                self._create_background_task(self.crawler.subscriber.notify(CrawlerEvent.IGNORE_REQUEST, exp, request, self.crawler.spider))
            if isinstance(response, Request):
                return response
            if isinstance(response, Response):
                continue
            raise InvalidOutputError(
                f"{self._get_method_class_name(method)}. must return Request or Response, got {type(response).__name__}"
            )
        return response

    async def _process_exception(self, request: 'Request', exp: Exception):
        for method in self.methods['process_exception']:
            response = await common_call(method, request, exp, self.crawler.spider)
            if response is None:
                continue
            if isinstance(response, (Request, Response)):
                return response
            if response:
                break
            raise InvalidOutputError(
                f"{self._get_method_class_name(method)}. must return None or Request or Response, got {type(response).__name__}"
            )
        else:
            raise exp

    async def download(self, request) -> 'Optional[Response]':
        """ called in the download method. """
        try:
            response = await self._process_request(request)
        except KeyError:
            raise RequestMethodError(f"{request.method.lower()} is not supported")
        except IgnoreRequestError as exp:
            self._create_background_task(self.crawler.subscriber.notify(CrawlerEvent.IGNORE_REQUEST, exp, request, self.crawler.spider))
            response = await self._process_exception(request, exp)
        except Exception as exp:
            self._stats.inc_value(f'download_error/{exp.__class__.__name__}')
            response = await self._process_exception(request, exp)
        else:
            self._create_background_task(self.crawler.subscriber.notify(CrawlerEvent.RESPONSE_RECEIVED, response, self.crawler.spider))
            self._stats.inc_value('response_received_count')
            
            # 实时分类统计响应状态码
            if isinstance(response, Response):
                status_code = response.status
                self._stats.inc_value(f'response_status_code/{status_code}')
                
                # 分类统计
                if 300 <= status_code < 400:
                    self._stats.inc_value('response_status_code/3xx')
                elif 400 <= status_code < 500:
                    self._stats.inc_value('response_status_code/4xx')
                elif 500 <= status_code < 600:
                    self._stats.inc_value('response_status_code/5xx')

        if isinstance(response, Response):
            response = await self._process_response(request, response)
        if isinstance(response, Request):
            # 检测是否是重试请求
            retry_times = response.meta.get('retry_times', 0)
            retry_depth = response.meta.get('_retry_depth', 0)
            
            # 检查重试深度限制，防止无限递归
            if retry_depth >= self.MAX_RETRY_DEPTH:
                self.logger.error(
                    f"达到最大重试深度 ({self.MAX_RETRY_DEPTH})，放弃重试: {response.url}"
                )
                raise RuntimeError(
                    f"Maximum retry depth ({self.MAX_RETRY_DEPTH}) exceeded for: {response.url}"
                )
            
            if retry_times > 0:
                # 重试请求，计算指数退避时间
                backoff_time = min(
                    self.RETRY_BACKOFF_BASE * (2 ** (retry_times - 1)),
                    self.RETRY_BACKOFF_MAX
                )
                response.meta['retry_backoff'] = backoff_time
                
                if backoff_time > 0:
                    self.logger.debug(
                        f"重试请求（退避 {backoff_time:.1f}s）: {response.url} "
                        f"(retry_times={retry_times})"
                    )
                    await asyncio.sleep(backoff_time)
                    self.logger.debug(
                        f"等待完成，准备重试: {response.url} "
                        f"(retry_times={retry_times})"
                    )
                else:
                    self.logger.debug(f"立即重试请求: {response.url} (retry_times={retry_times})")
                
                # 更新重试深度
                response.meta['_retry_depth'] = retry_depth + 1
                
                self.logger.debug(f"开始执行重试下载: {response.url} (depth={response.meta['_retry_depth']})")
                return await self.download(response)
            else:
                # 普通新请求，入队等待调度
                await self.crawler.engine.enqueue_request(response)
                return None
        return response

    @classmethod
    def create_instance(cls, *args, **kwargs):
        return cls(*args, **kwargs)

    def _add_middleware(self, middlewares):
        # 支持中间件优先级：中间件可以是字符串、元组 (middleware_path, priority) 或字典 {'middleware_path': priority}
        processed_middlewares = []
        
        # 检查是否是字典格式
        if isinstance(middlewares, dict):
            # 字典格式: {'middleware_path': priority}
            for middleware_path, priority in middlewares.items():
                processed_middlewares.append((middleware_path, priority))
        else:
            # 传统格式：列表中包含字符串或元组
            for item in middlewares:
                if isinstance(item, (list, tuple)) and len(item) == 2:
                    middleware_path, priority = item
                    processed_middlewares.append((middleware_path, priority))
                elif isinstance(item, str):
                    # 默认优先级为0
                    processed_middlewares.append((item, 0))
                else:
                    # 跳过无效条目
                    continue
        
        # 按优先级排序（高优先级在前）
        processed_middlewares.sort(key=lambda x: x[1], reverse=True)
        
        enabled_middlewares = []
        for middleware_path, priority in processed_middlewares:
            if self._validate_middleware(middleware_path):
                enabled_middlewares.append((middleware_path, priority))
        
        if enabled_middlewares:
            # 只打印一次中间件启用日志（避免多个下载器实例重复打印）
            if not MiddlewareManager._logged_enabled:
                MiddlewareManager._logged_enabled = True
                # 恢复INFO级别日志，保留关键的启用信息
                # 格式化中间件列表，使其更像字典格式，更易读
                if len(enabled_middlewares) == 1:
                    # 只有一个中间件时，单行显示
                    middleware_path, priority = enabled_middlewares[0]
                    self.logger.info(f'Enabled middlewares: {{{middleware_path!r}: {priority}}}')
                else:
                    # 多个中间件时，多行显示，类似字典格式
                    formatted_output = '{\n'
                    for i, (middleware_path, priority) in enumerate(enabled_middlewares):
                        is_last = (i == len(enabled_middlewares) - 1)
                        comma = ',' if not is_last else ''
                        formatted_output += f"  {middleware_path!r}: {priority}{comma}\n"
                    formatted_output += '}'
                    self.logger.info(f'Enabled middlewares:\n{formatted_output}')

    def _validate_middleware(self, middleware):
        middleware_cls = load_object(middleware)
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

    def _get_method_class_name(self, method):
        """安全地获取方法所属的类名"""
        if hasattr(method, '__self__'):
            return method.__self__.__class__.__name__
        else:
            return str(method)