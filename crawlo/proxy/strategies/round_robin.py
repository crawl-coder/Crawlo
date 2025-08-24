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


@register_strategy('round_robin')
def round_robin_strategy(proxies: List[Dict], request, stats) -> str:
    # 简化版：随机（真实轮询需记录上次索引）
    return random.choice(proxies)['url']