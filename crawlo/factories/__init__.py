#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Crawlo Component Factory System
================================

Provides unified component creation and dependency injection mechanism.
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