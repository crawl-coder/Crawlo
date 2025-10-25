#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
单例模式工具模块
================

提供同步和异步两种单例实现方式，适用于不同的使用场景。

使用场景：
1. 同步单例：用于框架初始化、配置管理等同步代码
2. 异步单例：用于数据库连接池、网络资源等异步代码

示例：
    # 同步单例
    @singleton
    class CoreInitializer:
        pass
    
    # 异步单例（在连接池管理器中使用）
    class MySQLConnectionPoolManager:
        _instances: Dict[str, 'MySQLConnectionPoolManager'] = {}
        _lock = asyncio.Lock()
        
        @classmethod
        async def get_pool(cls, ...):
            async with cls._lock:
                if pool_key not in cls._instances:
                    cls._instances[pool_key] = cls(pool_key)
            return cls._instances[pool_key].pool
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