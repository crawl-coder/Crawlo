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
from http.cookies import SimpleCookie
from parsel import Selector, SelectorList
from typing import Dict, Any, List, Optional, Union
from urllib.parse import urljoin as _urljoin

from crawlo.exceptions import DecodeError


class Response:
    """
    HTTP响应的封装，提供数据解析的便捷方法。
    
    功能特性:
    - 智能编码检测和缓存
    - 懒加载 Selector 实例
    - JSON 解析和缓存
    - 多类型数据提取
    """

    def __init__(
            self,
            url: str,
            *,
            headers: Dict[str, Any] = None,
            body: bytes = b"",
            method: str = 'GET',
            request: 'Request' = None,  # 使用字符串注解避免循环导入
            status_code: int = 200,
    ):
        # 基本属性
        self.url = url
        self.headers = headers or {}
        self.body = body
        self.method = method.upper()
        self.request = request
        self.status_code = status_code

        # 编码处理
        self.encoding = self._determine_encoding()

        # 缓存属性
        self._text_cache = None
        self._json_cache = None
        self._selector_instance = None

        # 状态标记
        self._is_success = 200 <= status_code < 300
        self._is_redirect = 300 <= status_code < 400
        self._is_client_error = 400 <= status_code < 500
        self._is_server_error = status_code >= 500

    def _determine_encoding(self) -> Optional[str]:
        """智能检测响应编码"""
        # 1. 优先使用 request 的编码
        if self.request and self.request.encoding:
            return self.request.encoding

        # 2. 从 Content-Type 头中检测
        content_type = self.headers.get("content-type", "") or self.headers.get("Content-Type", "")
        if content_type:
            charset_match = re.search(r"charset=([w-]+)", content_type, re.I)
            if charset_match:
                return charset_match.group(1).lower()

        # 3. 从 HTML meta 标签中检测(仅对HTML内容)
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

        # 4. 默认使用 utf-8
        return 'utf-8'

    @property
    def text(self) -> str:
        """将响应体(body)以正确的编码解码为字符串，并缓存结果。"""
        if self._text_cache is not None:
            return self._text_cache

        if not self.body:
            self._text_cache = ""
            return self._text_cache

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

    @property
    def is_success(self) -> bool:
        """检查响应是否成功 (2xx)"""
        return self._is_success

    @property
    def is_redirect(self) -> bool:
        """检查响应是否为重定向 (3xx)"""
        return self._is_redirect

    @property
    def is_client_error(self) -> bool:
        """检查响应是否为客户端错误 (4xx)"""
        return self._is_client_error

    @property
    def is_server_error(self) -> bool:
        """检查响应是否为服务器错误 (5xx)"""
        return self._is_server_error

    @property
    def content_type(self) -> str:
        """获取响应的 Content-Type"""
        return self.headers.get('content-type', '') or self.headers.get('Content-Type', '')

    @property
    def content_length(self) -> Optional[int]:
        """获取响应的 Content-Length"""
        length = self.headers.get('content-length') or self.headers.get('Content-Length')
        return int(length) if length else None

    def json(self, default: Any = None) -> Any:
        """将响应文本解析为 JSON 对象。"""
        if self._json_cache is not None:
            return self._json_cache

        try:
            self._json_cache = ujson.loads(self.text)
            return self._json_cache
        except (ujson.JSONDecodeError, ValueError) as e:
            if default is not None:
                return default
            raise DecodeError(f"Failed to parse JSON from {self.url}: {e}")

    def urljoin(self, url: str) -> str:
        """拼接 URL，自动处理相对路径。"""
        return _urljoin(self.url, url)

    @property
    def _selector(self) -> Selector:
        """懒加载 Selector 实例"""
        if self._selector_instance is None:
            self._selector_instance = Selector(self.text)
        return self._selector_instance

    def xpath(self, query: str) -> SelectorList:
        """使用 XPath 选择器查询文档。"""
        return self._selector.xpath(query)

    def css(self, query: str) -> SelectorList:
        """使用 CSS 选择器查询文档。"""
        return self._selector.css(query)

    def _is_xpath(self, query: str) -> bool:
        """判断查询语句是否为XPath"""
        return query.startswith(('/', '//', './'))

    def _extract_text_from_elements(self, elements: SelectorList, join_str: str = " ") -> str:
        """
        从元素列表中提取文本并拼接
        
        :param elements: SelectorList元素列表
        :param join_str: 文本拼接分隔符
        :return: 拼接后的文本
        """
        texts = []
        for element in elements:
            # 获取元素的所有文本节点
            if hasattr(element, 'xpath'):
                element_texts = element.xpath('.//text()').getall()
            else:
                element_texts = [str(element)]
            # 清理并添加非空文本
            for text in element_texts:
                cleaned = text.strip()
                if cleaned:
                    texts.append(cleaned)
        return join_str.join(texts)

    def extract_text(self, xpath_or_css: str, join_str: str = " ", default: str = '') -> str:
        """
        提取单个元素的文本内容，支持CSS和XPath选择器

        参数:
            xpath_or_css: XPath或CSS选择器
            join_str: 文本拼接分隔符(默认为空格)
            default: 默认返回值，当未找到元素时返回

        返回:
            拼接后的纯文本字符串
        """
        try:
            elements = self.xpath(xpath_or_css) if self._is_xpath(xpath_or_css) else self.css(xpath_or_css)
            if not elements:
                return default
            return self._extract_text_from_elements(elements, join_str)
        except Exception:
            return default

    def extract_texts(self, xpath_or_css: str, join_str: str = " ", default: List[str] = None) -> List[str]:
        """
        提取多个元素的文本内容列表，支持CSS和XPath选择器

        参数:
            xpath_or_css: XPath或CSS选择器
            join_str: 单个节点内文本拼接分隔符
            default: 默认返回值，当未找到元素时返回

        返回:
            纯文本列表(每个元素对应一个节点的文本)
        """
        if default is None:
            default = []
            
        try:
            elements = self.xpath(xpath_or_css) if self._is_xpath(xpath_or_css) else self.css(xpath_or_css)
            if not elements:
                return default
                
            result = []
            for element in elements:
                # 对每个元素提取文本
                if hasattr(element, 'xpath'):
                    texts = element.xpath('.//text()').getall()
                else:
                    texts = [str(element)]
                    
                # 清理文本并拼接
                clean_texts = [text.strip() for text in texts if text.strip()]
                if clean_texts:
                    result.append(join_str.join(clean_texts))
                    
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
        """
        try:
            elements = self.xpath(xpath_or_css) if self._is_xpath(xpath_or_css) else self.css(xpath_or_css)
            if not elements:
                return default
            return elements.attrib.get(attr_name, default)
        except Exception:
            return default

    def extract_attrs(self, xpath_or_css: str, attr_name: str, default: List[Any] = None) -> List[Any]:
        """
        提取多个元素的属性值列表，支持CSS和XPath选择器

        参数:
            xpath_or_css: XPath或CSS选择器
            attr_name: 属性名称
            default: 默认返回值

        返回:
            属性值列表
        """
        if default is None:
            default = []
            
        try:
            elements = self.xpath(xpath_or_css) if self._is_xpath(xpath_or_css) else self.css(xpath_or_css)
            if not elements:
                return default
                
            result = []
            for element in elements:
                if hasattr(element, 'attrib'):
                    attr_value = element.attrib.get(attr_name)
                    if attr_value is not None:
                        result.append(attr_value)
                        
            return result if result else default
        except Exception:
            return default

    def re_search(self, pattern: str, flags: int = re.DOTALL) -> Optional[re.Match]:
        """在响应文本上执行正则表达式搜索。"""
        if not isinstance(pattern, str):
            raise TypeError("Pattern must be a string")
        return re.search(pattern, self.text, flags=flags)

    def re_findall(self, pattern: str, flags: int = re.DOTALL) -> List[Any]:
        """在响应文本上执行正则表达式查找。"""
        if not isinstance(pattern, str):
            raise TypeError("Pattern must be a string")
        return re.findall(pattern, self.text, flags=flags)

    def get_cookies(self) -> Dict[str, str]:
        """从响应头中解析并返回Cookies。"""
        cookie_header = self.headers.get("Set-Cookie", "")
        if isinstance(cookie_header, list):
            cookie_header = ", ".join(cookie_header)
        cookies = SimpleCookie()
        cookies.load(cookie_header)
        return {key: morsel.value for key, morsel in cookies.items()}

    @property
    def meta(self) -> Dict:
        """获取关联的 Request 对象的 meta 字典。"""
        return self.request.meta if self.request else {}

    def __str__(self):
        return f"<{self.status_code} {self.url}>"