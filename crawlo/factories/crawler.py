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


# Engine组件
def create_engine(crawler, **kwargs):
    from crawlo.core.engine import Engine
    return Engine(crawler)

# Scheduler组件
def create_scheduler(crawler, **kwargs):
    from crawlo.core.scheduler import Scheduler
    return Scheduler.create_instance(crawler)

# StatsCollector组件
def create_stats(crawler, **kwargs):
    from crawlo.stats_collector import StatsCollector
    return StatsCollector(crawler)

# Subscriber组件
def create_subscriber(**kwargs):
    from crawlo.subscriber import Subscriber
    return Subscriber()

# ExtensionManager组件
def create_extension_manager(crawler, **kwargs):
    from crawlo.extension import ExtensionManager
    return ExtensionManager.create_instance(crawler)

def register_crawler_components():
    """注册Crawler相关组件"""
    from .utils import register_components
    
    # 注册工厂
    registry = get_component_registry()
    registry.register_factory(CrawlerComponentFactory())
    
    # 批量注册组件
    component_list = [
        {
            'name': 'engine',
            'component_type': 'Engine',
            'factory_func': create_engine,
            'dependencies': ['crawler']
        },
        {
            'name': 'scheduler',
            'component_type': 'Scheduler',
            'factory_func': create_scheduler,
            'dependencies': ['crawler']
        },
        {
            'name': 'stats',
            'component_type': 'StatsCollector',
            'factory_func': create_stats,
            'dependencies': ['crawler']
        },
        {
            'name': 'subscriber',
            'component_type': 'Subscriber',
            'factory_func': create_subscriber,
            'dependencies': []
        },
        {
            'name': 'extension_manager',
            'component_type': 'ExtensionManager',
            'factory_func': create_extension_manager,
            'dependencies': ['crawler']
        }
    ]
    
    register_components(component_list)


# 自动注册
register_crawler_components()