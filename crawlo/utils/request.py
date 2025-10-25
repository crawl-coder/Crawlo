#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
# @Time    :    2025-07-08 08:55
# @Author  :   crawl-coder
# @Desc    :   None
"""
import importlib
import json
import hashlib
from typing import Any, Optional, Iterable, Union, Dict
from w3lib.url import canonicalize_url

from crawlo import Request


def to_bytes(data: Any, encoding: str = 'utf-8') -> bytes:
    """
    将各种类型统一转换为 bytes。

    Args:
        data: 要转换的数据，支持 str, bytes, dict, int, float, bool, None 等类型
        encoding: 字符串编码格式，默认为 'utf-8'

    Returns:
        bytes: 转换后的字节数据

    Raises:
        TypeError: 当数据类型无法转换时
        UnicodeEncodeError: 当编码失败时
        ValueError: 当 JSON 序列化失败时

    Examples:
        >>> to_bytes("hello")
        b'hello'
        >>> to_bytes({"key": "value"})
        b'{"key": "value"}'
        >>> to_bytes(123)
        b'123'
        >>> to_bytes(None)
        b'null'
    """
    # 预检查编码参数
    if not isinstance(encoding, str):
        raise TypeError(f"encoding must be str, not {type(encoding).__name__}")

    try:
        if isinstance(data, bytes):
            return data
        elif isinstance(data, str):
            return data.encode(encoding)
        elif isinstance(data, dict):
            return json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode(encoding)
        elif isinstance(data, (int, float, bool)):
            return str(data).encode(encoding)
        elif data is None:
            return b'null'
        elif hasattr(data, '__str__'):
            # 处理其他可转换为字符串的对象
            return str(data).encode(encoding)
        else:
            raise TypeError(
                f"`data` must be str, dict, bytes, int, float, bool, or None, "
                f"not {type(data).__name__}"
            )
    except (UnicodeEncodeError, ValueError) as e:
        raise type(e)(f"Failed to convert {type(data).__name__} to bytes: {str(e)}") from e


def request_fingerprint(
        request: Request,
        include_headers: Optional[Iterable[Union[bytes, str]]] = None
) -> str:
    """
    生成请求指纹，基于方法、标准化 URL、body 和可选的 headers。
    
    .. deprecated:: 1.0.0
        此函数已废弃。请使用 :class:`crawlo.utils.fingerprint.FingerprintGenerator` 代替:
        
        .. code-block:: python
        
            from crawlo.utils.fingerprint import FingerprintGenerator
            
            fp = FingerprintGenerator.request_fingerprint(
                method=request.method,
                url=request.url,
                body=request.body or b'',
                headers=dict(request.headers) if hasattr(request, 'headers') else {}
            )
    
    此函数保留仅为向后兼容，将在 2.0.0 版本中移除。
    
    :param request: Request 对象（需包含 method, url, body, headers）
    :param include_headers: 指定要参与指纹计算的 header 名称列表（str 或 bytes）
    :return: 请求指纹（hex string）
    """
    import warnings
    warnings.warn(
        "request_fingerprint() is deprecated. "
        "Use FingerprintGenerator.request_fingerprint() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    from crawlo.utils.fingerprint import FingerprintGenerator
    
    # 准备请求数据
    method = request.method
    url = request.url
    body = request.body or b''
    headers = None
    
    # 处理 headers
    if include_headers and hasattr(request, 'headers'):
        headers = {}
        for header_name in include_headers:
            name_str = str(header_name).lower()  # 统一转为小写进行匹配
            value = ''

            # 兼容 headers 的访问方式（如 MultiDict 或 dict）
            if hasattr(request.headers, 'get_all'):
                # 如 scrapy.http.Headers 的 get_all 方法
                values = request.headers.get_all(name_str)
                value = ';'.join(str(v) for v in values) if values else ''
            elif hasattr(request.headers, '__getitem__'):
                # 如普通 dict
                try:
                    raw_value = request.headers[name_str]
                    if isinstance(raw_value, list):
                        value = ';'.join(str(v) for v in raw_value)
                    else:
                        value = str(raw_value)
                except (KeyError, TypeError):
                    value = ''
            else:
                value = ''
            
            headers[name_str] = value
    
    # 使用统一的指纹生成器
    return FingerprintGenerator.request_fingerprint(method, url, body, headers)


def set_request(request: Request, priority: int) -> None:
    """
    设置请求的深度和优先级
    
    :param request: Request 对象
    :param priority: 优先级值
    """
    # 增加请求深度
    request.meta['depth'] = request.meta.setdefault('depth', 0) + 1
    
    # 根据深度调整优先级，深度越深优先级越低
    if priority:
        request.priority -= request.meta['depth'] * priority


def request_to_dict(request: Request, spider=None) -> Dict[str, Any]:
    """
    将 Request 对象转换为可 JSON 序列化的字典，用于分布式爬虫中的请求序列化。

    Args:
        request: 要序列化的 Request 对象
        spider: 可选，用于辅助序列化（如回调函数的归属）

    Returns:
        包含 Request 所有关键信息的字典
    """
    # 基础属性
    d = {
        'url': request.url,
        'method': request.method,
        'headers': dict(request.headers),
        'body': request.body,
        'meta': request.meta.copy(),  # 复制一份
        'flags': request.flags.copy(),
        'cb_kwargs': request.cb_kwargs.copy(),
    }

    # 1. 处理 callback
    #    不能直接序列化函数，所以存储其路径
    if callable(getattr(request, 'callback', None)):
        d['_callback'] = _get_function_path(request.callback)

    # 2. 处理 errback
    if callable(getattr(request, 'err_back', None)):
        d['_errback'] = _get_function_path(request.err_back)

    # 3. 记录原始类名，以便反序列化时创建正确的实例
    d['_class'] = request.__class__.__module__ + '.' + request.__class__.__name__

    return d


def request_from_dict(d: Dict[str, Any], spider=None) -> Request:
    """
    从字典重建 Request 对象，用于分布式爬虫中的请求反序列化。

    Args:
        d: 由 request_to_dict 生成的字典
        spider: 可选，用于解析回调函数

    Returns:
        重建的 Request 对象
    """
    # 1. 获取类名并动态导入
    cls_path = d.pop('_class', None)
    if cls_path:
        module_path, cls_name = cls_path.rsplit('.', 1)
        module = importlib.import_module(module_path)
        cls = getattr(module, cls_name)
    else:
        cls = Request  # 默认为 Request

    # 2. 提取回调函数
    callback_path = d.pop('_callback', None)
    callback = _get_function_from_path(callback_path, spider) if callback_path else None

    # 3. 提取错误回调
    errback_path = d.pop('_errback', None)
    errback = _get_function_from_path(errback_path, spider) if errback_path else None

    # 5. 创建 Request 实例
    request = cls(
        url=d['url'],
        method=d.get('method', 'GET'),
        headers=d.get('headers', {}),
        body=d.get('body'),
        callback=callback,
        meta=d.get('meta', {}),
        flags=d.get('flags', []),
        cb_kwargs=d.get('cb_kwargs', {}),
    )
    
    # 手动设置 err_back 属性
    if errback is not None:
        request.err_back = errback

    return request


def _get_function_path(func: callable) -> str:
    """
    获取函数的模块路径，如 'myproject.spiders.my_spider.parse'
    """
    if hasattr(func, '__wrapped__'):
        # 处理被装饰的函数
        func = func.__wrapped__
    module = func.__module__
    if module is None or module == str.__class__.__module__:
        raise ValueError(f"无法序列化内置函数或lambda: {func}")
    return f"{module}.{func.__qualname__}"


def _get_function_from_path(path: str, spider=None) -> Optional[callable]:
    """
    从路径字符串获取函数对象。
    如果函数是 spider 的方法，会尝试绑定到 spider 实例。
    """
    try:
        module_path, func_name = path.rsplit('.', 1)
        module = importlib.import_module(module_path)

        # 逐级获取属性，支持 nested functions
        func = module
        for attr in func_name.split('.'):
            func = getattr(func, attr)

        # 如果 spider 存在，并且 func 是 spider 的方法
        if spider and hasattr(func, '__name__') and hasattr(spider, func.__name__):
            spider_method = getattr(spider, func.__name__)
            if spider_method is func:
                return spider_method  # 返回绑定的方法

        return func
    except Exception as e:
        raise ValueError(f"无法从路径 '{path}' 加载函数: {e}")

