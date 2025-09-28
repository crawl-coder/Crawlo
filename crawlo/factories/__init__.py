#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Crawlo组件工厂系统
==================

提供统一的组件创建和依赖注入机制
"""

from .registry import ComponentRegistry, get_component_registry
from .base import ComponentFactory, ComponentSpec
from .crawler import CrawlerComponentFactory

# 公共接口
register_component = get_component_registry().register
get_component = get_component_registry().get
create_component = get_component_registry().create

__all__ = [
    'ComponentRegistry',
    'ComponentFactory', 
    'ComponentSpec',
    'CrawlerComponentFactory',
    'get_component_registry',
    'register_component',
    'get_component',
    'create_component'
]