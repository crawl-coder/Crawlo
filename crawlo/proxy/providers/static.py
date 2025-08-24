#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
# @Time    :    2025-08-24 12:14
# @Author  :   crawl-coder
# @Desc    :   None
"""
from typing import List
from .base import BaseProxyProvider


class StaticProxyProvider(BaseProxyProvider):
    """从静态列表加载代理"""

    def __init__(self, proxies: List[str]):
        self.proxies = [p.strip() for p in proxies if p.strip()]

    async def fetch_proxies(self) -> List[str]:
        return self.proxies
