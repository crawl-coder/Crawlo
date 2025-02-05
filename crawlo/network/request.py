#!/usr/bin/python
# -*- coding:UTF-8 -*-
from typing import Dict, Optional, Callable


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
        self.headers = headers
        self.body = body
        self.method = method
        self.cookies = cookies
        self.priority = priority
        self.encoding = encoding
        self._meta = meta if meta is not None else {}

    @property
    def meta(self):
        return self._meta

    def __str__(self):
        return f'<Request url={self.url}> method={self.method}>'

    def __lt__(self, other):
        return self.priority < other.priority
