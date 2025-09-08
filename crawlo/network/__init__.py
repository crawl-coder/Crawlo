#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
Crawlo Network Module
====================
提供HTTP请求和响应对象的封装。

主要组件:
- Request: HTTP请求封装
- Response: HTTP响应封装
- RequestPriority: 请求优先级常量
"""

from .request import Request, RequestPriority
from .response import Response

__all__ = [
    'Request',
    'RequestPriority', 
    'Response',
]
