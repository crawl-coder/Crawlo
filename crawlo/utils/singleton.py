#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
单例装饰器 - 提供统一的单例实现
"""

import threading
from typing import Any, Dict, Type


class SingletonMeta(type):
    """单例元类"""
    _instances: Dict[Type, Any] = {}
    _lock = threading.Lock()

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            with cls._lock:
                if cls not in cls._instances:
                    instance = super().__call__(*args, **kwargs)
                    cls._instances[cls] = instance
        return cls._instances[cls]


def singleton(cls):
    """
    单例装饰器
    
    Args:
        cls: 要装饰的类
        
    Returns:
        装饰后的类，确保只有一个实例
    """
    instances = {}
    lock = threading.Lock()

    def get_instance(*args, **kwargs):
        if cls not in instances:
            with lock:
                if cls not in instances:
                    instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return get_instance