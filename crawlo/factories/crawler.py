#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Crawler Component Factory - Specialized for creating Crawler-related components
"""

from typing import Any, Type

from .base import ComponentFactory, ComponentSpec
from .registry import get_component_registry


class CrawlerComponentFactory(ComponentFactory):
    """Crawler Component Factory"""
    
    def create(self, spec: ComponentSpec, **kwargs) -> Any:
        """Create Crawler-related components"""
        # Check if crawler dependency is required
        if 'crawler' in spec.dependencies and 'crawler' not in kwargs:
            raise ValueError(f"Crawler instance required for component {spec.name}")
        
        return spec.factory_func(**kwargs)
    
    def supports(self, component_type: Type) -> bool:
        """Check if the specified type is supported"""
        # 延迟导入以避免启动时的性能开销
        from crawlo.core.engine import Engine
        from crawlo.core.scheduler import Scheduler
        from crawlo.stats.collector import StatsCollector
        from crawlo.event import Subscriber
        from crawlo.extension import ExtensionManager
        
        supported_types = (
            Engine, Scheduler, StatsCollector, 
            Subscriber, ExtensionManager
        )
        return issubclass(component_type, supported_types)


# Engine component
def create_engine(crawler, **kwargs):
    from crawlo.core.engine import Engine
    return Engine(crawler)

# Scheduler component
def create_scheduler(crawler, **kwargs):
    from crawlo.core.scheduler import Scheduler
    return Scheduler.create_instance(crawler)

# StatsCollector component
def create_stats(crawler, **kwargs):
    from crawlo.stats.collector import StatsCollector
    return StatsCollector(crawler)

# Subscriber component
def create_subscriber(**kwargs):
    from crawlo.event import Subscriber
    return Subscriber()

# ExtensionManager component
def create_extension_manager(crawler, **kwargs):
    from crawlo.extension import ExtensionManager
    return ExtensionManager.create_instance(crawler)

def register_crawler_components():
    """Register Crawler-related components (延迟调用，首次使用时由 factories/__init__.py 触发)"""
    from .utils import register_components
    
    # Register factory
    registry = get_component_registry()
    registry.register_factory(CrawlerComponentFactory())
    
    # Batch register components
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


# 注意：不再在模块级别自动调用 register_crawler_components()
# 注册改为延迟触发：由 crawlo.factories.__init__.py 的 _ensure_components_registered() 在首次 get_component_registry() 时触发