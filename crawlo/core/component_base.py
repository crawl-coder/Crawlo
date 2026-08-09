#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Crawlo 组件基类与规格定义（从 factories.py 迁出）

本模块仅包含最基本的抽象定义，不依赖 registry / application 容器，
确保可被任何需要"组件声明语义"的模块在 import 期安全引用。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Type


__all__ = [
    "ComponentSpec",
    "ComponentFactory",
    "DefaultComponentFactory",
]


@dataclass
class ComponentSpec:
    """Component Specification - Defines how to create a component"""

    name: str
    component_type: Type
    factory_func: Callable[..., Any]
    dependencies: Optional[List[str]] = None
    singleton: bool = False
    config_key: Optional[str] = None

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


class ComponentFactory(ABC):
    """Component Factory Base Class"""

    @abstractmethod
    def create(self, spec: ComponentSpec, **kwargs) -> Any:
        """Create component instance"""

    @abstractmethod
    def supports(self, component_type: Type) -> bool:
        """Check if the factory supports the specified component type"""


class DefaultComponentFactory(ComponentFactory):
    """Default Component Factory Implementation"""

    def __init__(self):
        self._instances: Dict[str, Any] = {}

    def create(self, spec: ComponentSpec, **kwargs) -> Any:
        """Create component instance"""
        if spec.singleton and spec.name in self._instances:
            return self._instances[spec.name]

        instance = spec.factory_func(**kwargs)

        if spec.singleton:
            self._instances[spec.name] = instance

        return instance

    def supports(self, component_type: Type) -> bool:
        """Supports all types"""
        return True

    def clear_singletons(self):
        """Clear singleton instances (for testing)"""
        self._instances.clear()
