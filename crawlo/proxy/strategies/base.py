#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
# @Time    :    2025-08-24 12:15
# @Author  :   crawl-coder
# @Desc    :   None
"""
from typing import List, Dict, Callable
from crawlo import Request

StrategyFunc = Callable[[List[Dict], Request, Dict[str, Dict]], str]


def register_strategy(name: str):
    """装饰器注册策略"""

    def wrapper(func: StrategyFunc):
        STRATEGIES[name] = func
        return func

    return wrapper


STRATEGIES: Dict[str, StrategyFunc] = {}
