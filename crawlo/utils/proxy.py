#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
# @Time    :    2025-08-23 19:21
# @Author  :   crawl-coder
# @Desc    :   None
"""
import httpx
from typing import List


PROXY_POOL_API = 'http://123.56.42.142:5000/proxy/getitem/'


async def get_proxies() -> List[str]:
    async with httpx.AsyncClient() as client:
        resp = await client.get(PROXY_POOL_API)
        data = resp.json()
        # 用户自己解析：适配各种格式
        return [data["proxy"]["http"]]
