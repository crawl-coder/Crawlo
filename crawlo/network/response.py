#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
HTTP Response 封装模块
=====================
提供功能丰富的HTTP响应封装，支持:
- 智能编码检测和解码
- XPath/CSS 选择器
- JSON 解析和缓存
- 正则表达式支持
- Cookie 处理
"""
import re
from typing import Dict, Any, List, Optional, Union, Pattern, Match, TYPE_CHECKING
from urllib.parse import urljoin as _urljoin
from parsel import Selector, SelectorList
from lxml.html import HtmlElement

# 尝试使用 ujson 提升性能，失败时降级到标准库 json
try:
    import ujson as json_module
    USE_UJSON = True
except ImportError:
    import json as json_module
    USE_UJSON = False

if TYPE_CHECKING:
    from crawlo.network.request import Request

from crawlo.exceptions import DecodeError
from crawlo.logging import get_logger
from crawlo.utils.encoding_detector import EncodingDetector
from crawlo.utils.request.response_helper import (
    parse_cookies,
    regex_search,
    regex_findall,
    regex_findone,
    get_header_value
)
from crawlo.utils.decorators import memoize_method_noargs
from crawlo.network.response_adaptive import ResponseAdaptiveMixin


class Response(ResponseAdaptiveMixin):
    """
    HTTP响应的封装，提供数据解析的便捷方法。
    
    功能特性:
    - 智能编码检测和缓存
    - 懒加载 Selector 实例
    - JSON 解析和缓存
    - 多类型数据提取
    - 自适应元素追踪（adaptive=True 自动保存指纹+失效时自愈）
    """

    # 响应体大小限制（100MB）
    MAX_BODY_SIZE = 100 * 1024 * 1024

    def __init__(
            self,
            url: str,
            *,
            headers: Optional[Dict[str, Any]] = None,
            body: bytes = b"",
            method: str = 'GET',
            request: Optional['Request'] = None,  # 使用字符串注解避免循环导入
            status: int = 200,
    ) -> None:
        """
        初始化响应对象
        
        Args:
            url: 响应URL
            headers: 响应头
            body: 响应体
            method: 请求方法
            request: 对应的请求对象
            status: HTTP 状态码
        """
        # 基本属性
        self.url: str = url
        self.headers: Dict[str, Any] = headers or {}
        
        # 检查响应体大小限制
        if len(body) > self.MAX_BODY_SIZE:
            raise ValueError(
                f"Response body too large: {len(body)} bytes "
                f"(limit: {self.MAX_BODY_SIZE} bytes)"
            )
        
        self.body: bytes = body
        self.method: str = method.upper()
        self.request: Optional['Request'] = request
        self.status: int = status

        # 请求标记（从 Request.flags 传递，供回调函数检查）
        self.flags: list = getattr(request, 'flags', []) if request else []

        # 编码处理
        self.encoding: str = self._determine_encoding()

        # 缓存属性
        self._text_cache: Optional[str] = None
        self._json_cache: Optional[Any] = None
        self._selector_instance: Optional[Selector] = None

        # 状态标记
        self._is_success: bool = 200 <= status < 300
        self._is_redirect: bool = 300 <= status < 400
        self._is_client_error: bool = 400 <= status < 500
        self._is_server_error: bool = status >= 500
    
    @classmethod
    def from_text(cls, url: str, text: str, encoding: str = 'utf-8', **kwargs) -> 'Response':
        """
        Create a Response from text.
        
        Args:
            url: Response URL
            text: Response body text
            encoding: Text encoding
            **kwargs: Additional response parameters (status, headers, etc.)
            
        Returns:
            Response: Response object
            
        Example:
            >>> response = Response.from_text('http://example.com', '<html>...</html>')
        """
        return cls(
            url=url,
            body=text.encode(encoding),
            **kwargs
        )
    
    @classmethod
    def from_json(cls, url: str, data: Dict[str, Any], **kwargs) -> 'Response':
        """
        Create a Response from JSON data.
        
        Args:
            url: Response URL
            data: JSON data dictionary
            **kwargs: Additional response parameters (status, headers, etc.)
            
        Returns:
            Response: Response object
            
        Example:
            >>> response = Response.from_json('http://api.example.com', {'key': 'value'})
        """
        import json
        return cls(
            url=url,
            body=json.dumps(data, ensure_ascii=False).encode('utf-8'),
            headers={'Content-Type': 'application/json', **(kwargs.pop('headers', {}))},
            **kwargs
        )

    # ==================== 编码检测相关方法 ====================
    
    def _determine_encoding(self) -> str:
        """
        智能检测响应编码
        
        编码检测优先级：
        1. Request 中指定的编码（最高优先级，用户显式指定）
        2. BOM 字节顺序标记
        3. HTTP Content-Type 头部
        4. HTML meta 标签声明
        5. 内容自动检测（基于字符频率分析）
        6. 默认编码 (utf-8)
        
        Returns:
            str: 检测到的编码
        """
        # 获取 Request 中声明的编码
        declared_encoding = None
        if self.request and getattr(self.request, 'encoding', None):
            declared_encoding = self.request.encoding
        
        # 使用 EncodingDetector 进行检测
        return EncodingDetector.detect(
            body=self.body,
            headers=self.headers,
            declared_encoding=declared_encoding,
        )

    @property
    def text(self) -> str:
        """
        将响应体(body)以正确的编码解码为字符串，并缓存结果。
        
        Returns:
            str: 解码后的文本
        """
        if self._text_cache is not None:
            return self._text_cache

        if not self.body:
            self._text_cache = ""
            return self._text_cache

        # 使用 EncodingDetector 解码
        self._text_cache = EncodingDetector.decode_body(
            body=self.body,
            encoding=self.encoding,
            headers=self.headers,
        )
        return self._text_cache

    # ==================== 状态检查相关属性 ====================
    
    @property
    def is_success(self) -> bool:
        """
        检查响应是否成功 (2xx)
        
        Returns:
            bool: 是否成功
        """
        return self._is_success

    @property
    def is_redirect(self) -> bool:
        """
        检查响应是否为重定向 (3xx)
        
        Returns:
            bool: 是否为重定向
        """
        return self._is_redirect

    @property
    def is_client_error(self) -> bool:
        """
        检查响应是否为客户端错误 (4xx)
        
        Returns:
            bool: 是否为客户端错误
        """
        return self._is_client_error

    @property
    def is_server_error(self) -> bool:
        """
        检查响应是否为服务器错误 (5xx)
        
        Returns:
            bool: 是否为服务器错误
        """
        return self._is_server_error

    # ==================== 响应头相关属性 ====================
    
    @property
    def content_type(self) -> str:
        """
        获取响应的 Content-Type
        
        Returns:
            str: Content-Type
        """
        return get_header_value(self.headers, 'content-type', '')

    @property
    def content_length(self) -> Optional[int]:
        """
        获取响应的 Content-Length
        
        Returns:
            Optional[int]: Content-Length
        """
        length = get_header_value(self.headers, 'content-length')
        return int(length) if length else None

    # ==================== JSON处理方法 ====================
    
    def json(self, default: Any = None) -> Any:
        """
        将响应文本解析为 JSON 对象。
        
        Args:
            default: 默认返回值，解析失败时返回
            
        Returns:
            Any: JSON对象
        """
        if self._json_cache is not None:
            return self._json_cache

        try:
            self._json_cache = json_module.loads(self.text)
            return self._json_cache
        except (json_module.JSONDecodeError, ValueError) as e:
            if default is not None:
                return default
            raise DecodeError(f"Failed to parse JSON from {self.url}: {e}")

    # ==================== URL处理方法 ====================
    
    def urljoin(self, url: str) -> str:
        """
        拼接 URL，自动处理相对路径。
        
        Args:
            url: 要拼接的URL
            
        Returns:
            str: 拼接后的URL
        """
        return _urljoin(self.url, url)

    # ==================== 选择器相关方法 ====================

    @property
    def _selector(self) -> Selector:
        """
        懒加载 Selector 实例
        
        Returns:
            Selector: Selector实例
        """
        if self._selector_instance is None:
            self._selector_instance = Selector(self.text)
        return self._selector_instance

    def xpath(self, query: str, adaptive: bool = False,
              identifier: str = '', percentage: float = 50.0,
              timeout: float = 5.0) -> SelectorList:
        """
        使用 XPath 选择器查询文档。

        Args:
            query: XPath查询表达式
            adaptive: 启用自适应追踪（命中时保存/更新指纹，失效时自动匹配）
            identifier: 指纹标识符（默认使用 query 字符串）
            percentage: 最低匹配百分比阈值（0-100）
            timeout: 查询超时时间（秒），默认 5 秒

        Returns:
            SelectorList: 查询结果
        """
        import threading
        
        result_holder = [None]
        exception_holder = [None]
        
        def _execute_xpath():
            try:
                result_holder[0] = self._selector.xpath(query)
            except Exception as e:
                exception_holder[0] = e
        
        # 执行 XPath 查询（带超时）
        thread = threading.Thread(target=_execute_xpath)
        thread.daemon = True
        thread.start()
        thread.join(timeout)
        
        # 检查超时
        if thread.is_alive():
            get_logger('Response').warning(
                f"XPath query timeout after {timeout}s: {query[:50]}..."
            )
            return SelectorList([])
        
        # 检查异常
        if exception_holder[0]:
            raise exception_holder[0]
        
        result = result_holder[0]

        # 自适应处理委托给 Mixin
        if adaptive:
            return self._handle_adaptive_result(result, query, adaptive, identifier, percentage)

        return result

    def css(self, query: str, adaptive: bool = False,
            identifier: str = '', percentage: float = 50.0,
            timeout: float = 5.0) -> SelectorList:
        """
        使用 CSS 选择器查询文档。

        Args:
            query: CSS选择器表达式
            adaptive: 启用自适应追踪（命中时保存/更新指纹，失效时自动匹配）
            identifier: 指纹标识符（默认使用 query 字符串）
            percentage: 最低匹配百分比阈值（0-100）
            timeout: 查询超时时间（秒），默认 5 秒

        Returns:
            SelectorList: 查询结果
        """
        # CSS 选择器转 XPath，复用 xpath 方法的自适应逻辑
        from parsel.csstranslator import HTMLTranslator
        try:
            xpath_query = HTMLTranslator().css_to_xpath(query)
        except Exception:
            xpath_query = query

        return self.xpath(
            xpath_query,
            adaptive=adaptive,
            identifier=identifier or query,
            percentage=percentage,
            timeout=timeout,
        )
    # 自适应选择器方法已提取到 ResponseAdaptiveMixin (response_adaptive.py)

    # ==================== 通用选择器方法 ====================

    def _is_xpath(self, query: str) -> bool:
        """
        判断查询语句是否为 XPath
        """
        return query.startswith(('/', '//', './'))

    def _get_elements(self, xpath_or_css: str) -> SelectorList:
        """
        根据选择器获取元素列表
        """
        if self._is_xpath(xpath_or_css):
            return self.xpath(xpath_or_css)
        return self.css(xpath_or_css)

    def _extract_text(self, elements: SelectorList, first_only: bool = False) -> Union[Optional[str], List[str]]:
        """
        从元素中提取文本
        
        Args:
            elements: 元素列表
            first_only: 是否只返回第一个元素的文本
            
        Returns:
            如果 first_only=True 返回 str 或 None
            否则返回 List[str]
        """
        result = []
        for element in elements:
            if hasattr(element, 'xpath'):
                texts = element.xpath('.//text()').getall()
                cleaned = ' '.join(t.strip() for t in texts if t.strip())
                if cleaned:
                    result.append(cleaned)
            else:
                text = str(element).strip()
                if text:
                    result.append(text)
        
        if first_only:
            return result[0] if result else None
        return result

    def get(self, xpath_or_css: str, default: Optional[str] = None, strict: bool = False) -> Optional[str]:
        """
        获取第一个匹配元素的文本。
        
        等同于 response.css(query).get() 或 response.xpath(query).get()
        
        Args:
            xpath_or_css: XPath 或 CSS 选择器
            default: 未找到时的默认值
            strict: 严格模式，True 时抛出异常而非返回 default
            
        Returns:
            str: 第一个元素的文本，未找到返回 default
            
        示例:
            title = response.get('title')
            content = response.get('.content', '')
        """
        try:
            elements = self._get_elements(xpath_or_css)
            result = self._extract_text(elements, first_only=True)
            return result if result is not None else default
        except Exception as e:
            if strict:
                raise
            get_logger('Response').debug(f"Selector failed: {e}")
            return default

    def getall(self, xpath_or_css: str, strict: bool = False) -> List[str]:
        """
        获取所有匹配元素的文本列表。
        
        等同于 response.css(query).getall() 或 response.xpath(query).getall()
        
        Args:
            xpath_or_css: XPath 或 CSS 选择器
            strict: 严格模式，True 时抛出异常而非返回空列表
            
        Returns:
            List[str]: 所有匹配元素的文本列表
            
        示例:
            items = response.getall('.item')
            links = response.getall('a::text')
        """
        try:
            elements = self._get_elements(xpath_or_css)
            return self._extract_text(elements, first_only=False)
        except Exception as e:
            if strict:
                raise
            get_logger('Response').debug(f"Selector failed: {e}")
            return []

    def attr(self, xpath_or_css: str, name: str, default: Optional[str] = None) -> Optional[str]:
        """
        获取第一个匹配元素的指定属性值。
        
        Args:
            xpath_or_css: XPath 或 CSS 选择器
            name: 属性名称
            default: 未找到时的默认值
            
        Returns:
            Optional[str]: 属性值，未找到返回 default
            
        示例:
            href = response.attr('a', 'href')
            src = response.attr('img', 'src', '')
        """
        try:
            elements = self._get_elements(xpath_or_css)
            if not elements:
                return default
            return elements[0].attrib.get(name, default)
        except Exception:
            return default

    def attrs(self, xpath_or_css: str, name: str) -> List[str]:
        """
        获取所有匹配元素的指定属性值列表。
        
        Args:
            xpath_or_css: XPath 或 CSS 选择器
            name: 属性名称
            
        Returns:
            List[str]: 属性值列表
            
        示例:
            hrefs = response.attrs('a', 'href')
            srcs = response.attrs('img', 'src')
        """
        try:
            elements = self._get_elements(xpath_or_css)
            return [e.attrib.get(name) for e in elements if e.attrib.get(name) is not None]
        except Exception:
            return []

    def get_outer(self, xpath_or_css: str, default: Optional[str] = None) -> Optional[str]:
        """
        获取第一个匹配元素的完整 HTML（包含标签）。
        
        Args:
            xpath_or_css: XPath 或 CSS 选择器
            default: 未找到时的默认值
            
        Returns:
            str: 第一个元素的完整 HTML，未找到返回 default
            
        示例:
            content_html = response.get_outer('.content')
            # '<div class="content">...</div>'
        """
        try:
            elements = self._get_elements(xpath_or_css)
            return elements.get() or default
        except Exception:
            return default

    def getall_outer(self, xpath_or_css: str) -> List[str]:
        """
        获取所有匹配元素的完整 HTML 列表（包含标签）。
        
        Args:
            xpath_or_css: XPath 或 CSS 选择器
            
        Returns:
            List[str]: 所有元素的完整 HTML 列表
            
        示例:
            items_html = response.getall_outer('.item')
            # ['<div class="item">item1</div>', '<div class="item">item2</div>']
        """
        try:
            elements = self._get_elements(xpath_or_css)
            return elements.getall()
        except Exception:
            return []

    # ==================== 正则表达式相关方法 ====================
    
    def re_findone(self, pattern: Union[str, Pattern], flags: int = re.DOTALL, default: Optional[str] = None) -> Optional[str]:
        """
        在响应文本上执行正则表达式查找，返回第一个匹配。
        
        Args:
            pattern: 正则表达式模式
            flags: 正则表达式标志
            default: 未匹配时的默认值
            
        Returns:
            Optional[str]: 第一个匹配结果，未匹配返回 default
            
        示例:
            price = response.re_findone(r'price: (\\d+)', default='0')
        """
        pattern_str = pattern if isinstance(pattern, str) else pattern.pattern
        return regex_findone(pattern_str, self.text, flags) or default

    def re_search(self, pattern: Union[str, Pattern], flags: int = re.DOTALL) -> Optional[Match]:
        """
        在响应文本上执行正则表达式搜索。
        
        Args:
            pattern: 正则表达式模式
            flags: 正则表达式标志
            
        Returns:
            Optional[Match]: 匹配结果
        """
        pattern_str = pattern if isinstance(pattern, str) else pattern.pattern
        return regex_search(pattern_str, self.text, flags)

    def re_findall(self, pattern: Union[str, Pattern], flags: int = re.DOTALL) -> List[Any]:
        """
        在响应文本上执行正则表达式查找。
        
        Args:
            pattern: 正则表达式模式
            flags: 正则表达式标志
            
        Returns:
            List[Any]: 所有匹配结果
        """
        pattern_str = pattern if isinstance(pattern, str) else pattern.pattern
        return regex_findall(pattern_str, self.text, flags)

    def re_css(self, xpath_or_css: str, pattern: Union[str, Pattern], flags: int = re.DOTALL) -> List[str]:
        """
        从匹配选择器的元素中提取文本，再用正则提取。
        
        Args:
            xpath_or_css: XPath 或 CSS 选择器
            pattern: 正则表达式模式
            flags: 正则表达式标志
            
        Returns:
            List[str]: 所有正则匹配结果
            
        示例:
            # 从所有商品名称中提取价格数字
            prices = response.re_css('.price', r'\\d+\\.\\d+')
        """
        texts = self.getall(xpath_or_css)
        pattern_str = pattern if isinstance(pattern, str) else pattern.pattern
        result = []
        for text in texts:
            matches = regex_findall(pattern_str, text, flags)
            result.extend(matches)
        return result

    # ==================== Cookie处理方法 ====================
    
    def get_cookies(self) -> Dict[str, str]:
        """
        从响应头中解析并返回Cookies。
        
        Returns:
            Dict[str, str]: Cookies字典
        """
        cookie_header = self.headers.get("Set-Cookie", "")
        return parse_cookies(cookie_header)

    # ==================== 请求相关方法 ====================
    
    def follow(self, url: str, callback=None, **kwargs):
        """
        创建一个跟随链接的请求。
        
        Args:
            url: 要跟随的URL（可以是相对URL）
            callback: 回调函数
            **kwargs: 传递给Request的其他参数
            
        Returns:
            Request: 新的请求对象
        """
        # 延迟导入Request以避免循环导入
        from crawlo.network.request import Request
        
        # 使用urljoin处理相对URL
        absolute_url = self.urljoin(url)
        
        # 创建新的请求
        return Request(
            url=absolute_url,
            callback=callback or getattr(self.request, 'callback', None),
            **kwargs
        )

    @property
    def meta(self) -> Dict:
        """
        获取关联的 Request 对象的 meta 字典。
        
        Returns:
            Dict: meta字典
        """
        return self.request.meta if self.request else {}

    def __str__(self) -> str:
        return f"<{self.status} {self.url}>"