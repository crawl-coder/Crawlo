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
    """请求优先级常量"""
    HIGH = -100
    NORMAL = 0
    LOW = 100


class Request:
    """
    封装一个 HTTP 请求对象，用于爬虫框架中表示一个待抓取的请求任务。
    支持 JSON、表单、原始 body 提交，自动处理 Content-Type 与编码。
    不支持文件上传（multipart/form-data），保持轻量。
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
        'flags',
        '_json_body',
        '_form_data'
    )

    def __init__(
        self,
        url: str,
        callback: Optional[Callable] = None,
        method: Optional[str] = 'GET',
        headers: Optional[Dict[str, str]] = None,
        body: Optional[Union[bytes, str, Dict[Any, Any]]] = None,
        form_data: Optional[Dict[Any, Any]] = None,
        json_body: Optional[Dict[Any, Any]] = None,
        cb_kwargs: Optional[Dict[str, Any]] = None,
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

        :param url: 请求 URL（必须）
        :param callback: 成功回调函数
        :param method: HTTP 方法，默认 GET
        :param headers: 请求头
        :param body: 原始请求体（bytes/str），若为 dict 且未使用 json_body/form_data，则自动转为 JSON
        :param form_data: 表单数据，自动转为 application/x-www-form-urlencoded
        :param json_body: JSON 数据，自动序列化并设置 Content-Type
        :param cb_kwargs: 传递给 callback 的额外参数
        :param cookies: Cookies 字典
        :param meta: 元数据（跨中间件传递数据）
        :param priority: 优先级（数值越小越优先）
        :param dont_filter: 是否跳过去重
        :param timeout: 超时时间（秒）
        :param proxy: 代理地址，如 http://127.0.0.1:8080
        :param allow_redirects: 是否允许重定向
        :param auth: 认证元组 (username, password)
        :param verify: 是否验证 SSL 证书
        :param flags: 标记（用于调试或分类）
        :param encoding: 字符编码，默认 utf-8
        """
        self.callback = callback
        self.method = str(method).upper()
        self.headers = headers or {}
        self.cookies = cookies or {}
        self.priority = -priority  # 用于排序：值越小优先级越高
        self._meta = deepcopy(meta) if meta is not None else {}
        self.timeout = self._meta.get('download_timeout', timeout)
        self.proxy = proxy
        self.allow_redirects = allow_redirects
        self.auth = auth
        self.verify = verify
        self.flags = flags or []
        self.encoding = encoding
        self.cb_kwargs = cb_kwargs or {}
        self.body = body
        # 保存高层语义参数（用于 copy）
        self._json_body = json_body
        self._form_data = form_data

        # 构建 body
        if json_body is not None:
            if 'Content-Type' not in self.headers:
                self.headers['Content-Type'] = 'application/json'
            self.body = json.dumps(json_body, ensure_ascii=False).encode(encoding)
            if self.method == 'GET':
                self.method = 'POST'

        elif form_data is not None:
            if self.method == 'GET':
                self.method = 'POST'
            if 'Content-Type' not in self.headers:
                self.headers['Content-Type'] = 'application/x-www-form-urlencoded'
            query_str = urlencode(form_data)
            self.body = query_str.encode(encoding)  # ✅ 显式编码为 bytes


        else:
            # 处理原始 body
            if isinstance(self.body, dict):
                if 'Content-Type' not in self.headers:
                    self.headers['Content-Type'] = 'application/json'
                self.body = json.dumps(self.body, ensure_ascii=False).encode(encoding)
            elif isinstance(self.body, str):
                self.body = self.body.encode(encoding)

        self.dont_filter = dont_filter
        self._set_url(url)

    def copy(self: _Request) -> _Request:
        """
        创建当前请求的副本，保留所有高层语义（json_body/form_data）。
        """
        return type(self)(
            url=self.url,
            callback=self.callback,
            method=self.method,
            headers=self.headers.copy(),
            body=None,  # 由 form_data/json_body 重新生成
            form_data=self._form_data,
            json_body=self._json_body,
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
            encoding=self.encoding
        )

    def set_meta(self, key: str, value: Any) -> None:
        """设置 meta 中的某个键值。"""
        self._meta[key] = value

    def _set_url(self, url: str) -> None:
        """安全设置 URL，确保格式正确。"""
        if not isinstance(url, str):
            raise TypeError(f"Request url 必须为字符串，当前类型: {type(url).__name__}")

        s = safe_url_string(url, self.encoding)
        escaped_url = escape_ajax(s)
        self._url = escaped_url

        if not self._url.startswith(('http://', 'https://')):
            raise ValueError(f"URL 缺少 scheme: {self._url}")

    @property
    def url(self) -> str:
        return self._url

    @property
    def meta(self) -> Dict[str, Any]:
        return self._meta

    def __str__(self) -> str:
        return f'<Request url={self.url} method={self.method}>'

    def __repr__(self) -> str:
        return str(self)

    def __lt__(self, other: _Request) -> bool:
        """用于按优先级排序"""
        return self.priority < other.priority