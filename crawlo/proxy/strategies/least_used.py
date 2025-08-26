#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
# @Time    :    2025-08-24 12:17
# @Author  :   crawl-coder
# @Desc    :   None
"""
from typing import List, Dict

from .base import register_strategy


@register_strategy('least_used')
def least_used_strategy(proxies: List[Dict], request, stats) -> str:
    proxies.sort(key=lambda p: stats.get(p['url'], {}).get('total', 0))
    return proxies[0]['url']