#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
# @Time    :    2025-08-24 12:10
# @Author  :   crawl-coder
# @Desc    :   None
"""
from .base import STRATEGIES, StrategyFunc, register_strategy

from . import random
from . import round_robin
from . import least_used
from . import domain_rule

__all__ = ['STRATEGIES', 'StrategyFunc', 'register_strategy']