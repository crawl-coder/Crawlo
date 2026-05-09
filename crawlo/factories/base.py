#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Component Factory Base Classes and Specifications
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Type, Any, Dict, Callable, List, Optional


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
        pass
    
    @abstractmethod
    def supports(self, component_type: Type) -> bool:
        """Check if the factory supports the specified component type"""
        pass


class DefaultComponentFactory(ComponentFactory):
    """Default Component Factory Implementation"""
    
    def __init__(self):
        self._instances: Dict[str, Any] = {}
    
    def create(self, spec: ComponentSpec, **kwargs) -> Any:
        """Create component instance"""
        # Singleton pattern check
        if spec.singleton and spec.name in self._instances:
            return self._instances[spec.name]
        
        # Call factory function to create instance
        instance = spec.factory_func(**kwargs)
        
        # Save singleton instance
        if spec.singleton:
            self._instances[spec.name] = instance
        
        return instance
    
    def supports(self, component_type: Type) -> bool:
        """Supports all types"""
        return True
    
    def clear_singletons(self):
        """Clear singleton instances (for testing)"""
        self._instances.clear()