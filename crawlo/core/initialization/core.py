#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
CoreInitializer — 核心初始化器
==============================
协调整个框架的初始化过程，用 SingletonMeta 保证单例。
阶段化编排 + 依赖校验 + 超时隔离执行 + fallback 兜底。
"""
import threading
import time as _time
from typing import Any, List, Optional

from crawlo.core.singleton import SingletonMeta
from crawlo.core.initialization.phases import (
    InitializationPhase,
    PhaseResult,
    get_phase_definition,
    get_execution_order,
    validate_phase_dependencies,
)
from crawlo.core.initialization.context import InitializationContext
from crawlo.core.initialization.registry import get_global_registry
from crawlo.core.initialization.built_in import register_built_in_initializers


class CoreInitializer(metaclass=SingletonMeta):
    """核心初始化器 — 协调整个框架的初始化过程"""

    def __init__(self):
        self._context: Optional[InitializationContext] = None
        self._is_ready = False
        self._init_lock = threading.RLock()

        is_valid, error_msg = validate_phase_dependencies()
        if not is_valid:
            raise RuntimeError(f"初始化阶段配置错误: {error_msg}")

        register_built_in_initializers()

    @property
    def context(self) -> Optional[InitializationContext]:
        return self._context

    @property
    def is_ready(self) -> bool:
        return self._is_ready

    def initialize(self, settings=None, **kwargs) -> Any:
        with self._init_lock:
            if self._is_ready and self._context and self._context.settings:
                return self._context.settings

            context = InitializationContext()
            context.custom_settings = kwargs
            context.settings = settings
            self._context = context

            try:
                self._execute_initialization_phases(context)

                if not context.is_phase_completed(InitializationPhase.SETTINGS):
                    raise RuntimeError("Settings initialization failed")

                self._is_ready = True
                context.finish()

                return context.settings

            except Exception as e:
                context.add_error(f"Framework initialization failed: {e}")
                context.finish()

                return self._fallback_initialization(settings, **kwargs)

    def _execute_initialization_phases(self, context: InitializationContext):
        registry = get_global_registry()
        execution_order = get_execution_order()

        registered_phases = set(registry.get_all_phases())

        for phase in execution_order:
            if phase == InitializationPhase.ERROR:
                continue

            if phase not in registered_phases:
                continue

            context.set_current_phase(phase)

            if not self._check_dependencies(phase, context):
                phase_def = get_phase_definition(phase)
                if not (phase_def and phase_def.optional):
                    raise RuntimeError(f"Dependencies not satisfied for phase {phase}")
                else:
                    continue

            start_time = _time.time()
            try:
                result = self._execute_phase_with_timeout(phase, context, registry)
                result.duration = _time.time() - start_time

                context.mark_phase_completed(phase, result)

                if not result.success and not self._is_phase_optional(phase):
                    raise RuntimeError(f"Phase {phase} failed: {result.error}")

            except Exception as e:
                duration = _time.time() - start_time
                result = PhaseResult(
                    phase=phase,
                    success=False,
                    duration=duration,
                    error=e
                )
                context.mark_phase_completed(phase, result)

                if not self._is_phase_optional(phase):
                    raise

    def _execute_phase_with_timeout(self, phase: InitializationPhase,
                                    context: InitializationContext,
                                    registry) -> PhaseResult:
        phase_def = get_phase_definition(phase)
        timeout = phase_def.timeout if phase_def else 30.0

        result_container: List[Optional[PhaseResult]] = [None]
        exception_container: List[Optional[Exception]] = [None]

        def execute_in_thread():
            try:
                result_container[0] = registry.execute_phase(phase, context)
            except Exception as e:
                exception_container[0] = e

        thread = threading.Thread(target=execute_in_thread, daemon=True)
        thread.start()
        thread.join(timeout=timeout)

        if thread.is_alive():
            error_msg = f"Phase {phase.value} execution timeout after {timeout} seconds"
            context.add_warning(error_msg)
            return PhaseResult(
                phase=phase,
                success=False,
                error=TimeoutError(error_msg)
            )

        if exception_container[0]:
            raise exception_container[0]

        if result_container[0] is None:
            raise RuntimeError(f"Phase {phase.value} returned None result")
        return result_container[0]

    def _check_dependencies(self, phase: InitializationPhase,
                          context: InitializationContext) -> bool:
        phase_def = get_phase_definition(phase)
        if not phase_def:
            return True

        for dependency in phase_def.dependencies:
            if not context.is_phase_completed(dependency):
                return False

        return True

    def _is_phase_optional(self, phase: InitializationPhase) -> bool:
        phase_def = get_phase_definition(phase)
        return phase_def.optional if phase_def else False

    def _fallback_initialization(self, settings=None, **kwargs):
        try:
            from crawlo.settings.setting_manager import SettingManager  # noqa: WPS433

            if settings:
                return settings
            else:
                fallback_settings = SettingManager()
                if kwargs:
                    fallback_settings.update_attributes(kwargs)
                return fallback_settings

        except Exception:
            return None

    def reset(self):
        with self._init_lock:
            self._context = None
            self._is_ready = False


__all__ = ["CoreInitializer"]
