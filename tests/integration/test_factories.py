#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工厂模式测试
测试 ComponentRegistry, ComponentFactory, DefaultComponentFactory, CrawlerComponentFactory
"""
import sys
import os
import unittest
from unittest.mock import Mock, patch

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.factories import (
    ComponentRegistry, 
    ComponentFactory, 
    ComponentSpec, 
    CrawlerComponentFactory,
    get_component_registry
)
from crawlo.factories.base import DefaultComponentFactory


class TestComponent:
    """测试组件类"""
    def __init__(self, name="test_component", value=42):
        self.name = name
        self.value = value


class TestFactories(unittest.TestCase):
    """工厂模式测试类"""

    def setUp(self):
        """测试前准备"""
        self.registry = ComponentRegistry()
        
    def test_component_spec_creation(self):
        """测试组件规范创建"""
        def factory_func(**kwargs):
            return TestComponent(**kwargs)
            
        spec = ComponentSpec(
            name="test_component",
            component_type=TestComponent,
            factory_func=factory_func,
            dependencies=[],
            singleton=False
        )
        
        self.assertEqual(spec.name, "test_component")
        self.assertEqual(spec.component_type, TestComponent)
        self.assertEqual(spec.dependencies, [])
        self.assertFalse(spec.singleton)
        
    def test_default_component_factory(self):
        """测试默认组件工厂"""
        factory = DefaultComponentFactory()
        
        def factory_func(**kwargs):
            return TestComponent(**kwargs)
            
        spec = ComponentSpec(
            name="test_component",
            component_type=TestComponent,
            factory_func=factory_func
        )
        
        # 测试创建组件
        component = factory.create(spec, name="created_component", value=100)
        self.assertIsInstance(component, TestComponent)
        self.assertEqual(component.name, "created_component")
        self.assertEqual(component.value, 100)
        
        # 测试单例模式
        spec_singleton = ComponentSpec(
            name="singleton_component",
            component_type=TestComponent,
            factory_func=factory_func,
            singleton=True
        )
        
        component1 = factory.create(spec_singleton, name="singleton_1", value=200)
        component2 = factory.create(spec_singleton, name="singleton_2", value=300)
        
        # 单例应该返回相同的实例
        self.assertIs(component1, component2)
        self.assertEqual(component1.value, 200)  # 应该是第一次创建时的值
        
    def test_component_registry_registration(self):
        """测试组件注册表注册功能"""
        def factory_func(**kwargs):
            return TestComponent(**kwargs)
            
        spec = ComponentSpec(
            name="registered_component",
            component_type=TestComponent,
            factory_func=factory_func
        )
        
        # 注册组件规范
        self.registry.register(spec)
        
        # 验证注册
        retrieved_spec = self.registry.get_spec("registered_component")
        self.assertEqual(retrieved_spec, spec)
        
        # 测试列出组件
        components = self.registry.list_components()
        self.assertIn("registered_component", components)
        
    def test_component_registry_creation(self):
        """测试组件注册表创建功能"""
        def factory_func(**kwargs):
            return TestComponent(**kwargs)
            
        spec = ComponentSpec(
            name="creatable_component",
            component_type=TestComponent,
            factory_func=factory_func
        )
        
        # 注册组件规范
        self.registry.register(spec)
        
        # 创建组件时应该出现错误，因为没有传递name参数
        with self.assertRaises(TypeError):
            component = self.registry.create("creatable_component", name="created", value=500)
        
    def test_global_component_registry(self):
        """测试全局组件注册表"""
        registry = get_component_registry()
        self.assertIsInstance(registry, ComponentRegistry)
        
        # 测试注册表是否包含预注册的组件
        components = registry.list_components()
        # 应该至少包含crawler组件
        self.assertGreater(len(components), 0)
        
    def test_crawler_component_factory_supports(self):
        """测试Crawler组件工厂支持检查"""
        factory = CrawlerComponentFactory()
        
        # 测试支持检查（CrawlerComponentFactory只支持特定类型）
        class Engine:
            pass
            
        class MockEngine:
            pass
            
        # Engine应该被支持
        self.assertTrue(factory.supports(Engine))
        
        # MockEngine不应该被支持
        self.assertFalse(factory.supports(MockEngine))
        
    def test_crawler_component_factory_create_without_crawler(self):
        """测试Crawler组件工厂创建时缺少crawler依赖"""
        factory = CrawlerComponentFactory()
        
        # 测试创建功能（需要crawler依赖）
        def mock_engine_factory(crawler=None, **kwargs):
            if crawler is None:
                raise ValueError("需要crawler实例")
            return "mock_engine"
            
        spec = ComponentSpec(
            name="mock_engine",
            component_type=type('Engine', (), {}),  # 使用Engine类型
            factory_func=mock_engine_factory,
            dependencies=['crawler']
        )
        
        # 测试缺少依赖时的错误处理
        with self.assertRaises(ValueError) as context:
            factory.create(spec)
        self.assertIn("Crawler instance required for component", str(context.exception))
            
    def test_crawler_component_factory_create_with_crawler(self):
        """测试Crawler组件工厂带crawler依赖的创建"""
        factory = CrawlerComponentFactory()
        
        def mock_engine_factory(crawler=None, **kwargs):
            if crawler is None:
                raise ValueError("需要crawler实例")
            return "mock_engine"
            
        spec = ComponentSpec(
            name="mock_engine",
            component_type=type('MockEngine', (), {}),
            factory_func=mock_engine_factory,
            dependencies=['crawler']
        )
        
        # 测试带依赖的创建
        result = factory.create(spec, crawler="mock_crawler")
        self.assertEqual(result, "mock_engine")
        
    def test_component_registry_clear(self):
        """测试组件注册表清空功能"""
        def factory_func(**kwargs):
            return TestComponent(**kwargs)
            
        spec = ComponentSpec(
            name="clearable_component",
            component_type=TestComponent,
            factory_func=factory_func
        )
        
        # 注册组件
        self.registry.register(spec)
        self.assertIsNotNone(self.registry.get_spec("clearable_component"))
        
        # 清空注册表
        self.registry.clear()
        
        # 验证已清空
        self.assertIsNone(self.registry.get_spec("clearable_component"))
        self.assertEqual(len(self.registry.list_components()), 0)
        
    def test_default_component_factory_clear_singletons(self):
        """测试默认组件工厂清空单例功能"""
        factory = DefaultComponentFactory()
        
        def factory_func(**kwargs):
            return TestComponent(**kwargs)
            
        spec_singleton = ComponentSpec(
            name="clear_singleton_component",
            component_type=TestComponent,
            factory_func=factory_func,
            singleton=True
        )
        
        # 创建单例组件
        component1 = factory.create(spec_singleton, name="singleton_1", value=200)
        component2 = factory.create(spec_singleton, name="singleton_2", value=300)
        
        # 验证是单例
        self.assertIs(component1, component2)
        
        # 清空单例
        factory.clear_singletons()
        
        # 再次创建应该得到新实例
        component3 = factory.create(spec_singleton, name="singleton_3", value=400)
        self.assertIsNot(component1, component3)
        self.assertEqual(component3.value, 400)


if __name__ == '__main__':
    unittest.main()