#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Crawlo 组件注册与工厂构建工具（从 factories.py 迁出）

职责：
- register_component / register_components：便捷注册（批量）组件 spec
- create_component_factory：通用工厂函数构建器（按 module_path + class_name 懒 import 实例化）
- create_crawler_component_factory：带 crawler 依赖注入的工厂函数构建器（给需要 crawler 句柄的组件用）
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Type, Union

from crawlo.core.component_base import ComponentSpec
from crawlo.core.component_registry import get_component_registry


__all__ = [
    "register_component",
    "register_components",
    "create_component_factory",
    "create_crawler_component_factory",
]


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

    if isinstance(component_type, str):
        # Store as string type identifier, factories will use name-based matching
        component_type = type(component_type, (), {'__type_identifier__': component_type})

    spec_kwargs: Dict[str, Any] = {
        'name': name,
        'component_type': component_type,
        'factory_func': factory_func,
        'dependencies': dependencies or [],
        'singleton': singleton,
    }

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
            module = __import__(module_path, fromlist=[class_name])
            component_class = getattr(module, class_name)

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
            module = __import__(module_path, fromlist=[class_name])
            component_class = getattr(module, class_name)

            if hasattr(component_class, 'create_instance'):
                return component_class.create_instance(crawler, **kwargs)
            else:
                return component_class(crawler, **kwargs)
        except Exception as e:
            raise RuntimeError(f"Failed to create {component_name}: {e}")

    return factory_func
