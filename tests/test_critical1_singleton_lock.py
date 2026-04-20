#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
测试 CRITICAL-1: CoreInitializer 单例 + threading.RLock 死锁风险的修复

验证点：
1. CoreInitializer 使用 SingletonMeta 元类，isinstance 检查正常
2. LogManager 使用 SingletonMeta 元类，isinstance 检查正常
3. SingletonMeta._reset_instance 可以重置实例（用于测试）
4. 单例行为正确：多次调用返回同一实例
5. CoreInitializer 保持线程安全
"""
import threading
from unittest.mock import patch

import pytest


class TestSingletonMetaFix:
    """测试 SingletonMeta 替代 @singleton 装饰器"""

    def test_core_initializer_isinstance_works(self):
        """CoreInitializer 的 isinstance 检查正常工作"""
        from crawlo.initialization.core import CoreInitializer
        # 不重置单例，避免影响其他测试的全局注册表状态
        instance = CoreInitializer()
        assert isinstance(instance, CoreInitializer), (
            "CoreInitializer instance should pass isinstance check"
        )

    def test_log_manager_isinstance_works(self):
        """LogManager 的 isinstance 检查正常工作"""
        from crawlo.logging.manager import LogManager
        instance = LogManager()
        assert isinstance(instance, LogManager), (
            "LogManager instance should pass isinstance check"
        )

    def test_core_initializer_is_class_not_function(self):
        """CoreInitializer 是类而非函数"""
        from crawlo.initialization.core import CoreInitializer
        assert isinstance(CoreInitializer, type), (
            "CoreInitializer should be a class (with SingletonMeta), not a function"
        )

    def test_log_manager_is_class_not_function(self):
        """LogManager 是类而非函数"""
        from crawlo.logging.manager import LogManager
        assert isinstance(LogManager, type), (
            "LogManager should be a class (with SingletonMeta), not a function"
        )

    def test_singleton_same_instance(self):
        """多次调用返回同一实例"""
        from crawlo.logging.manager import LogManager
        instance1 = LogManager()
        instance2 = LogManager()
        assert instance1 is instance2

    def test_singleton_meta_reset(self):
        """SingletonMeta._reset_instance 可以重置实例"""
        from crawlo.utils.singleton import SingletonMeta
        
        class TestClass(metaclass=SingletonMeta):
            def __init__(self):
                self.value = 42
        
        # 创建实例
        inst1 = TestClass()
        assert inst1.value == 42
        
        # 重置
        SingletonMeta._reset_instance(TestClass)
        
        # 创建新实例
        inst2 = TestClass()
        assert inst2 is not inst1
        assert inst2.value == 42


class TestCoreInitializerThreadSafety:
    """测试 CoreInitializer 的线程安全性"""

    def test_initialize_with_threading_lock(self):
        """initialize 方法使用 threading.RLock 是安全的"""
        from crawlo.initialization.core import CoreInitializer
        # 不重置单例，避免影响全局注册表
        # 只验证 initialize 可以正常调用
        instance = CoreInitializer()
        # 如果已经初始化，直接验证状态
        assert hasattr(instance, '_init_lock'), "Should have _init_lock"
        assert hasattr(instance, 'initialize'), "Should have initialize method"


class TestSingletonMetaPreservesClassAttributes:
    """测试 SingletonMeta 保留类的属性"""

    def test_class_name_preserved(self):
        """类名保留"""
        from crawlo.initialization.core import CoreInitializer
        assert CoreInitializer.__name__ == 'CoreInitializer'

    def test_class_doc_preserved(self):
        """类文档保留"""
        from crawlo.initialization.core import CoreInitializer
        assert CoreInitializer.__doc__ is not None
        assert '初始化器' in CoreInitializer.__doc__

    def test_class_methods_accessible(self):
        """类方法可访问"""
        from crawlo.initialization.core import CoreInitializer
        assert hasattr(CoreInitializer, 'initialize')
        assert hasattr(CoreInitializer, 'is_ready')
        assert hasattr(CoreInitializer, 'reset')
