#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
初始化器注册表
==============
- Initializer / BaseInitializer: 初始化器基类
- InitializerRegistry: 管理注册与执行
- get_global_registry: 全局注册表解析（DI 容器优先 + RegistryContext fallback）
"""
import threading
from typing import Any, Callable, Dict, List, Optional

from crawlo.core.initialization.phases import InitializationPhase
from crawlo.core.initialization.context import InitializationContext
from crawlo.core.initialization.utils import create_initialization_result


class Initializer:
    """Initializer base class"""

    def __init__(self, phase: InitializationPhase):
        self._phase = phase

    @property
    def phase(self) -> InitializationPhase:
        return self._phase

    def initialize(self, context: InitializationContext) -> 'PhaseResult':
        raise NotImplementedError("Subclasses must implement initialize method")


class BaseInitializer(Initializer):
    """Base initializer class — retained for backward compatibility"""

    def __init__(self, phase: InitializationPhase):
        super().__init__(phase)

    def _create_result(self, success: bool, duration: float = 0.0,
                      artifacts: Optional[Dict[str, Any]] = None, error: Optional[Exception] = None):
        return create_initialization_result(
            phase=self.phase,
            success=success,
            duration=duration,
            artifacts=artifacts,
            error=error
        )


class InitializerRegistry:
    """Initializer Registry — Manage registration and execution of all initializers"""

    def __init__(self):
        self._initializers: Dict[InitializationPhase, Initializer] = {}
        self._lock = threading.RLock()

    def register(self, initializer: Initializer):
        with self._lock:
            phase = initializer.phase
            if phase in self._initializers:
                raise ValueError(f"Initializer for phase {phase} already registered")
            self._initializers[phase] = initializer

    def register_function(self, phase: InitializationPhase,
                         init_func: Callable[[InitializationContext], 'PhaseResult']):

        class FunctionInitializer(Initializer):
            def __init__(self, phase: InitializationPhase, func: Callable):
                super().__init__(phase)
                self._func = func

            def initialize(self, context: InitializationContext):
                return self._func(context)

        self.register(FunctionInitializer(phase, init_func))

    def get_initializer(self, phase: InitializationPhase) -> Optional[Initializer]:
        with self._lock:
            return self._initializers.get(phase)

    def get_all_phases(self) -> List[InitializationPhase]:
        with self._lock:
            return list(self._initializers.keys())

    def has_initializer(self, phase: InitializationPhase) -> bool:
        with self._lock:
            return phase in self._initializers

    def clear(self):
        with self._lock:
            self._initializers.clear()

    def execute_phase(self, phase: InitializationPhase,
                     context: InitializationContext):
        initializer = self.get_initializer(phase)
        if not initializer:
            error = ValueError(f"No initializer registered for phase {phase}")
            from crawlo.core.initialization.phases import PhaseResult
            return PhaseResult(
                phase=phase,
                success=False,
                error=error
            )

        try:
            return initializer.initialize(context)
        except Exception as e:
            from crawlo.core.initialization.phases import PhaseResult
            return PhaseResult(
                phase=phase,
                success=False,
                error=e
            )


def _resolve_registry_context():
    """优先从容器拿 RegistryContext，否则 fallback ctx.registries。"""
    try:
        from crawlo.core.application import default_container, RegistryContext
        if default_container.is_registered(RegistryContext):
            return default_container.resolve(RegistryContext)
    except Exception:  # noqa: S110
        pass
    from crawlo.core.application import get_global_context
    return get_global_context().registries


def get_global_registry() -> InitializerRegistry:
    """获取全局初始化器注册表（DI 容器优先 + RegistryContext fallback）。"""
    try:
        from crawlo.core.application import default_container
        if default_container.is_registered(InitializerRegistry):
            return default_container.resolve(InitializerRegistry)
    except Exception:  # pragma: no cover
        pass

    rctx = _resolve_registry_context()
    if rctx.initializer_registry is None:
        inst = InitializerRegistry()
        rctx.initializer_registry = inst
        try:
            from crawlo.core.application import default_container as _c
            _c.register_instance(InitializerRegistry, inst)
        except Exception:  # pragma: no cover
            pass
    return rctx.initializer_registry


def register_initializer(initializer: Initializer):
    """注册初始化器到全局注册表"""
    get_global_registry().register(initializer)


def register_phase_function(phase: InitializationPhase,
                            init_func: Callable[[InitializationContext], 'PhaseResult']):
    """注册函数式初始化器到全局注册表"""
    get_global_registry().register_function(phase, init_func)


__all__ = [
    "Initializer",
    "BaseInitializer",
    "InitializerRegistry",
    "get_global_registry",
    "register_initializer",
    "register_phase_function",
]
