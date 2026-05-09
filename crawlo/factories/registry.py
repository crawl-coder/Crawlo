#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Component Registry - Manages registration and creation of all components
"""

import asyncio
from typing import Dict, List, Type, Any, Optional

from .base import ComponentFactory, ComponentSpec, DefaultComponentFactory
from crawlo.utils.async_lock import AsyncRLock


class ComponentRegistry:
    """
    Component Registry
    
    Responsibilities:
    1. Manage component specification registration
    2. Find appropriate factory by type
    3. Handle dependencies
    4. Create component instances
    """
    
    def __init__(self):
        self._specs: Dict[str, ComponentSpec] = {}
        self._factories: List[ComponentFactory] = []
        self._default_factory = DefaultComponentFactory()
        self._lock = AsyncRLock()  # 异步安全锁
    
    async def register_async(self, spec: ComponentSpec):
        """Async-safe registration method"""
        async with self._lock:
            self._specs[spec.name] = spec
    
    async def register_factory_async(self, factory: ComponentFactory):
        """Async-safe factory registration method"""
        async with self._lock:
            self._factories.append(factory)
    
    async def get_spec_async(self, name: str) -> Optional[ComponentSpec]:
        """Async-safe spec retrieval method"""
        async with self._lock:
            return self._specs.get(name)
    
    async def get_factory_async(self, component_type: Type) -> ComponentFactory:
        """Async-safe factory retrieval method"""
        async with self._lock:
            for factory in self._factories:
                if factory.supports(component_type):
                    return factory
            return self._default_factory
    
    async def list_components_async(self) -> List[str]:
        """Async-safe component listing method"""
        async with self._lock:
            return list(self._specs.keys())
    
    def register(self, spec: ComponentSpec):
        """
        Register component spec (synchronous version, for initialization phase)
        Use register_async() in async environments for lock protection
        """
        self._specs[spec.name] = spec
    
    def register_factory(self, factory: ComponentFactory):
        """
        Register component factory (synchronous method, for backward compatibility only)
        :deprecated: Use register_factory_async instead
        """
        self._factories.append(factory)
    
    def get_spec(self, name: str) -> Optional[ComponentSpec]:
        """
        Get component spec (synchronous method, for backward compatibility only)
        :deprecated: Use get_spec_async instead
        """
        return self._specs.get(name)
    
    def get_factory(self, component_type: Type) -> ComponentFactory:
        """
        Get factory that supports the specified type (synchronous method)
        """
        for factory in self._factories:
            if factory.supports(component_type):
                return factory
        return self._default_factory
    
    def create(self, name: str, **kwargs) -> Any:
        """Create component instance"""
        spec = self.get_spec(name)
        if not spec:
            raise ValueError(f"Component spec '{name}' not found")
        
        factory = self.get_factory(spec.component_type)
        return factory.create(spec, **kwargs)
    
    def get(self, name: str, **kwargs) -> Any:
        """Get component instance (alias for create)"""
        return self.create(name, **kwargs)
    
    def list_components(self) -> List[str]:
        """
        List all registered components (synchronous method)
        """
        return list(self._specs.keys())
    
    def clear(self):
        """
        Clear the registry
        """
        self._specs.clear()
        self._factories.clear()
        self._default_factory.clear_singletons()


# Global component registry
_global_registry = ComponentRegistry()


def get_component_registry() -> ComponentRegistry:
    """Get the global component registry"""
    return _global_registry