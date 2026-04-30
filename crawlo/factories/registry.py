#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
组件注册表 - 管理所有组件的注册和创建
"""

import asyncio
from typing import Dict, List, Type, Any, Optional

from .base import ComponentFactory, ComponentSpec, DefaultComponentFactory
from crawlo.utils.async_lock import AsyncRLock


class ComponentRegistry:
    """
    组件注册表
    
    职责：
    1. 管理组件规范的注册
    2. 根据类型查找合适的工厂
    3. 处理依赖关系
    4. 创建组件实例
    """
    
    def __init__(self):
        self._specs: Dict[str, ComponentSpec] = {}
        self._factories: List[ComponentFactory] = []
        self._default_factory = DefaultComponentFactory()
        self._lock = AsyncRLock()  # 异步安全锁
    
    async def register_async(self, spec: ComponentSpec):
        """异步安全的注册方法"""
        async with self._lock:
            self._specs[spec.name] = spec
    
    async def register_factory_async(self, factory: ComponentFactory):
        """异步安全的工厂注册方法"""
        async with self._lock:
            self._factories.append(factory)
    
    async def get_spec_async(self, name: str) -> Optional[ComponentSpec]:
        """异步安全的获取规范方法"""
        async with self._lock:
            return self._specs.get(name)
    
    async def get_factory_async(self, component_type: Type) -> ComponentFactory:
        """异步安全的获取工厂方法"""
        async with self._lock:
            for factory in self._factories:
                if factory.supports(component_type):
                    return factory
            return self._default_factory
    
    async def list_components_async(self) -> List[str]:
        """异步安全的列出组件方法"""
        async with self._lock:
            return list(self._specs.keys())
    
    def register(self, spec: ComponentSpec):
        """
        注册组件规范（同步版本，用于初始化阶段）
        异步环境请使用 register_async() 以获取锁保护
        """
        self._specs[spec.name] = spec
    
    def register_factory(self, factory: ComponentFactory):
        """
        注册组件工厂（同步方法，仅用于向后兼容）
        :deprecated: 请使用 register_factory_async
        """
        self._factories.append(factory)
    
    def get_spec(self, name: str) -> Optional[ComponentSpec]:
        """
        获取组件规范（同步方法，仅用于向后兼容）
        :deprecated: 请使用 get_spec_async
        """
        return self._specs.get(name)
    
    def get_factory(self, component_type: Type) -> ComponentFactory:
        """
        获取支持指定类型的工厂（同步方法）
        """
        for factory in self._factories:
            if factory.supports(component_type):
                return factory
        return self._default_factory
    
    def create(self, name: str, **kwargs) -> Any:
        """创建组件实例"""
        spec = self.get_spec(name)
        if not spec:
            raise ValueError(f"Component spec '{name}' not found")
        
        factory = self.get_factory(spec.component_type)
        return factory.create(spec, **kwargs)
    
    def get(self, name: str, **kwargs) -> Any:
        """获取组件实例（create的别名）"""
        return self.create(name, **kwargs)
    
    def list_components(self) -> List[str]:
        """
        列出所有已注册的组件（同步方法）
        """
        return list(self._specs.keys())
    
    def clear(self):
        """
        清空注册表
        """
        self._specs.clear()
        self._factories.clear()
        self._default_factory.clear_singletons()


# 全局组件注册表
_global_registry = ComponentRegistry()


def get_component_registry() -> ComponentRegistry:
    """获取全局组件注册表"""
    return _global_registry