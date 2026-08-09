#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Crawlo Component Factory System
================================================

原 factories.py 约 563 行混合 5 个子模块职责，现按职责拆分为：

* `crawlo.core.component_base`     — ComponentSpec / ComponentFactory / DefaultComponentFactory
* `crawlo.core.component_registry` — ComponentRegistry + get_component_registry
* `crawlo.core.component_utils`    — register_component(s) / create_component_factory / create_crawler_component_factory

本模块（factories.py）只保留：
1. Crawler 相关组件的具体工厂函数（create_engine / create_scheduler / ...）
2. CrawlerComponentFactory（专用于 Crawler 组件的工厂实现）
3. register_crawler_components()（批量注册上述组件）
4. 顶层延迟注册 _ensure_components_registered + get_component_registry / register_component / get_component / create_component
5. deprecated re-export：对已迁出符号，仍可通过本模块 import，行为一致但会在访问符号时触发 DeprecationWarning（通过 ``__getattr__`` 延迟触发，避免 import 期刷屏）。
"""
from __future__ import annotations

import warnings
from typing import Any, Type

# —— 内部真实使用的迁出符号：**全部加别名且以下划线开头**，确保不会污染模块命名空间；
#    使得对外导出的同名符号（ComponentSpec / ComponentFactory / ...）在模块 __dict__
#    中不存在，进而会触发 __getattr__ → 给出 DeprecationWarning 并返回同一对象引用。
from crawlo.core.component_base import (
    ComponentSpec as _ComponentSpec,
    ComponentFactory as _ComponentFactoryBase,
)
from crawlo.core.component_registry import (
    get_component_registry as _get_registry_impl,
)
from crawlo.core.component_utils import (
    register_component,
    register_components as _batch_register,
)


# —— 已迁移符号清单：当外部代码 ``from crawlo.core.factories import ComponentSpec``
#    触发 __getattr__ 时，给出 DeprecationWarning 并返回同引用对象（保证身份相等）。
_MIGRATED_SYMBOLS: dict[str, tuple[str, str]] = {
    "ComponentSpec":               ("crawlo.core.component_base",     "基类与规格定义"),
    "ComponentFactory":            ("crawlo.core.component_base",     "基类与规格定义"),
    "DefaultComponentFactory":     ("crawlo.core.component_base",     "基类与规格定义"),
    "ComponentRegistry":           ("crawlo.core.component_registry", "组件注册表与全局解析"),
    "register_components":         ("crawlo.core.component_utils",    "组件注册 / 工厂构建工具"),
    "create_component_factory":    ("crawlo.core.component_utils",    "组件注册 / 工厂构建工具"),
    "create_crawler_component_factory": ("crawlo.core.component_utils", "组件注册 / 工厂构建工具"),
}


__all__ = [
    # —— migrated (deprecated re-export; 通过 __getattr__ 延迟告警) ——
    "ComponentSpec",
    "ComponentFactory",
    "DefaultComponentFactory",
    "ComponentRegistry",
    # —— stayed in this module ——
    "CrawlerComponentFactory",
    # —— top-level helpers（主入口继续保留且无告警）——
    "get_component_registry",
    "register_component",
    "get_component",
    "create_component",
    "register_components",
    "create_component_factory",
    "create_crawler_component_factory",
    "register_crawler_components",
    "create_engine",
    "create_scheduler",
    "create_stats",
    "create_subscriber",
    "create_extension_manager",
]


def __getattr__(name: str):
    """对已迁出符号，在首次访问时给出 DeprecationWarning 并返回同对象。"""
    if name in _MIGRATED_SYMBOLS:
        new_module, desc = _MIGRATED_SYMBOLS[name]
        warnings.warn(
            f"`crawlo.core.factories.{name}` 迁出至 `{new_module}` "
            f"（{desc}）。旧 `from crawlo.core.factories import {name}` 仍可用但已 deprecated，"
            f"请改为 `from {new_module} import {name}`（或直接使用新提供的专用 API）。"
            "兼容 re-export 将在 v3.1 移除。",
            DeprecationWarning,
            stacklevel=2,
        )
        import sys as _sys
        mod = _sys.modules[new_module]
        value = getattr(mod, name)
        globals()[name] = value
        return value
    raise AttributeError(f"module 'crawlo.core.factories' has no attribute {name!r}")


# ===================================================================
# Crawler 组件工厂与具体构建函数
# ===================================================================


class CrawlerComponentFactory(_ComponentFactoryBase):
    """Crawler Component Factory"""

    def create(self, spec: _ComponentSpec, **kwargs) -> Any:
        """Create Crawler-related components"""
        if 'crawler' in spec.dependencies and 'crawler' not in kwargs:
            raise ValueError(f"Crawler instance required for component {spec.name}")

        return spec.factory_func(**kwargs)

    def supports(self, component_type: Type) -> bool:
        """Check if the specified type is supported"""
        from crawlo.core.engine import Engine
        from crawlo.core.scheduling.task_scheduler import Scheduler
        from crawlo.stats.collector import StatsCollector
        from crawlo.event import Subscriber
        from crawlo.extensions import ExtensionManager

        supported_types = (
            Engine, Scheduler, StatsCollector,
            Subscriber, ExtensionManager,
        )
        return issubclass(component_type, supported_types)


def create_engine(crawler, **kwargs):
    from crawlo.core.engine import Engine
    return Engine(crawler)


def create_scheduler(crawler, **kwargs):
    from crawlo.core.scheduling.task_scheduler import Scheduler
    return Scheduler.create_instance(crawler)


def create_stats(crawler, **kwargs):
    from crawlo.stats.collector import StatsCollector
    return StatsCollector(crawler)


def create_subscriber(**kwargs):
    from crawlo.event import Subscriber
    return Subscriber()


def create_extension_manager(crawler, **kwargs):
    from crawlo.extensions import ExtensionManager
    return ExtensionManager.create_instance(crawler)


def register_crawler_components():
    """Register Crawler-related components (延迟调用，首次使用时由 _ensure_components_registered 触发)"""

    registry = _get_registry_impl()
    registry.register_factory(CrawlerComponentFactory())

    component_list = [
        {'name': 'engine',            'component_type': 'Engine',           'factory_func': create_engine,            'dependencies': ['crawler']},
        {'name': 'scheduler',         'component_type': 'Scheduler',        'factory_func': create_scheduler,         'dependencies': ['crawler']},
        {'name': 'stats',             'component_type': 'StatsCollector',   'factory_func': create_stats,             'dependencies': ['crawler']},
        {'name': 'subscriber',        'component_type': 'Subscriber',       'factory_func': create_subscriber,        'dependencies': []},
        {'name': 'extension_manager', 'component_type': 'ExtensionManager', 'factory_func': create_extension_manager, 'dependencies': ['crawler']},
    ]
    _batch_register(component_list)


# ===================================================================
# 顶层延迟注册 + 公共便捷 API
# ===================================================================


_components_registered_triggered: bool = False


def _ensure_components_registered():
    """确保 Crawler 相关组件已注册（Phase 8 Step 8.3：容器优先 + RegistryContext 兜底）。"""
    global _components_registered_triggered
    reg_ctx = None
    try:
        from crawlo.core.application import default_container
        from crawlo.core.application import RegistryContext
        if default_container.is_registered(RegistryContext):
            reg_ctx = default_container.resolve(RegistryContext)
    except Exception:  # noqa: S110
        reg_ctx = None

    if reg_ctx is None:
        from crawlo.core.application import get_global_context
        reg_ctx = get_global_context().registries

    if not reg_ctx.components_registered:
        register_crawler_components()
        reg_ctx.components_registered = True
    _components_registered_triggered = True


def get_component_registry():
    """获取全局组件注册表（首次调用时自动完成 Crawler 组件注册）"""
    _ensure_components_registered()
    return _get_registry_impl()


def get_component(name, **kwargs):
    """获取组件实例（首次调用时自动完成 Crawler 组件注册）"""
    _ensure_components_registered()
    return _get_registry_impl().get(name, **kwargs)


def create_component(name, **kwargs):
    """创建组件实例（首次调用时自动完成 Crawler 组件注册）"""
    _ensure_components_registered()
    return _get_registry_impl().create(name, **kwargs)
