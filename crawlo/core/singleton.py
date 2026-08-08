#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
单例模式工具
=============
提供同步单例元类 ``SingletonMeta`` 和装饰器 ``singleton``。
"""
import threading
from typing import Any, Dict, Type


class SingletonMeta(type):
    """单例元类

    与 @singleton 装饰器相比，使用元类实现单例有以下优势：
    1. 保留类的类型，isinstance() 检查正常工作
    2. 类型提示和 IDE 自动补全不受影响
    3. 类的 __name__, __doc__ 等属性保持不变
    """
    _instances: Dict[Type, Any] = {}
    _lock = threading.Lock()

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            with cls._lock:
                if cls not in cls._instances:
                    instance = super().__call__(*args, **kwargs)
                    cls._instances[cls] = instance
        return cls._instances[cls]

    @classmethod
    def _reset_instance(mcs, cls):
        """重置指定类的单例实例（仅用于测试）"""
        with mcs._lock:
            mcs._instances.pop(cls, None)


def singleton(cls):
    """单例装饰器"""
    instances = {}
    lock = threading.Lock()

    def get_instance(*args, **kwargs):
        if cls not in instances:
            with lock:
                if cls not in instances:
                    instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return get_instance


__all__ = ['SingletonMeta', 'singleton']
