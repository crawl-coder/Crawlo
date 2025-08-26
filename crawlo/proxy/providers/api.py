#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
# @Time    :    2025-08-24 12:13
# @Author  :   crawl-coder
# @Desc    :   None
"""
import httpx
from typing import List
from .base import BaseProxyProvider


class APIProxyProvider(BaseProxyProvider):
    """
    从 HTTP API 获取代理
    示例返回: [{"ip": "x.x.x.x", "port": 8080}, ...]
    """
    def __init__(self, url: str, method='GET', auth=None, timeout: float = 10.0, path: str = ""):
        self.url = url
        self.method = method
        self.auth = auth
        self.timeout = timeout
        self.path = path  # JSON 路径，如 "data.proxies"

    async def fetch_proxies(self) -> List[str]:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.request(self.method, self.url, auth=self.auth)
                resp.raise_for_status()
                data = resp.json()
                proxies = data.get('proxy')
                return proxies
        except Exception as e:
            print(f"[APIProxyProvider] 请求失败 {self.url}: {e}")
            return []