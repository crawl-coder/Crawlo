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
import ujson
from typing import Dict, Any, List, Optional, Union, Pattern, Match, TYPE_CHECKING
from urllib.parse import urljoin as _urljoin
from parsel import Selector, SelectorList

if TYPE_CHECKING:
    from crawlo.network.request import Request

# 尝试导入 w3lib 编码检测函数
try:
    from w3lib.encoding import (
        html_body_declared_encoding,
        html_to_unicode,
        http_content_type_encoding,
        read_bom,
        resolve_encoding,
    )
    W3LIB_AVAILABLE = True
except ImportError:
    W3LIB_AVAILABLE = False
    # 当 w3lib 不可用时，从 utils 导入替代函数
    from crawlo.utils import (
        html_body_declared_encoding,
        html_to_unicode,
        http_content_type_encoding,
        read_bom,
        resolve_encoding,
    )

from crawlo.exceptions import DecodeError
from crawlo.utils import (
    extract_text,
    extract_texts,
    extract_attr,
    extract_attrs,
    is_xpath,
    parse_cookies,
    regex_search,
    regex_findall,
    get_header_value
)


def memoize_method_noargs(func):
    """
    装饰器，用于缓存无参数方法的结果
    
    Args:
        func: 要装饰的函数
        
    Returns:
        function: 装饰后的函数
    """
    cache_attr = f'_cache_{func.__name__}'
    
    def wrapper(self):
        if not hasattr(self, cache_attr):
            setattr(self, cache_attr, func(self))
        return getattr(self, cache_attr)
    
    return wrapper


