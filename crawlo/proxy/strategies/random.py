#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
# @Time    :    2025-08-24 12:16
# @Author  :   crawl-coder
# @Desc    :   None
"""
import random
from typing import List, Dict

from .base import register_strategy


@register_strategy('random')
def random_strategy(proxies: List[Dict], request, stats) -> str:
    return random.choice(proxies)['url']