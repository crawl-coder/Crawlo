#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
HTTP Request 封装模块
====================
提供功能完善的HTTP请求封装，支持:
- JSON/表单数据自动处理
- GET请求参数处理
- 优先级排序机制
- 安全的深拷贝操作
- 灵活的请求配置
"""
import json
from copy import deepcopy
from enum import IntEnum
from typing import Dict, Optional, Callable, Union, Any, TypeVar, List, TYPE_CHECKING
from urllib.parse import urldefrag, urlencode, urlparse, urlunparse, parse_qsl

from w3lib.url import safe_url_string, add_or_replace_parameter

_Request = TypeVar("_Request", bound="Request")


class RequestPriority(IntEnum):
    """
    请求优先级枚举。
    
    数值越大，优先级越高（用户传入正值，更符合直觉）。
    内部存储时会自动取反，确保队列按值小的先出队。
    
    Examples:
        >>> request = Request(url, priority=RequestPriority.HIGH)
        >>> request.priority = RequestPriority.URGENT
    
    优先级映射：
        用户传入值 → 存储值 → 出队顺序
        URGENT(200)    → -200   → 最先出队
        HIGH(100)      → -100   → 第二出队
        NORMAL(0)      → 0      → 正常出队
        LOW(-100)      → 100    → 较后出队
        BACKGROUND(-200) → 200  → 最后出队
    
    注意：
        内部存储使用负值是为了兼容 Python 的 heapq（最小堆）。
        用户只需关注传入的正值，框架会自动处理取反逻辑。
    """
    URGENT = 200       # 紧急任务（最高优先级）
    HIGH = 100         # 高优先级  
    NORMAL = 0         # 正常优先级(默认)
    LOW = -100         # 低优先级
    BACKGROUND = -200  # 后台任务（最低优先级）


class Request:
    """
    封装一个 HTTP 请求对象，用于爬虫框架中表示一个待抓取的请求任务。
    支持 JSON、表单、GET参数、原始 body 提交，自动处理 Content-Type 与编码。
    不支持文件上传（multipart/form-data），保持轻量。
    """

    __slots__ = (
        '_url',
        '_meta',
        'callback',
        'cb_kwargs',
        'errback',
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
        '_form_data',
        '_params',
        '_original_url',  # 保存原始 URL（不含参数），用于 copy
        'use_dynamic_loader',
    )

    def __init__(
        self,
        url: str,
        callback: Optional[Callable] = None,
        errback: Optional[Callable] = None,
        method: Optional[str] = 'GET',
        headers: Optional[Dict[str, str]] = None,
        body: Optional[Union[bytes, str, Dict[Any, Any]]] = None,
        form_data: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
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
        encoding: Optional[str] = None,  
        use_dynamic_loader: bool = False
    ) -> None:
        """
        初始化请求对象。

        Args:
            url: 请求 URL（必须）
            callback: 成功回调函数
            errback: 错误回调函数
            method: HTTP 方法，默认 GET
            headers: 请求头
            body: 原始请求体（bytes/str），若为 dict 且未使用 json_body/form_data，则自动转为 JSON
            form_data: 表单数据，POST请求时自动转为 application/x-www-form-urlencoded
            json_body: JSON 数据，自动序列化并设置 Content-Type
            params: GET请求参数，会自动附加到URL上
            cb_kwargs: 传递给 callback 的额外参数
            cookies: Cookies 字典
            meta: 元数据（跨中间件传递数据）
            priority: 优先级（数值越小越优先）
            dont_filter: 是否跳过去重
            timeout: 超时时间（秒）
            proxy: 代理地址，如 http://127.0.0.1:8080
            allow_redirects: 是否允许重定向
            auth: 认证元组 (username, password)
            verify: 是否验证 SSL 证书
            flags: 标记（用于调试或分类）
            encoding: 字符编码，默认 utf-8
            use_dynamic_loader: 是否使用动态加载器
        """
        # Basic URL validation
        if not url or not isinstance(url, str) or url.strip() == '':
            raise ValueError("URL cannot be empty")
        
        self.callback = callback
        self.errback = errback
        self.method = str(method).upper()
        self.headers = headers or {}
        self.cookies = cookies or {}
        # Internal: negate priority for min-heap queue (smaller values = higher priority)
        # User passes positive values (URGENT=200), we store as -200 for correct queue ordering
        self.priority = -priority  # Internal storage: negated for heapq compatibility
        
        # 安全处理 meta，移除 logger 后再 deepcopy
        self._meta = self._safe_deepcopy_meta(meta) if meta is not None else {}
        
        # Save callback info to meta for serialization
        if callback is not None and hasattr(callback, '__self__') and hasattr(callback, '__name__'):
            spider_instance = getattr(callback, '__self__', None)
            if spider_instance is not None:
                self._meta['_callback_info'] = {
                    'spider_class': spider_instance.__class__.__name__,
                    'method_name': callback.__name__
                }
        
        self.timeout = self._meta.get('download_timeout', timeout)
        self.proxy = proxy
        self.allow_redirects = allow_redirects
        self.auth = auth
        self.verify = verify
        self.flags = flags or []
        self.encoding = encoding
        self.cb_kwargs = cb_kwargs or {}
        self.body = body
        self.use_dynamic_loader = use_dynamic_loader
        
        # 保存高层语义参数（用于 copy）
        self._json_body = json_body
        self._form_data = form_data
        self._params = params
        self._original_url = url  # 保存原始 URL（不含参数），用于 copy

        # 处理GET参数
        if params is not None and self.method == 'GET':
            # 将GET参数附加到URL上
            self._url = self._add_params_to_url(url, params)
        else:
            self._url = url

        # 构建 body
        if json_body is not None:
            if 'Content-Type' not in self.headers:
                self.headers['Content-Type'] = 'application/json'
            self.body = json.dumps(json_body, ensure_ascii=False).encode(encoding or 'utf-8')
            if self.method == 'GET':
                self.method = 'POST'

        elif form_data is not None:
            if self.method == 'GET':
                # 对于GET请求，将form_data作为GET参数处理
                self._url = self._add_params_to_url(self._url, form_data)
            else:
                # 对于POST等请求，将form_data作为请求体处理
                if 'Content-Type' not in self.headers:
                    self.headers['Content-Type'] = 'application/x-www-form-urlencoded'
                query_str = urlencode(form_data)
                self.body = query_str.encode(encoding or 'utf-8')  # 显式编码为 bytes


        else:
            # 处理原始 body
            if isinstance(self.body, dict):
                if 'Content-Type' not in self.headers:
                    self.headers['Content-Type'] = 'application/json'
                self.body = json.dumps(self.body, ensure_ascii=False).encode(encoding or 'utf-8')
            elif isinstance(self.body, str):
                self.body = self.body.encode(encoding or 'utf-8')

        self.dont_filter = dont_filter
        self._set_url(self._url)

    @staticmethod
    def _add_params_to_url(url: str, params: Dict[str, Any], replace: bool = True) -> str:
        """
        将参数添加到 URL 中
            
        Args:
            url: 原始 URL
            params: 参数字典
            replace: 是否覆盖已有参数（默认 True）
                
        Returns:
            str: 添加参数后的 URL
        """
        if not params:
            return url
                
        # 解析 URL
        parsed = urlparse(url)
        # 解析现有查询参数
        query_params = dict(parse_qsl(parsed.query, keep_blank_values=True))
            
        # 添加新参数
        if replace:
            # 覆盖模式：新参数替换旧参数
            query_params.update({str(k): str(v) for k, v in params.items()})
        else:
            # 追加模式：保留旧参数，添加新参数
            for key, value in params.items():
                key_str = str(key)
                if key_str not in query_params:
                    query_params[key_str] = str(value)
            
        # 重新构建查询字符串
        new_query = urlencode(query_params)
        # 构建新的 URL
        return urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query,
            parsed.fragment
        ))

    @staticmethod
    def _safe_deepcopy_meta(meta: Dict[str, Any]) -> Dict[str, Any]:
        """
        安全地 deepcopy meta，移除 logger 后再复制
        
        Args:
            meta: 元数据字典
            
        Returns:
            Dict[str, Any]: 深拷贝后的元数据字典
        """
        import logging
        
        MAX_DEPTH = 50  # 最大递归深度
        
        def clean_logger_recursive(obj: Any, depth: int = 0) -> Any:
            """递归移除 logger 对象（带深度限制）"""
            # 深度检查
            if depth > MAX_DEPTH:
                raise ValueError(
                    f"Meta nesting too deep (>{MAX_DEPTH} levels). "
                    f"Check for circular references or excessive nesting."
                )
            
            if isinstance(obj, logging.Logger):
                return None
            elif isinstance(obj, dict):
                cleaned = {}
                for k, v in obj.items():
                    if not (k == 'logger' or isinstance(v, logging.Logger)):
                        cleaned[k] = clean_logger_recursive(v, depth + 1)
                return cleaned
            elif isinstance(obj, (list, tuple)):
                cleaned_list = []
                for item in obj:
                    cleaned_item = clean_logger_recursive(item, depth + 1)
                    if cleaned_item is not None:
                        cleaned_list.append(cleaned_item)
                return type(obj)(cleaned_list)
            else:
                return obj
        
        try:
            # 先清理 logger，再 deepcopy
            cleaned_meta = clean_logger_recursive(meta)
            # 确保返回字典类型
            if not isinstance(cleaned_meta, dict):
                return {}
            return deepcopy(cleaned_meta)
        except ValueError:
            # 重新抛出深度异常
            raise
        except Exception as e:
            # 其他异常降级为浅拷贝
            get_logger('Request').warning(
                f"Failed to deep copy meta: {e}, falling back to shallow copy"
            )
            return dict(meta)

    def copy(self: _Request) -> _Request:
        """
        创建当前请求的副本，保留所有高层语义（json_body/form_data/params）。
        
        注意：使用原始 URL（不含查询参数），由 params 重新拼接，避免参数重复。
        
        Returns:
            Request: 请求副本
        """
        return type(self)(
            url=self._original_url,  # 使用原始 URL，避免参数重复
            callback=self.callback,
            method=self.method,
            headers=self.headers.copy(),
            body=None,  # 由 form_data/json_body/params 重新生成
            form_data=self._form_data,
            json_body=self._json_body,
            params=self._params,
            cb_kwargs=deepcopy(self.cb_kwargs),
            errback=self.errback,
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
            encoding=self.encoding,
            use_dynamic_loader=self.use_dynamic_loader
        )
    
    def __copy__(self: _Request) -> _Request:
        """
        Shallow copy optimization (for performance-critical scenarios).
        
        Note: This is a shallow copy, use copy() for deep copy.
        
        Returns:
            Request: Shallow copy of request
        """
        new_request = type(self).__new__(type(self))
        for slot in self.__slots__:
            setattr(new_request, slot, getattr(self, slot))
        return new_request

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize Request to dict (for queue storage, distributed transfer).
        
        Returns:
            Dict[str, Any]: Serialized request dictionary
            
        Example:
            >>> request = Request('http://example.com', params={'page': 1})
            >>> data = request.to_dict()
            >>> # {'url': 'http://example.com', 'method': 'GET', ...}
        """
        return {
            'url': self._original_url,
            'method': self.method,
            'headers': self.headers.copy(),
            'body': self.body.decode('utf-8', errors='replace') if isinstance(self.body, bytes) else self.body,
            'form_data': self._form_data,
            'json_body': self._json_body,
            'params': self._params,
            'cb_kwargs': deepcopy(self.cb_kwargs),
            'cookies': self.cookies.copy(),
            'meta': deepcopy(self._meta),
            'priority': -self.priority,  # Negate to positive value
            'dont_filter': self.dont_filter,
            'timeout': self.timeout,
            'proxy': self.proxy,
            'allow_redirects': self.allow_redirects,
            'auth': self.auth,
            'verify': self.verify,
            'flags': list(self.flags),
            'encoding': self.encoding,
            'use_dynamic_loader': self.use_dynamic_loader,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Request':
        """
        Deserialize Request from dict.
        
        Args:
            data: Serialized request dictionary
            
        Returns:
            Request: Deserialized request object
            
        Example:
            >>> data = {'url': 'http://example.com', 'method': 'GET', ...}
            >>> request = Request.from_dict(data)
        """
        url = data.get('url')
        if not url or not isinstance(url, str):
            raise ValueError(
                f"Invalid URL in request data: {repr(url)}. "
                f"Full data keys: {list(data.keys()) if isinstance(data, dict) else 'N/A'}"
            )
        
        return cls(
            url=url,
            method=data.get('method', 'GET'),
            headers=data.get('headers'),
            body=data.get('body'),
            form_data=data.get('form_data'),
            json_body=data.get('json_body'),
            params=data.get('params'),
            cb_kwargs=data.get('cb_kwargs'),
            cookies=data.get('cookies'),
            meta=data.get('meta'),
            priority=data.get('priority', 0),
            dont_filter=data.get('dont_filter', False),
            timeout=data.get('timeout'),
            proxy=data.get('proxy'),
            allow_redirects=data.get('allow_redirects', True),
            auth=data.get('auth'),
            verify=data.get('verify', True),
            flags=data.get('flags'),
            encoding=data.get('encoding'),
            use_dynamic_loader=data.get('use_dynamic_loader', False),
        )

    @classmethod
    def get(cls, url: str, **kwargs) -> 'Request':
        """
        Create a GET request.
        
        Args:
            url: Request URL
            **kwargs: Additional request parameters
            
        Returns:
            Request: GET request object
            
        Example:
            >>> request = Request.get('http://example.com', params={'page': 1})
        """
        return cls(url, method='GET', **kwargs)
    
    @classmethod
    def post(cls, url: str, **kwargs) -> 'Request':
        """
        Create a POST request.
        
        Args:
            url: Request URL
            **kwargs: Additional request parameters (json_body, form_data, etc.)
            
        Returns:
            Request: POST request object
            
        Example:
            >>> request = Request.post('http://example.com/api', json_body={'key': 'value'})
        """
        return cls(url, method='POST', **kwargs)

    def set_meta(self, key: str, value: Any) -> 'Request':
        """
        设置 meta 中的某个键值，支持链式调用。
        
        Args:
            key: 键名
            value: 键值
            
        Returns:
            Request: 支持链式调用
        """
        self._meta[key] = value
        return self
    
    def add_header(self, key: str, value: str) -> 'Request':
        """
        添加请求头，支持链式调用。
        
        Args:
            key: 请求头键名
            value: 请求头值
            
        Returns:
            Request: 支持链式调用
        """
        self.headers[key] = value
        return self
    
    def add_headers(self, headers: Dict[str, str]) -> 'Request':
        """
        批量添加请求头，支持链式调用。
        
        Args:
            headers: 请求头字典
            
        Returns:
            Request: 支持链式调用
        """
        self.headers.update(headers)
        return self
    
    def set_proxy(self, proxy: str) -> 'Request':
        """
        设置代理，支持链式调用。
        
        Args:
            proxy: 代理地址
            
        Returns:
            Request: 支持链式调用
        """
        self.proxy = proxy
        return self
    
    def set_timeout(self, timeout: float) -> 'Request':
        """
        设置超时时间，支持链式调用。
        
        Args:
            timeout: 超时时间（秒）
            
        Returns:
            Request: 支持链式调用
        """
        self.timeout = timeout
        return self
    
    def add_flag(self, flag: str) -> 'Request':
        """
        添加标记，支持链式调用。
        
        Args:
            flag: 标记
            
        Returns:
            Request: 支持链式调用
        """
        if flag not in self.flags:
            self.flags.append(flag)
        return self
    
    def remove_flag(self, flag: str) -> 'Request':
        """
        移除标记，支持链式调用。
        
        Args:
            flag: 标记
            
        Returns:
            Request: 支持链式调用
        """
        if flag in self.flags:
            self.flags.remove(flag)
        return self
    
    def set_dynamic_loader(self, use_dynamic: bool = True, options: Optional[Dict[str, Any]] = None) -> 'Request':
        """
        设置使用动态加载器，支持链式调用。
        
        Args:
            use_dynamic: 是否使用动态加载器
            options: 动态加载器选项
            
        Returns:
            Request: 支持链式调用
        """
        self.use_dynamic_loader = use_dynamic
        # 同时在meta中设置标记，供混合下载器使用
        self._meta['use_dynamic_loader'] = use_dynamic
        return self
    
    def set_protocol_loader(self) -> 'Request':
        """
        强制使用协议加载器，支持链式调用。
        
        Returns:
            Request: 支持链式调用
        """
        self.use_dynamic_loader = False
        self._meta['use_dynamic_loader'] = False
        self._meta['use_protocol_loader'] = True
        return self

    def _set_url(self, url: str) -> None:
        """
        安全设置 URL，确保格式正确。
        
        Args:
            url: URL字符串
        """
        if not isinstance(url, str):
            raise TypeError(f"Request url 必须为字符串，当前类型: {type(url).__name__}")
        
        if not url.strip():
            raise ValueError("URL 不能为空")
        
        # 检查危险的 URL scheme
        dangerous_schemes = ['file://', 'ftp://', 'javascript:', 'data:']
        if any(url.lower().startswith(scheme) for scheme in dangerous_schemes):
            raise ValueError(f"URL scheme 不安全: {url[:20]}...")

        # URL 编码使用 UTF-8 作为默认值（仅用于 URL 字符串处理）
        url_encoding = self.encoding if self.encoding else 'utf-8'
        s = safe_url_string(url, url_encoding)
        escaped_url = escape_ajax(s)
        
        if not escaped_url.startswith(('http://', 'https://')):
            raise ValueError(f"URL 缺少 HTTP(S) scheme: {escaped_url[:50]}...")
        
        # 检查 URL 长度
        if len(escaped_url) > 8192:  # 大多数服务器支持的最大 URL 长度
            raise ValueError(f"URL 过长 (超过 8192 字符): {len(escaped_url)} 字符")
        
        self._url = escaped_url

    @property
    def url(self) -> str:
        """
        获取URL
        
        Returns:
            str: URL字符串
        """
        return self._url

    @property
    def meta(self) -> Dict[str, Any]:
        """
        获取元数据
        
        Returns:
            Dict[str, Any]: 元数据字典
        """
        return self._meta

    def __str__(self) -> str:
        return f'<Request url={self.url} method={self.method}>'

    def __repr__(self) -> str:
        return str(self)

    def __lt__(self, other: _Request) -> bool:
        """
        用于按优先级排序
        
        Args:
            other: 另一个请求对象
            
        Returns:
            bool: 是否优先级更高
        """
        return self.priority < other.priority

def escape_ajax(url: str) -> str:
    """
    根据Google AJAX爬取规范转换URL（处理哈希片段#!）：
    https://developers.google.com/webmasters/ajax-crawling/docs/getting-started

    规则说明：
    1. 仅当URL包含 `#!` 时才转换（表示这是AJAX可爬取页面）
    2. 将 `#!key=value` 转换为 `?_escaped_fragment_=key%3Dvalue`
    3. 保留原始查询参数（如果有）

    示例：
    >>> escape_ajax("www.example.com/ajax.html#!key=value")
    'www.example.com/ajax.html?_escaped_fragment_=key%3Dvalue'
    >>> escape_ajax("www.example.com/ajax.html?k1=v1#!key=value")
    'www.example.com/ajax.html?k1=v1&_escaped_fragment_=key%3Dvalue'
    >>> escape_ajax("www.example.com/ajax.html#!")
    'www.example.com/ajax.html?_escaped_fragment_='

    非AJAX可爬取的URL（无#!）原样返回：
    >>> escape_ajax("www.example.com/ajax.html#normal")
    'www.example.com/ajax.html#normal'
    
    Args:
        url: 原始URL
        
    Returns:
        str: 转换后的URL
    """
    # 分离URL的基础部分和哈希片段
    de_frag, frag = urldefrag(url)

    # 仅处理以"!"开头的哈希片段（Google规范）
    if not frag.startswith("!"):
        return url  # 不符合规则则原样返回

    # 调用辅助函数添加 `_escaped_fragment_` 参数
    return add_or_replace_parameter(de_frag, "_escaped_fragment_", frag[1:])