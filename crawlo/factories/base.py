#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
组件工厂基类和规范
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Type, Any, Dict, Callable


@dataclass
class ComponentSpec:
    """组件规范 - 定义如何创建组件"""
    
    name: str
    component_type: Type
    factory_func: Callable[..., Any]
    dependencies: list = None
    singleton: bool = False
    config_key: str = None
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


class ComponentFactory(ABC):
    """组件工厂基类"""
    
    @abstractmethod
    def create(self, spec: ComponentSpec, **kwargs) -> Any:
        """创建组件实例"""
        pass
    
    @abstractmethod
    def supports(self, component_type: Type) -> bool:
        """检查是否支持指定类型的组件"""
        pass


class DefaultComponentFactory(ComponentFactory):
    """默认组件工厂实现"""
    
    def __init__(self):
        self._instances: Dict[str, Any] = {}
    
    def create(self, spec: ComponentSpec, **kwargs) -> Any:
        """创建组件实例"""
        # 单例模式检查
        if spec.singleton and spec.name in self._instances:
            return self._instances[spec.name]
        
        # 调用工厂函数创建实例
        instance = spec.factory_func(**kwargs)
        
        # 保存单例实例
        if spec.singleton:
            self._instances[spec.name] = instance
        
        return instance
    
    def supports(self, component_type: Type) -> bool:
        """支持所有类型"""
        return True
    
    def clear_singletons(self):
        """清除单例实例（测试用）"""
        self._instances.clear()