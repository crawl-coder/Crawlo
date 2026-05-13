#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
通用装饰器模块

提供框架层复用的 decorator 工具。
"""


def memoize_method_noargs(func):
    """
    装饰器，用于缓存无参数方法的结果
    
    Args:
        func: 要装饰的函数
        
    Returns:
        function: 装饰后的函数
    """
    cache_attr = f'_cache_{func.__name__}'
    
    def wrapper(self):
        if not hasattr(self, cache_attr):
            setattr(self, cache_attr, func(self))
        return getattr(self, cache_attr)
    
    return wrapper
