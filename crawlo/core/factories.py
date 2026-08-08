#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Crawlo Component Factory System（Phase 5 #30：原 factories/ 目录 5 子模块合并入单文件）
==========================================================================================

Provides unified component creation and dependency injection mechanism.

子模块原职责（合并后保持定义顺序）：
    base.py      ComponentSpec / ComponentFactory / DefaultComponentFactory 基类
    utils.py     register_component / register_components / 工厂函数构建器
    registry.py  ComponentRegistry + get_component_registry（DI 容器优先）
    crawler.py   CrawlerComponentFactory + 5 个爬虫组件 create_* + register_crawler_components
    __init__.py  顶层延迟注册 _ensure_components_registered() + get_component_registry() / register_component() 等
"""
from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Type, Union

from crawlo.utils.concurrency import AsyncRLock


__all__ = [
    "ComponentSpec",
    "ComponentFactory",
    "DefaultComponentFactory",
    "ComponentRegistry",
    "CrawlerComponentFactory",
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


# ===================================================================
# base.py — 基类与规格
# ===================================================================


@dataclass
class ComponentSpec:
    """Component Specification - Defines how to create a component"""

    name: str
    component_type: Type
    factory_func: Callable[..., Any]
    dependencies: Optional[List[str]] = None
    singleton: bool = False
    config_key: Optional[str] = None

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


class ComponentFactory(ABC):
    """Component Factory Base Class"""

    @abstractmethod
    def create(self, spec: ComponentSpec, **kwargs) -> Any:
        """Create component instance"""
        pass

    @abstractmethod
    def supports(self, component_type: Type) -> bool:
        """Check if the factory supports the specified component type"""
        pass


class DefaultComponentFactory(ComponentFactory):
    """Default Component Factory Implementation"""

    def __init__(self):
        self._instances: Dict[str, Any] = {}

    def create(self, spec: ComponentSpec, **kwargs) -> Any:
        """Create component instance"""
        # Singleton pattern check
        if spec.singleton and spec.name in self._instances:
            return self._instances[spec.name]

        # Call factory function to create instance
        instance = spec.factory_func(**kwargs)

        # Save singleton instance
        if spec.singleton:
            self._instances[spec.name] = instance

        return instance

    def supports(self, component_type: Type) -> bool:
        """Supports all types"""
        return True

    def clear_singletons(self):
        """Clear singleton instances (for testing)"""
        self._instances.clear()


# ===================================================================
# utils.py — 工具函数
# ===================================================================


def _utils_register_component(
    name: str,
    component_type: Union[Type, str],
    factory_func: Callable[..., Any],
    dependencies: Optional[List[str]] = None,
    singleton: bool = False,
    config_key: Optional[str] = None
) -> None:
    """
    Convenience function for registering components

    Args:
        name: Component name
        component_type: Component type
        factory_func: Factory function
        dependencies: Dependency list
        singleton: Whether to use singleton pattern
        config_key: Configuration key name
    """
    registry = _utils_get_component_registry()

    # If component_type is a string, use it as identifier (not creating empty class)
    if isinstance(component_type, str):
        # Store as string type identifier, factories will use name-based matching
        component_type = type(component_type, (), {'__type_identifier__': component_type})

    spec_kwargs = {
        'name': name,
        'component_type': component_type,
        'factory_func': factory_func,
        'dependencies': dependencies or [],
        'singleton': singleton
    }

    # Only add config_key if it's not None
    if config_key is not None:
        spec_kwargs['config_key'] = config_key

    spec = ComponentSpec(**spec_kwargs)

    registry.register(spec)


def register_components(component_list: List[dict]) -> None:
    """
    Batch register components

    Args:
        component_list: Component definition list, each element is a dictionary containing component info
    """
    for component_info in component_list:
        _utils_register_component(**component_info)


def create_component_factory(
    component_name: str,
    module_path: str,
    class_name: str,
    dependencies: Optional[List[str]] = None,
    singleton: bool = False
) -> Callable[..., Any]:
    """
    Convenience function for creating component factory functions

    Args:
        component_name: Component name (for error messages)
        module_path: Module path
        class_name: Class name
        dependencies: Dependency list
        singleton: Whether to use singleton pattern

    Returns:
        Factory function
    """
    def factory_func(*args, **kwargs):
        try:
            # Dynamic module import
            module = __import__(module_path, fromlist=[class_name])
            component_class = getattr(module, class_name)

            # Check if create_instance method should be called
            if hasattr(component_class, 'create_instance'):
                return component_class.create_instance(*args, **kwargs)
            else:
                return component_class(*args, **kwargs)
        except Exception as e:
            raise RuntimeError(f"Failed to create {component_name}: {e}")

    return factory_func


def create_crawler_component_factory(
    component_name: str,
    module_path: str,
    class_name: str
) -> Callable[..., Any]:
    """
    Create component factory function that requires crawler dependency

    Args:
        component_name: Component name
        module_path: Module path
        class_name: Class name

    Returns:
        Factory function
    """
    def factory_func(crawler=None, **kwargs):
        if crawler is None:
            raise ValueError(f"Crawler instance required for component {component_name}")

        try:
            # Dynamic module import
            module = __import__(module_path, fromlist=[class_name])
            component_class = getattr(module, class_name)

            # Check if create_instance method should be called
            if hasattr(component_class, 'create_instance'):
                return component_class.create_instance(crawler, **kwargs)
            else:
                return component_class(crawler, **kwargs)
        except Exception as e:
            raise RuntimeError(f"Failed to create {component_name}: {e}")

    return factory_func


# ===================================================================
# registry.py — 组件注册表
# ===================================================================


class ComponentRegistry:
    """
    Component Registry

    Responsibilities:
    1. Manage component specification registration
    2. Find appropriate factory by type
    3. Handle dependencies
    4. Create component instances
    """

    def __init__(self):
        self._specs: Dict[str, ComponentSpec] = {}
        self._factories: List[ComponentFactory] = []
        self._default_factory = DefaultComponentFactory()
        self._lock = AsyncRLock()  # 异步安全锁

    async def register_async(self, spec: ComponentSpec):
        """Async-safe registration method"""
        async with self._lock:
            self._specs[spec.name] = spec

    async def register_factory_async(self, factory: ComponentFactory):
        """Async-safe factory registration method"""
        async with self._lock:
            self._factories.append(factory)

    async def get_spec_async(self, name: str) -> Optional[ComponentSpec]:
        """Async-safe spec retrieval method"""
        async with self._lock:
            return self._specs.get(name)

    async def get_factory_async(self, component_type: Type) -> ComponentFactory:
        """Async-safe factory retrieval method"""
        async with self._lock:
            for factory in self._factories:
                if factory.supports(component_type):
                    return factory
            return self._default_factory

    async def list_components_async(self) -> List[str]:
        """Async-safe component listing method"""
        async with self._lock:
            return list(self._specs.keys())

    def register(self, spec: ComponentSpec):
        """
        Register component spec (synchronous version, for initialization phase)
        Use register_async() in async environments for lock protection
        """
        self._specs[spec.name] = spec

    def register_factory(self, factory: ComponentFactory):
        """
        Register component factory (synchronous method, for backward compatibility only)
        :deprecated: Use register_factory_async instead
        """
        self._factories.append(factory)

    def get_spec(self, name: str) -> Optional[ComponentSpec]:
        """
        Get component spec (synchronous method, for backward compatibility only)
        :deprecated: Use get_spec_async instead
        """
        return self._specs.get(name)

    def get_factory(self, component_type: Type) -> ComponentFactory:
        """
        Get factory that supports the specified type (synchronous method)
        """
        for factory in self._factories:
            if factory.supports(component_type):
                return factory
        return self._default_factory

    def create(self, name: str, **kwargs) -> Any:
        """Create component instance"""
        spec = self.get_spec(name)
        if not spec:
            raise ValueError(f"Component spec '{name}' not found")

        factory = self.get_factory(spec.component_type)
        return factory.create(spec, **kwargs)

    def get(self, name: str, **kwargs) -> Any:
        """Get component instance (alias for create)"""
        return self.create(name, **kwargs)

    def list_components(self) -> List[str]:
        """
        List all registered components (synchronous method)
        """
        return list(self._specs.keys())

    def clear(self):
        """
        Clear the registry
        """
        self._specs.clear()
        self._factories.clear()
        self._default_factory.clear_singletons()


def _registry_resolve_registry_context():
    """Phase 8 Step 8.8 收尾：优先从容器拿 RegistryContext，否则 fallback ctx.registries。"""
    try:
        from crawlo.core.application import default_container
        from crawlo.core.application import RegistryContext
        if default_container.is_registered(RegistryContext):
            return default_container.resolve(RegistryContext)
    except Exception:  # noqa: S110
        pass
    from crawlo.core.application import get_global_context
    return get_global_context().registries


def _registry_get_component_registry() -> ComponentRegistry:
    """Get the global component registry（Phase 8 Step 8.8：DI 容器优先 + RegistryContext fallback）。

    迁移策略（与 InitializerRegistry / JobRegistry 保持三模块一致）：
    1. 先从 :data:`default_container` 解析（Phase 8.2 已在 ApplicationContext.__post_init__
       把非 None 的注册表单例 register 进来）——@inject 类会走这条，依赖显式。
    2. 若容器未注册则 fallback 到 ``RegistryContext.component_registry``：None 时就地构造
       并 ``register_instance`` 补充注册，确保后续 resolve 也能拿到同一引用。

    行为兼容：首次调用懒创建 → 存进子上下文 + 同步注册进容器；无行为变化。
    """
    try:
        from crawlo.core.application import default_container
        if default_container.is_registered(ComponentRegistry):
            return default_container.resolve(ComponentRegistry)
    except Exception:  # pragma: no cover - 容器初始化异常不应破坏调用链
        pass

    # Fallback：通过 RegistryContext 写位（ApplicationContext 顶层 property 会同步到子对象）
    rctx = _registry_resolve_registry_context()
    if rctx.component_registry is None:
        inst = ComponentRegistry()
        rctx.component_registry = inst
        try:
            from crawlo.core.application import default_container as _c
            _c.register_instance(ComponentRegistry, inst)
        except Exception:  # pragma: no cover
            pass
    return rctx.component_registry


# 给 utils.py 内部用的别名（utils 原来 from .registry import get_component_registry）
_utils_get_component_registry = _registry_get_component_registry


# ===================================================================
# crawler.py — Crawler 组件工厂
# ===================================================================


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
        from crawlo.core.scheduling.task_scheduler import Scheduler
        from crawlo.stats.collector import StatsCollector
        from crawlo.event import Subscriber
        from crawlo.extensions import ExtensionManager

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
    from crawlo.core.scheduling.task_scheduler import Scheduler
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
    from crawlo.extensions import ExtensionManager
    return ExtensionManager.create_instance(crawler)


def register_crawler_components():
    """Register Crawler-related components (延迟调用，首次使用时由顶层 _ensure_components_registered 触发)"""

    # Register factory
    registry = _registry_get_component_registry()
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


# ===================================================================
# __init__.py — 顶层延迟注册与公共 API
# ===================================================================


_components_registered_triggered: bool = False


def _ensure_components_registered():
    """确保 Crawler 相关组件已注册（Phase 8 Step 8.3：容器优先 + RegistryContext 兜底）。

    ``components_registered`` 属于 RegistryContext；Phase 8.2 已把 RegistryContext 整体
    注册进 default_container，因此这里优先从容器拿到 RegistryContext，避免直接 import
    ApplicationContext。若容器未就绪（import 期/测试期），再 fallback 到 ctx。
    """
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
    return _registry_get_component_registry()


def register_component(spec):
    """注册组件（首次调用时自动完成 Crawler 组件注册）"""
    _ensure_components_registered()
    return _registry_get_component_registry().register(spec)


def get_component(name, **kwargs):
    """获取组件实例（首次调用时自动完成 Crawler 组件注册）"""
    _ensure_components_registered()
    return _registry_get_component_registry().get(name, **kwargs)


def create_component(name, **kwargs):
    """创建组件实例（首次调用时自动完成 Crawler 组件注册）"""
    _ensure_components_registered()
    return _registry_get_component_registry().create(name, **kwargs)
