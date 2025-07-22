#!/usr/bin/python
# -*- coding: UTF-8 -*-
import json
from copy import deepcopy
from urllib.parse import urlencode
from w3lib.url import safe_url_string
from typing import Dict, Optional, Callable, Union, Any, TypeVar, List

from crawlo.utils.url import escape_ajax

_Request = TypeVar("_Request", bound="Request")


class RequestPriority:
    HIGH = -100
    NORMAL = 0
    LOW = 100


class Request:
    """
    封装一个 HTTP 请求对象，用于爬虫框架中表示一个待抓取的请求任务。
    支持设置回调函数、请求头、请求体、优先级、元数据等。
    """

    __slots__ = (
        '_url',
        '_meta',
        'callback',
        'cb_kwargs',
        'err_back',
        'headers',
        'body',
        'method',
        'cookies',
        'priority',
        'encoding',
        'dont_filter',
        'timeout',
        'proxy',
        'allow_redirects',
        'auth',
        'verify',
        'flags'
    )

    def __init__(
        self,
        url: str,
        callback: Optional[Callable] = None,
        method: Optional[str] = 'GET',
        headers: Optional[Dict[str, str]] = None,
        body: Optional[Union[Dict, bytes, str]] = None,
        form_data: Optional[Dict] = None,
        json_body: Optional[Dict] = None,   # ✅ 参数名从 json 改为 json_body
        cb_kwargs: Optional[Dict[str, Any]] = None,
        err_back: Optional[Callable] = None,
        cookies: Optional[Dict[str, str]] = None,
        meta: Optional[Dict[str, Any]] = None,
        priority: int = RequestPriority.NORMAL,
        dont_filter: bool = False,
        timeout: Optional[float] = None,
        proxy: Optional[str] = None,
        allow_redirects: bool = True,
        auth: Optional[tuple] = None,
        verify: bool = True,
        flags: Optional[List[str]] = None,
        encoding: str = 'utf-8'
    ):
        """
        初始化请求对象。

        参数说明:
        :param url: 请求的 URL 地址（必须）
        :param callback: 响应处理回调函数（可选）
        :param method: HTTP 请求方法，默认为 GET
        :param headers: 请求头（可选）
        :param body: 请求体（可为 dict、bytes 或 str）
        :param form_data 表单数据，自动设置为 POST 并构造 x-www-form-urlencoded 请求体
        :param json_body: 用于构造 JSON 请求体，自动设置 Content-Type 为 application/json
        :param cb_kwargs: 传递给回调函数的额外参数（可选）
        :param err_back: 请求失败时的错误回调函数（可选）
        :param cookies: 请求 cookies（可选）
        :param meta: 元数据字典，用于在请求间传递数据
        :param priority: 请求优先级，数值越小优先级越高（默认为 0）
        :param dont_filter: 是否跳过去重过滤（默认为 False）
        :param timeout: 请求超时时间（秒）
        :param proxy: 代理地址（如：http://127.0.0.1:8080）
        :param allow_redirects: 是否允许重定向（默认为 True）
        :param auth: 认证信息，格式为 (username, password)
        :param verify: 是否验证 SSL 证书（默认为 True）
        :param flags: 请求标记（调试、重试等用途）
        """
        self.callback = callback
        self.method = str(method).upper()
        self.headers = headers or {}
        self.body = body
        self.cb_kwargs = cb_kwargs or {}
        self.err_back = err_back
        self.cookies = cookies or {}
        self.priority = -priority  # 高优先级值更小，便于排序
        self._meta = deepcopy(meta) if meta is not None else {}
        self.timeout = self._meta.get('download_timeout', timeout)
        self.proxy = proxy
        self.allow_redirects = allow_redirects
        self.auth = auth
        self.verify = verify
        self.flags = flags or []

        # 默认编码
        self.encoding = encoding

        # 优先使用 json_body 参数
        if json_body is not None:
            if 'Content-Type' not in self.headers:
                self.headers['Content-Type'] = 'application/json'
            self.body = json.dumps(json_body, ensure_ascii=False).encode(self.encoding)
            if self.method == 'GET':
                self.method = 'POST'

        # 其次使用 form_data
        elif form_data is not None:
            if self.method == 'GET':
                self.method = 'POST'
            if 'Content-Type' not in self.headers:
                self.headers['Content-Type'] = 'application/x-www-form-urlencoded'
            self.body = urlencode(form_data)

        # 最后处理 body 为 dict 的情况
        elif isinstance(self.body, dict):
            if 'Content-Type' not in self.headers:
                self.headers['Content-Type'] = 'application/json'
            self.body = json.dumps(self.body, ensure_ascii=False).encode(self.encoding)

        self.dont_filter = dont_filter
        self._set_url(url)

    def copy(self: _Request) -> _Request:
        """
        创建当前 Request 的副本，用于避免引用共享数据。

        :return: 一个新的 Request 实例
        """
        return type(self)(
            url=self.url,
            callback=self.callback,
            method=self.method,
            headers=self.headers.copy(),
            body=self.body,
            form_data=None,  # form_data 不参与复制
            json_body=None,   # json_body 参数也不参与复制
            cb_kwargs=deepcopy(self.cb_kwargs),
            err_back=self.err_back,
            cookies=self.cookies.copy(),
            meta=deepcopy(self._meta),
            priority=-self.priority,
            dont_filter=self.dont_filter,
            timeout=self.timeout,
            proxy=self.proxy,
            allow_redirects=self.allow_redirects,
            auth=self.auth,
            verify=self.verify,
            flags=self.flags.copy(),
        )

    def set_meta(self, key: str, value: Any) -> None:
        """
        设置 meta 中的某个键值对。

        :param key: 要设置的键
        :param value: 对应的值
        """
        self._meta[key] = value

    def _set_url(self, url: str) -> None:
        """
        设置并验证 URL，确保其格式正确且包含 scheme。

        :param url: 原始 URL 字符串
        :raises TypeError: 如果传入的不是字符串
        :raises ValueError: 如果 URL 没有 scheme
        """
        if not isinstance(url, str):
            raise TypeError(f"Request url 必须为字符串类型，当前类型为 {type(url).__name__}")

        s = safe_url_string(url, self.encoding)
        escaped_url = escape_ajax(s)
        self._url = escaped_url

        if not self._url.startswith(('http://', 'https://', 'about:', '')):
            raise ValueError(f"请求 URL 缺少 scheme（如 http://）: {self._url}")

    @property
    def url(self) -> str:
        """
        获取请求的 URL。

        :return: 当前请求的 URL 字符串
        """
        return self._url

    @property
    def meta(self) -> Dict[str, Any]:
        """
        获取请求的元数据。

        :return: 元数据字典
        """
        return self._meta

    def __str__(self) -> str:
        """
        返回对象的字符串表示，用于调试和日志输出。

        :return: 字符串 <Request url=... method=...>
        """
        return f'<Request url={self.url} method={self.method}>'

    def __repr__(self) -> str:
        """
        返回对象的官方字符串表示。

        :return: 字符串，与 __str__ 相同
        """
        return str(self)

    def __lt__(self, other: _Request) -> bool:
        """
        比较两个请求的优先级，用于排序。

        :param other: 另一个 Request 对象
        :return: 如果当前请求优先级更高（数值更小）返回 True
        """
        return self.priority < other.priority