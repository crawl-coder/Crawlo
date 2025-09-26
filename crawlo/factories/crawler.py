#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Crawler组件工厂 - 专门用于创建Crawler相关组件
"""

from typing import Any, Type

from .base import ComponentFactory, ComponentSpec
from .registry import get_component_registry


class CrawlerComponentFactory(ComponentFactory):
    """Crawler组件工厂"""
    
    def create(self, spec: ComponentSpec, **kwargs) -> Any:
        """创建Crawler相关组件"""
        # 检查是否需要crawler依赖
        if 'crawler' in spec.dependencies and 'crawler' not in kwargs:
            raise ValueError(f"Crawler instance required for component {spec.name}")
        
        return spec.factory_func(**kwargs)
    
    def supports(self, component_type: Type) -> bool:
        """检查是否支持指定类型"""
        # 这里可以根据需要定义支持的组件类型
        supported_types = [
            'Engine', 'Scheduler', 'StatsCollector', 
            'Subscriber', 'ExtensionManager'
        ]
        return component_type.__name__ in supported_types


def register_crawler_components():
    """注册Crawler相关组件"""
    registry = get_component_registry()
    
    # 注册工厂
    registry.register_factory(CrawlerComponentFactory())
    
    # 注册组件规范
    
    # Engine组件
    def create_engine(crawler, **kwargs):
        from crawlo.core.engine import Engine
        return Engine(crawler)
    
    registry.register(ComponentSpec(
        name='engine',
        component_type=type('Engine', (), {}),
        factory_func=create_engine,
        dependencies=['crawler']
    ))
    
    # Scheduler组件
    def create_scheduler(crawler, **kwargs):
        from crawlo.core.scheduler import Scheduler
        return Scheduler.create_instance(crawler)
    
    registry.register(ComponentSpec(
        name='scheduler',
        component_type=type('Scheduler', (), {}),
        factory_func=create_scheduler,
        dependencies=['crawler']
    ))
    
    # StatsCollector组件
    def create_stats(crawler, **kwargs):
        from crawlo.stats_collector import StatsCollector
        return StatsCollector(crawler)
    
    registry.register(ComponentSpec(
        name='stats',
        component_type=type('StatsCollector', (), {}),
        factory_func=create_stats,
        dependencies=['crawler']
    ))
    
    # Subscriber组件
    def create_subscriber(**kwargs):
        from crawlo.subscriber import Subscriber
        return Subscriber()
    
    registry.register(ComponentSpec(
        name='subscriber',
        component_type=type('Subscriber', (), {}),
        factory_func=create_subscriber
    ))
    
    # ExtensionManager组件
    def create_extension_manager(crawler, **kwargs):
        from crawlo.extension import ExtensionManager
        return ExtensionManager.create_instance(crawler)
    
    registry.register(ComponentSpec(
        name='extension_manager',
        component_type=type('ExtensionManager', (), {}),
        factory_func=create_extension_manager,
        dependencies=['crawler']
    ))


# 自动注册
register_crawler_components()