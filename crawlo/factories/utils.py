#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Factory Utilities - Generic component registration and creation tools
"""

from typing import Any, Callable, List, Optional, Type, Union
from .base import ComponentSpec
from .registry import get_component_registry


def register_component(
    name: str,
    component_type: Union[Type, str],
    factory_func: Callable[..., Any],
    dependencies: Optional[List[str]] = None,
    singleton: bool = False,
    config_key: Optional[str] = None
) -> None:
    """
    Convenience function for registering components
    
    Args:
        name: Component name
        component_type: Component type
        factory_func: Factory function
        dependencies: Dependency list
        singleton: Whether to use singleton pattern
        config_key: Configuration key name
    """
    registry = get_component_registry()
    
    # If component_type is a string, use it as identifier (not creating empty class)
    if isinstance(component_type, str):
        # Store as string type identifier, factories will use name-based matching
        component_type = type(component_type, (), {'__type_identifier__': component_type})
    
    spec_kwargs = {
        'name': name,
        'component_type': component_type,
        'factory_func': factory_func,
        'dependencies': dependencies or [],
        'singleton': singleton
    }
    
    # Only add config_key if it's not None
    if config_key is not None:
        spec_kwargs['config_key'] = config_key
    
    spec = ComponentSpec(**spec_kwargs)
    
    registry.register(spec)


def register_components(component_list: List[dict]) -> None:
    """
    Batch register components
    
    Args:
        component_list: Component definition list, each element is a dictionary containing component info
    """
    for component_info in component_list:
        register_component(**component_info)


def create_component_factory(
    component_name: str,
    module_path: str,
    class_name: str,
    dependencies: Optional[List[str]] = None,
    singleton: bool = False
) -> Callable[..., Any]:
    """
    Convenience function for creating component factory functions
    
    Args:
        component_name: Component name (for error messages)
        module_path: Module path
        class_name: Class name
        dependencies: Dependency list
        singleton: Whether to use singleton pattern
        
    Returns:
        Factory function
    """
    def factory_func(*args, **kwargs):
        try:
            # Dynamic module import
            module = __import__(module_path, fromlist=[class_name])
            component_class = getattr(module, class_name)
            
            # Check if create_instance method should be called
            if hasattr(component_class, 'create_instance'):
                return component_class.create_instance(*args, **kwargs)
            else:
                return component_class(*args, **kwargs)
        except Exception as e:
            raise RuntimeError(f"Failed to create {component_name}: {e}")
    
    return factory_func


def create_crawler_component_factory(
    component_name: str,
    module_path: str,
    class_name: str
) -> Callable[..., Any]:
    """
    Create component factory function that requires crawler dependency
    
    Args:
        component_name: Component name
        module_path: Module path
        class_name: Class name
        
    Returns:
        Factory function
    """
    def factory_func(crawler=None, **kwargs):
        if crawler is None:
            raise ValueError(f"Crawler instance required for component {component_name}")
        
        try:
            # Dynamic module import
            module = __import__(module_path, fromlist=[class_name])
            component_class = getattr(module, class_name)
            
            # Check if create_instance method should be called
            if hasattr(component_class, 'create_instance'):
                return component_class.create_instance(crawler, **kwargs)
            else:
                return component_class(crawler, **kwargs)
        except Exception as e:
            raise RuntimeError(f"Failed to create {component_name}: {e}")
    
    return factory_func