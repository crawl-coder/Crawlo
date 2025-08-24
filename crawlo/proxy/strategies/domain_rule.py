#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
# @Time    :    2025-08-24 12:17
# @Author  :   crawl-coder
# @Desc    :   None
"""
from typing import List, Dict

from .base import register_strategy
from .least_used import least_used_strategy


@register_strategy('domain_rule')
def domain_rule_strategy(proxies: List[Dict], request, stats, rules: dict = None) -> str:
    rules = rules or {}
    for domain, proxy_url in rules.items():
        if domain in request.url:
            return proxy_url
    return least_used_strategy(proxies, request, stats)