class Response:
    """
    HTTP响应的封装，提供数据解析的便捷方法。
    
    功能特性:
    - 智能编码检测和缓存
    - 懒加载 Selector 实例
    - JSON 解析和缓存
    - 多类型数据提取
    """

    # 默认编码
    _DEFAULT_ENCODING = "ascii"

    def __init__(
            self,
            url: str,
            *,
            headers: Optional[Dict[str, Any]] = None,
            body: bytes = b"",
            method: str = 'GET',
            request: Optional['Request'] = None,  # 使用字符串注解避免循环导入
            status_code: int = 200,
    ) -> None:
        """
        初始化响应对象
        
        Args:
            url: 响应URL
            headers: 响应头
            body: 响应体
            method: 请求方法
            request: 对应的请求对象
            status_code: 状态码
        """
        # 基本属性
        self.url: str = url
        self.headers: Dict[str, Any] = headers or {}
        self.body: bytes = body
        self.method: str = method.upper()
        self.request: Optional['Request'] = request
        self.status_code: int = status_code

        # 编码处理
        self.encoding: str = self._determine_encoding()

        # 缓存属性
        self._text_cache: Optional[str] = None
        self._json_cache: Optional[Any] = None
        self._selector_instance: Optional[Selector] = None

        # 状态标记
        self._is_success: bool = 200 <= status_code < 300
        self._is_redirect: bool = 300 <= status_code < 400
        self._is_client_error: bool = 400 <= status_code < 500
        self._is_server_error: bool = status_code >= 500

    # ==================== 编码检测相关方法 ====================
    
    def _determine_encoding(self) -> str:
        """
        智能检测响应编码
        
        编码检测优先级：
        1. Request 中指定的编码
        2. BOM 字节顺序标记
        3. HTTP Content-Type 头部
        4. HTML meta 标签声明
        5. 内容自动检测
        6. 默认编码 (utf-8)
        
        Returns:
            str: 检测到的编码
        """
        # 1. 优先使用声明的编码
        declared_encoding = self._declared_encoding()
        if declared_encoding:
            return declared_encoding
            
        # 2. 使用 w3lib 进行编码检测（如果可用）
        if W3LIB_AVAILABLE:
            return self._body_inferred_encoding()
        else:
            # 如果 w3lib 不可用，使用原有的检测逻辑
            # 从 Content-Type 头中检测
            content_type = self.headers.get("content-type", "") or self.headers.get("Content-Type", "")
            if content_type:
                charset_match = re.search(r"charset=([\w-]+)", content_type, re.I)
                if charset_match:
                    return charset_match.group(1).lower()

            # 从 HTML meta 标签中检测(仅对HTML内容)
            if b'<html' in self.body[:1024].lower():
                # 查找 <meta charset="xxx"> 或 <meta http-equiv="Content-Type" content="...charset=xxx">
                html_start = self.body[:4096]  # 只检查前4KB
                try:
                    html_text = html_start.decode('ascii', errors='ignore')
                    # <meta charset="utf-8">
                    charset_match = re.search(r'<meta[^>]+charset=["\']?([\w-]+)', html_text, re.I)
                    if charset_match:
                        return charset_match.group(1).lower()

                    # <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
                    content_match = re.search(r'<meta[^>]+content=["\'][^"\'>]*charset=([\w-]+)', html_text, re.I)
                    if content_match:
                        return content_match.group(1).lower()
                except Exception:
                    pass

        # 3. 默认使用 utf-8
        return 'utf-8'

    def _declared_encoding(self) -> Optional[str]:
        """
        获取声明的编码
        优先级：Request编码 > BOM > HTTP头部 > HTML meta标签
        
        Returns:
            Optional[str]: 声明的编码
        """
        # 1. Request 中指定的编码
        if self.request and getattr(self.request, 'encoding', None):
            return self.request.encoding
            
        # 2. BOM 字节顺序标记
        bom_encoding = self._bom_encoding()
        if bom_encoding:
            return bom_encoding
            
        # 3. HTTP Content-Type 头部
        headers_encoding = self._headers_encoding()
        if headers_encoding:
            return headers_encoding
            
        # 4. HTML meta 标签声明编码
        body_declared_encoding = self._body_declared_encoding()
        if body_declared_encoding:
            return body_declared_encoding
            
        return None

    @memoize_method_noargs
    def _bom_encoding(self) -> Optional[str]:
        """
        BOM 字节顺序标记编码检测
        
        Returns:
            Optional[str]: BOM编码
        """
        if not W3LIB_AVAILABLE:
            # 使用替代函数
            encoding, _ = read_bom(self.body)
            return encoding
        return read_bom(self.body)[0]

    @memoize_method_noargs
    def _headers_encoding(self) -> Optional[str]:
        """
        HTTP Content-Type 头部编码检测
        
        Returns:
            Optional[str]: 头部编码
        """
        if not W3LIB_AVAILABLE:
            # 使用替代函数
            content_type = self.headers.get("content-type", "") or self.headers.get("Content-Type", "")
            return http_content_type_encoding(content_type)
        content_type = self.headers.get("Content-Type", b"") or self.headers.get("content-type", b"")
        if isinstance(content_type, bytes):
            content_type = content_type.decode('latin-1')
        return http_content_type_encoding(content_type)

    @memoize_method_noargs
    def _body_declared_encoding(self) -> Optional[str]:
        """
        HTML meta 标签声明编码检测
        
        Returns:
            Optional[str]: HTML声明编码
        """
        if not W3LIB_AVAILABLE:
            # 使用替代函数
            return html_body_declared_encoding(self.body)
        return html_body_declared_encoding(self.body)

    @memoize_method_noargs
    def _body_inferred_encoding(self) -> str:
        """
        内容自动检测编码
        
        Returns:
            str: 推断的编码
        """
        if not W3LIB_AVAILABLE:
            # 使用替代函数
            content_type = self.headers.get("content-type", "") or self.headers.get("Content-Type", "")
            # 使用 html_to_unicode 函数进行编码检测
            encoding, _ = html_to_unicode(
                content_type,
                self.body,
                auto_detect_fun=self._auto_detect_fun,
                default_encoding=self._DEFAULT_ENCODING,
            )
            return encoding

        content_type = self.headers.get("Content-Type", b"") or self.headers.get("content-type", b"")
        if isinstance(content_type, bytes):
            content_type = content_type.decode('latin-1')
        
        # 使用 w3lib 的 html_to_unicode 函数进行编码检测
        benc, _ = html_to_unicode(
            content_type,
            self.body,
            auto_detect_fun=self._auto_detect_fun,
            default_encoding=self._DEFAULT_ENCODING,
        )
        return benc

    def _auto_detect_fun(self, text: bytes) -> Optional[str]:
        """
        自动检测编码的回调函数
        
        Args:
            text: 要检测的字节文本
            
        Returns:
            Optional[str]: 检测到的编码
        """
        if not W3LIB_AVAILABLE:
            # 使用替代函数
            for enc in (self._DEFAULT_ENCODING, "utf-8", "cp1252"):
                try:
                    text.decode(enc)
                except UnicodeError:
                    continue
                return resolve_encoding(enc)
            return None
        for enc in (self._DEFAULT_ENCODING, "utf-8", "cp1252"):
            try:
                text.decode(enc)
            except UnicodeError:
                continue
            return resolve_encoding(enc)
        return None

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

        # 如果可用，使用 w3lib 进行更准确的解码
        if W3LIB_AVAILABLE:
            try:
                content_type = self.headers.get("Content-Type", b"") or self.headers.get("content-type", b"")
                if isinstance(content_type, bytes):
                    content_type = content_type.decode('latin-1')
                
                # 使用 w3lib 的 html_to_unicode 函数
                _, self._text_cache = html_to_unicode(
                    content_type,
                    self.body,
                    default_encoding=self.encoding
                )
                return self._text_cache
            except Exception:
                # 如果 w3lib 解码失败，回退到原有方法
                pass
        else:
            # 使用替代函数
            try:
                content_type = self.headers.get("content-type", "") or self.headers.get("Content-Type", "")
                # 使用 html_to_unicode 函数
                _, self._text_cache = html_to_unicode(
                    content_type,
                    self.body,
                    default_encoding=self.encoding
                )
                return self._text_cache
            except Exception:
                # 如果解码失败，回退到原有方法
                pass

        # 尝试多种编码
        encodings_to_try = [self.encoding]
        if self.encoding != 'utf-8':
            encodings_to_try.append('utf-8')
        if 'gbk' not in encodings_to_try:
            encodings_to_try.append('gbk')
        if 'gb2312' not in encodings_to_try:
            encodings_to_try.append('gb2312')
        encodings_to_try.append('latin1')  # 最后的回退选项

        for encoding in encodings_to_try:
            if not encoding:
                continue
            try:
                self._text_cache = self.body.decode(encoding)
                return self._text_cache
            except (UnicodeDecodeError, LookupError):
                continue

        # 所有编码都失败，使用容错解码
        try:
            self._text_cache = self.body.decode('utf-8', errors='replace')
            return self._text_cache
        except Exception as e:
            raise DecodeError(f"Failed to decode response from {self.url}: {e}")

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
            self._json_cache = ujson.loads(self.text)
            return self._json_cache
        except (ujson.JSONDecodeError, ValueError) as e:
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

    def xpath(self, query: str) -> SelectorList:
        """
        使用 XPath 选择器查询文档。
        
        Args:
            query: XPath查询表达式
            
        Returns:
            SelectorList: 查询结果
        """
        return self._selector.xpath(query)

    def css(self, query: str) -> SelectorList:
        """
        使用 CSS 选择器查询文档。
        
        Args:
            query: CSS选择器表达式
            
        Returns:
            SelectorList: 查询结果
        """
        return self._selector.css(query)

    def _is_xpath(self, query: str) -> bool:
        """
        判断查询语句是否为XPath
        
        Args:
            query: 查询表达式
            
        Returns:
            bool: 是否为XPath
        """
        return is_xpath(query)

    def _extract_text(self, elements: SelectorList, join_str: str = " ") -> str:
        """
        从元素列表中提取文本并拼接
        
        Args:
            elements: SelectorList元素列表
            join_str: 文本拼接分隔符
            
        Returns:
            str: 拼接后的文本
        """
        return extract_text(elements, join_str)

    def extract_text(self, xpath_or_css: str, join_str: str = " ", default: str = '') -> str:
        """
        提取单个元素的文本内容，支持CSS和XPath选择器

        参数:
            xpath_or_css: XPath或CSS选择器
            join_str: 文本拼接分隔符(默认为空格)
            default: 默认返回值，当未找到元素时返回

        返回:
            拼接后的纯文本字符串
            
        示例:
            # 使用CSS选择器
            title = response.extract_text('title')
            content = response.extract_text('.content p', join_str=' ')
            
            # 使用XPath选择器
            title = response.extract_text('//title')
            content = response.extract_text('//div[@class="content"]//p', join_str=' ')
            
        Args:
            xpath_or_css: XPath或CSS选择器
            join_str: 文本拼接分隔符
            default: 默认返回值
            
        Returns:
            str: 提取的文本
        """
        try:
            elements = self.xpath(xpath_or_css) if self._is_xpath(xpath_or_css) else self.css(xpath_or_css)
            if not elements:
                return default
            return self._extract_text(elements, join_str)
        except Exception:
            return default

    def extract_texts(self, xpath_or_css: str, join_str: str = " ", default: Optional[List[str]] = None) -> List[str]:
        """
        提取多个元素的文本内容列表，支持CSS和XPath选择器

        参数:
            xpath_or_css: XPath或CSS选择器
            join_str: 单个节点内文本拼接分隔符
            default: 默认返回值，当未找到元素时返回

        返回:
            纯文本列表(每个元素对应一个节点的文本)
            
        示例:
            # 使用CSS选择器
            paragraphs = response.extract_texts('.content p')
            titles = response.extract_texts('h1, h2, h3')
            
            # 使用XPath选择器
            paragraphs = response.extract_texts('//div[@class="content"]//p')
            titles = response.extract_texts('//h1 | //h2 | //h3')
            
        Args:
            xpath_or_css: XPath或CSS选择器
            join_str: 单个节点内文本拼接分隔符
            default: 默认返回值
            
        Returns:
            List[str]: 提取的文本列表
        """
        if default is None:
            default = []
            
        try:
            elements = self.xpath(xpath_or_css) if self._is_xpath(xpath_or_css) else self.css(xpath_or_css)
            if not elements:
                return default
                
            result = extract_texts(elements, join_str)
            return result if result else default
        except Exception:
            return default

    def extract_attr(self, xpath_or_css: str, attr_name: str, default: Any = None) -> Any:
        """
        提取单个元素的属性值，支持CSS和XPath选择器

        参数:
            xpath_or_css: XPath或CSS选择器
            attr_name: 属性名称
            default: 默认返回值

        返回:
            属性值或默认值
            
        示例:
            # 使用CSS选择器
            link_href = response.extract_attr('a', 'href')
            img_src = response.extract_attr('.image', 'src')
            
            # 使用XPath选择器
            link_href = response.extract_attr('//a[@class="link"]', 'href')
            img_src = response.extract_attr('//img[@alt="example"]', 'src')
            
        Args:
            xpath_or_css: XPath或CSS选择器
            attr_name: 属性名称
            default: 默认返回值
            
        Returns:
            Any: 提取的属性值
        """
        try:
            elements = self.xpath(xpath_or_css) if self._is_xpath(xpath_or_css) else self.css(xpath_or_css)
            if not elements:
                return default
            return extract_attr(elements, attr_name, default)
        except Exception:
            return default

    def extract_attrs(self, xpath_or_css: str, attr_name: str, default: Optional[List[Any]] = None) -> List[Any]:
        """
        提取多个元素的属性值列表，支持CSS和XPath选择器

        参数:
            xpath_or_css: XPath或CSS选择器
            attr_name: 属性名称
            default: 默认返回值

        返回:
            属性值列表
            
        示例:
            # 使用CSS选择器
            links = response.extract_attrs('a', 'href')
            images = response.extract_attrs('img', 'src')
            
            # 使用XPath选择器
            links = response.extract_attrs('//a[@class="link"]', 'href')
            images = response.extract_attrs('//img[@alt]', 'src')
            
        Args:
            xpath_or_css: XPath或CSS选择器
            attr_name: 属性名称
            default: 默认返回值
            
        Returns:
            List[Any]: 提取的属性值列表
        """
        if default is None:
            default = []
            
        try:
            elements = self.xpath(xpath_or_css) if self._is_xpath(xpath_or_css) else self.css(xpath_or_css)
            if not elements:
                return default
                
            result = extract_attrs(elements, attr_name)
            return result if result else default
        except Exception:
            return default

    # ==================== 正则表达式相关方法 ====================
    
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
        return f"<{self.status_code} {self.url}>"