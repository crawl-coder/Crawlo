#!/usr/bin/python
# -*- coding:UTF-8 -*-
import hashlib
from copy import deepcopy
from w3lib.url import safe_url_string
from typing import Dict, Optional, Callable, Union

from crawlo.utils.url import escape_ajax


class Request(object):

    def __init__(
            self,
            url: str,
            *,
            callback: Optional[Callable] = None,
            headers: Optional[Dict[str, str]] = None,
            body: Optional[bytes] = None,
            method: Optional[str] = 'GET',
            cookies: Optional[Dict[str, str]] = None,
            priority: int = 0,
            encoding: Optional[str] = 'UTF-8',
            meta: Optional[Dict[str, str]] = None

    ):
        self.url = url
        self.callback = callback
        self.headers = headers if headers else {}
        self.body = body
        self.method = str(method).upper()
        self.cookies = cookies
        self.priority = priority
        self.encoding = encoding
        self._meta = meta if meta is not None else {}

    def copy(self):
        return deepcopy(self)

    def fingerprint(self) -> str:
        data = f"{self.url}{self.method}{self.body or b''}".encode()
        return hashlib.sha256(data).hexdigest()

    def set_meta(self, key: str, value: str):
        self._meta[key] = value

    def _set_url(self, url: str) -> None:
        if not isinstance(url, str):
            raise TypeError(f"Request url must be str, got {type(url).__name__}")

        s = safe_url_string(url, self.encoding)
        self._url = escape_ajax(s)

        if (
            "://" not in self._url
            and not self._url.startswith("about:")
            and not self._url.startswith("data:")
        ):
            raise ValueError(f"Missing scheme in request url: {self._url}")

    @property
    def meta(self):
        return self._meta

    def __str__(self):
        return f'<Request url={self.url}> method={self.method}>'

    def __lt__(self, other):
        return self.priority < other.priority
