#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Crawler Component Factory - Specialized for creating Crawler-related components
"""

from typing import Any, Type

from .base import ComponentFactory, ComponentSpec
from .registry import get_component_registry
from crawlo.core.engine import Engine
from crawlo.core.scheduler import Scheduler
from crawlo.stats.collector import StatsCollector
from crawlo.event import Subscriber
from crawlo.extension import ExtensionManager


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
        # 实际类型已在顶部导入
        supported_types = (
            Engine, Scheduler, StatsCollector, 
            Subscriber, ExtensionManager
        )
        return issubclass(component_type, supported_types)


# Engine component
def create_engine(crawler, **kwargs):
    # Engine 已在顶部导入
    return Engine(crawler)

# Scheduler component
def create_scheduler(crawler, **kwargs):
    # Scheduler 已在顶部导入
    return Scheduler.create_instance(crawler)

# StatsCollector component
def create_stats(crawler, **kwargs):
    # StatsCollector 已在顶部导入
    return StatsCollector(crawler)

# Subscriber component
def create_subscriber(**kwargs):
    # Subscriber 已在顶部导入
    return Subscriber()

# ExtensionManager component
def create_extension_manager(crawler, **kwargs):
    # ExtensionManager 已在顶部导入
    return ExtensionManager.create_instance(crawler)

def register_crawler_components():
    """Register Crawler-related components"""
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


# 自动注册
register_crawler_components()