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
    """确保 Crawler 相关组件已注册（Phase 8 Step 8.3：容器优先 + RegistryContext 兜底）。

    ``components_registered`` 属于 RegistryContext；Phase 8.2 已把 RegistryContext 整体
    注册进 default_container，因此这里优先从容器拿到 RegistryContext，避免直接 import
    ApplicationContext。若容器未就绪（import 期/测试期），再 fallback 到 ctx。
    """
    reg_ctx = None
    try:
        from crawlo.container import default_container
        from crawlo.core.application import RegistryContext
        if default_container.is_registered(RegistryContext):
            reg_ctx = default_container.resolve(RegistryContext)
    except Exception:  # noqa: S110
        reg_ctx = None

    if reg_ctx is None:
        from crawlo.core.application import get_global_context
        reg_ctx = get_global_context().registries

    if not reg_ctx.components_registered:
        from .crawler import register_crawler_components
        register_crawler_components()
        reg_ctx.components_registered = True


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