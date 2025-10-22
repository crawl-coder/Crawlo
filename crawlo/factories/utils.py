#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
工厂工具模块 - 提供通用的组件注册和创建工具
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
    注册组件的便捷函数
    
    Args:
        name: 组件名称
        component_type: 组件类型
        factory_func: 工厂函数
        dependencies: 依赖列表
        singleton: 是否单例
        config_key: 配置键名
    """
    registry = get_component_registry()
    
    # 如果component_type是字符串，创建一个动态类型
    if isinstance(component_type, str):
        component_type = type(component_type, (), {})
    
    spec_kwargs = {
        'name': name,
        'component_type': component_type,
        'factory_func': factory_func,
        'dependencies': dependencies or [],
        'singleton': singleton
    }
    
    # 只有当config_key不为None时才添加
    if config_key is not None:
        spec_kwargs['config_key'] = config_key
    
    spec = ComponentSpec(**spec_kwargs)
    
    registry.register(spec)


def register_components(component_list: List[dict]) -> None:
    """
    批量注册组件
    
    Args:
        component_list: 组件定义列表，每个元素是一个包含组件信息的字典
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
    创建组件工厂函数的便捷函数
    
    Args:
        component_name: 组件名称（用于错误信息）
        module_path: 模块路径
        class_name: 类名
        dependencies: 依赖列表
        singleton: 是否单例
        
    Returns:
        工厂函数
    """
    def factory_func(*args, **kwargs):
        try:
            # 动态导入模块
            module = __import__(module_path, fromlist=[class_name])
            component_class = getattr(module, class_name)
            
            # 检查是否需要调用create_instance方法
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
    创建需要crawler依赖的组件工厂函数
    
    Args:
        component_name: 组件名称
        module_path: 模块路径
        class_name: 类名
        
    Returns:
        工厂函数
    """
    def factory_func(crawler=None, **kwargs):
        if crawler is None:
            raise ValueError(f"Crawler instance required for component {component_name}")
        
        try:
            # 动态导入模块
            module = __import__(module_path, fromlist=[class_name])
            component_class = getattr(module, class_name)
            
            # 检查是否需要调用create_instance方法
            if hasattr(component_class, 'create_instance'):
                return component_class.create_instance(crawler, **kwargs)
            else:
                return component_class(crawler, **kwargs)
        except Exception as e:
            raise RuntimeError(f"Failed to create {component_name}: {e}")
    
    return factory_func