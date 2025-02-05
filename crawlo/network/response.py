#!/usr/bin/python
# -*- coding:UTF-8 -*-
import re
import ujson
from typing import Dict
from urllib.parse import urljoin as _urljoin
from parsel import Selector

from crawlo import Request
from crawlo.exceptions import DecodeError


class Response(object):

    def __init__(
            self,
            url: str,
            *,
            headers: Dict,
            body: bytes = b'',
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
        self.encoding = request.encoding
        self._selector = None
        self._text_cache = None

    @property
    def text(self):
        # 请求缓存
        if self._text_cache:
            return self._text_cache
        try:
            self._text_cache = self.body.decode(self.encoding)
        except UnicodeDecodeError:
            try:
                _encoding_re = re.compile(r"charset=([\w-]+)", flags=re.I)
                _encoding_string = self.headers.get('Content-Type', '') or self.headers.get('content-type', '')
                _encoding = _encoding_re.search(_encoding_string)
                if _encoding:
                    _encoding = _encoding.group(1)
                    self._text_cache = self.body.decode(_encoding)
                else:
                    raise DecodeError(f"{self.request} {self.request.encoding} error.")
            except UnicodeDecodeError as exp:
                raise UnicodeDecodeError(
                    exp.encoding, exp.object, exp.start, exp.end, f"{self.request} error."
                )
        return self._text_cache

    def json(self):
        return ujson.loads(self.text)

    def urljoin(self, url):
        return _urljoin(self.url, url)

    def xpath(self, xpath_str):
        if self._selector is None:
            self._selector = Selector(self.text)
        return self._selector.xpath(xpath_str)

    @property
    def meta(self):
        return self.request.meta

    def __str__(self):
        return f"{self.url} {self.status_code} {self.request.encoding} "
