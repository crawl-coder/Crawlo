#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Crawlo 组件注册表（从 factories.py 迁出）

职责：
1. 管理 ComponentSpec 的注册（同步 + 异步锁安全双模式）
2. 按 component_type 路由到合适的 ComponentFactory
3. 创建组件实例（含 singleton 缓存复用）
4. 解析"全局注册表实例"——优先 DI 容器 default_container，其次 fallback 到
   RegistryContext.component_registry，确保与 Phase 8.8 Application 体系一致。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Type

from crawlo.core.component_base import (
    ComponentSpec,
    ComponentFactory,
    DefaultComponentFactory,
)
from crawlo.utils.concurrency import AsyncRLock


__all__ = [
    "ComponentRegistry",
    "get_component_registry",
]


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
        self._lock = AsyncRLock()

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
        """List all registered components (synchronous method)"""
        return list(self._specs.keys())

    def clear(self):
        """Clear the registry"""
        self._specs.clear()
        self._factories.clear()
        self._default_factory.clear_singletons()


def _resolve_registry_context():
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


def get_component_registry() -> ComponentRegistry:
    """Get the global component registry（Phase 8 Step 8.8：DI 容器优先 + RegistryContext fallback）。

    迁移策略（与 InitializerRegistry / JobRegistry 保持三模块一致）：
    1. 先从 ``default_container`` 解析（Phase 8.2 已在 ApplicationContext.__post_init__
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
    rctx = _resolve_registry_context()
    if rctx.component_registry is None:
        inst = ComponentRegistry()
        rctx.component_registry = inst
        try:
            from crawlo.core.application import default_container as _c
            _c.register_instance(ComponentRegistry, inst)
        except Exception:  # pragma: no cover
            pass
    return rctx.component_registry
