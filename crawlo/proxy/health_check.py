#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
# @Time    :    2025-08-24 12:10
# @Author  :   crawl-coder
# @Desc    :   None
"""
import time
import httpx
from typing import Dict


async def check_single_proxy(proxy_info: Dict, test_url: str = "https://httpbin.org/ip"):
    """单个代理健康检查"""
    try:
        async with httpx.AsyncClient(proxies=proxy_info['url'], timeout=10.0) as client:
            resp = await client.get(test_url)
            if 200 <= resp.status_code < 300:
                proxy_info['healthy'] = True
                proxy_info['failures'] = 0
                proxy_info['unhealthy_since'] = 0
            else:
                raise Exception(f"HTTP {resp.status_code}")
    except Exception:
        proxy_info['healthy'] = False
        proxy_info['unhealthy_since'] = proxy_info.get('unhealthy_since') or time.time()
        proxy_info['failures'] = proxy_info.get('failures', 0) + 1
    finally:
        proxy_info['last_health_check'] = time.time()
