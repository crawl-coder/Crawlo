#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Crawlo Component Factory System
================================

Provides unified component creation and dependency injection mechanism.
"""

from .registry import ComponentRegistry, get_component_registry as _get_component_registry
from .base import ComponentFactory, ComponentSpec

def _ensure_components_registered():
    """确保 Crawler 相关组件已注册（首次使用时才触发，状态存储于 ApplicationContext）"""
    from crawlo.core.application import get_global_context
    ctx = get_global_context()
    if not ctx.components_registered:
        from .crawler import register_crawler_components
        register_crawler_components()
        ctx.components_registered = True


def get_component_registry():
    """获取全局组件注册表（首次调用时自动完成 Crawler 组件注册）"""
    _ensure_components_registered()
    return _get_component_registry()


# 公共接口（延迟注册）
def register_component(spec):
    """注册组件（首次调用时自动完成 Crawler 组件注册）"""
    _ensure_components_registered()
    return _get_component_registry().register(spec)


def get_component(name, **kwargs):
    """获取组件实例（首次调用时自动完成 Crawler 组件注册）"""
    _ensure_components_registered()
    return _get_component_registry().get(name, **kwargs)


def create_component(name, **kwargs):
    """创建组件实例（首次调用时自动完成 Crawler 组件注册）"""
    _ensure_components_registered()
    return _get_component_registry().create(name, **kwargs)


def __getattr__(name):
    """模块级延迟导入（PEP 562），避免 import 时触发 CrawlerComponentFactory 的注册链"""
    if name == 'CrawlerComponentFactory':
        _ensure_components_registered()
        from .crawler import CrawlerComponentFactory
        return CrawlerComponentFactory
    raise AttributeError(f"module 'crawlo.factories' has no attribute '{name}'")


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