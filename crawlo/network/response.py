#!/usr/bin/python
# -*- coding:UTF-8 -*-
import re
import ujson
from http.cookies import SimpleCookie
from parsel import Selector, SelectorList
from typing import Dict, Any, List, Optional
from urllib.parse import urljoin as _urljoin

from crawlo import Request
from crawlo.exceptions import DecodeError


class Response:
    """
    HTTP响应的封装，提供数据解析的便捷方法。
    """

    def __init__(
        self,
        url: str,
        *,
        headers: Dict[str, Any],
        body: bytes = b"",
        method: str = 'GET',
        request: Request = None,
        status_code: int = 200,
    ):
        self.url = url
        self.headers = headers
        self.body = body
        self.method = method
        self.request = request
        self.status_code = status_code
        self.encoding = self.request.encoding if self.request else None
        self._text_cache = None
        self._json_cache = None
        self._selector_instance = None  # 修改变量名，避免与 @property 冲突

    @property
    def text(self) -> str:
        """将响应体(body)以正确的编码解码为字符串，并缓存结果。"""
        if self._text_cache is not None:
            return self._text_cache

        encoding = self.encoding
        try:
            # 优先使用 request 提供的编码
            if encoding:
                self._text_cache = self.body.decode(encoding)
                return self._text_cache

            # 从 Content-Type 中提取编码
            content_type = self.headers.get("Content-Type", "")
            charset_match = re.search(r"charset=([\w-]+)", content_type, re.I)
            if charset_match:
                encoding = charset_match.group(1)
                self._text_cache = self.body.decode(encoding)
                return self._text_cache

            # 默认尝试 UTF-8
            self._text_cache = self.body.decode("utf-8")
            return self._text_cache

        except UnicodeDecodeError as e:
            raise DecodeError(f"Failed to decode response from {self.url}: {e}")

    def json(self) -> Any:
        """将响应文本解析为 JSON 对象。"""
        if self._json_cache:
            return self._json_cache
        self._json_cache = ujson.loads(self.text)
        return self._json_cache

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

    def xpath_text(self, query: str) -> str:
        """使用 XPath 提取并返回纯文本。"""
        fragments = self.xpath(f"{query}//text()").getall()
        return " ".join(text.strip() for text in fragments if text.strip())

    def css_text(self, query: str) -> str:
        """使用 CSS 选择器提取并返回纯文本。"""
        fragments = self.css(f"{query} ::text").getall()
        return " ".join(text.strip() for text in fragments if text.strip())

    def get_text(self, xpath_or_css: str, join_str: str = " ") -> str:
        """
        获取指定节点的纯文本(自动拼接子节点文本)

        参数:
            xpath_or_css: XPath或CSS选择器
            join_str: 文本拼接分隔符(默认为空格)

        返回:
            拼接后的纯文本字符串
        """
        elements = self.xpath(xpath_or_css) if xpath_or_css.startswith(('/', '//', './')) else self.css(xpath_or_css)
        texts = elements.xpath('.//text()').getall()
        return join_str.join(text.strip() for text in texts if text.strip())

    def get_all_text(self, xpath_or_css: str, join_str: str = " ") -> List[str]:
        """
        获取多个节点的纯文本列表

        参数:
            xpath_or_css: XPath或CSS选择器
            join_str: 单个节点内文本拼接分隔符

        返回:
            纯文本列表(每个元素对应一个节点的文本)
        """
        elements = self.xpath(xpath_or_css) if xpath_or_css.startswith(('/', '//', './')) else self.css(xpath_or_css)
        result = []
        for element in elements:
            texts = element.xpath('.//text()').getall()
            clean_text = join_str.join(text.strip() for text in texts if text.strip())
            if clean_text:
                result.append(clean_text)
        return result

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
