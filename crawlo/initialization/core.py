#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
核心初始化器 - 协调整个初始化过程
"""

import threading
import time
import signal
from typing import Optional, Any

from .built_in import register_built_in_initializers
from .context import InitializationContext
from .phases import InitializationPhase, PhaseResult, get_execution_order, get_phase_definition, validate_phase_dependencies
from .registry import get_global_registry


from crawlo.utils.singleton import singleton

@singleton
class CoreInitializer:
    """
    核心初始化器 - 协调整个框架的初始化过程
    
    职责：
    1. 管理初始化阶段的执行顺序
    2. 处理阶段间的依赖关系
    3. 提供统一的初始化入口
    4. 错误处理和降级策略
    """
    
    def __init__(self):
        self._context: Optional[InitializationContext] = None
        self._is_ready = False
        self._init_lock = threading.RLock()
        
        # 在注册内置初始化器之前，先验证阶段依赖关系
        is_valid, error_msg = validate_phase_dependencies()
        if not is_valid:
            raise RuntimeError(f"初始化阶段配置错误: {error_msg}")
        
        # 注册内置初始化器
        register_built_in_initializers()
    
    @property
    def context(self) -> Optional[InitializationContext]:
        """获取初始化上下文"""
        return self._context
    
    @property  
    def is_ready(self) -> bool:
        """检查框架是否已准备就绪"""
        return self._is_ready
    
    def initialize(self, settings=None, **kwargs) -> Any:
        """
        执行框架初始化
        
        Args:
            settings: 配置对象
            **kwargs: 额外的配置参数
            
        Returns:
            初始化后的配置管理器
        """
        with self._init_lock:
            # 如果已经初始化完成，直接返回
            if self._is_ready and self._context and self._context.settings:
                return self._context.settings
            
            # 创建初始化上下文
            context = InitializationContext()
            context.custom_settings = kwargs
            context.settings = settings
            self._context = context
            
            try:
                # 执行初始化阶段
                self._execute_initialization_phases(context)
                
                # 检查关键阶段是否完成
                if not context.is_phase_completed(InitializationPhase.SETTINGS):
                    raise RuntimeError("Settings initialization failed")
                
                self._is_ready = True
                context.finish()
                
                return context.settings
                
            except Exception as e:
                context.add_error(f"Framework initialization failed: {e}")
                context.finish()
                
                # 降级策略
                return self._fallback_initialization(settings, **kwargs)
    
    def _execute_initialization_phases(self, context: InitializationContext):
        """执行初始化阶段"""
        registry = get_global_registry()
        execution_order = get_execution_order()
        
        # 只执行已注册的阶段
        registered_phases = set(registry.get_all_phases())
        
        for phase in execution_order:
            if phase == InitializationPhase.ERROR:
                continue
                
            # 只执行已注册的阶段
            if phase not in registered_phases:
                continue
                
            context.set_current_phase(phase)
            
            # 检查依赖关系
            if not self._check_dependencies(phase, context):
                phase_def = get_phase_definition(phase)
                if not (phase_def and phase_def.optional):
                    raise RuntimeError(f"Dependencies not satisfied for phase {phase}")
                else:
                    # 可选阶段，跳过
                    continue
            
            # 执行阶段（带超时控制）
            start_time = time.time()
            try:
                result = self._execute_phase_with_timeout(phase, context, registry)
                result.duration = time.time() - start_time
                
                context.mark_phase_completed(phase, result)
                
                if not result.success and not self._is_phase_optional(phase):
                    raise RuntimeError(f"Phase {phase} failed: {result.error}")
                    
            except Exception as e:
                duration = time.time() - start_time
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
        """
        执行阶段并支持超时控制
        
        Args:
            phase: 初始化阶段
            context: 初始化上下文
            registry: 初始化器注册表
            
        Returns:
            PhaseResult: 阶段执行结果
            
        Raises:
            TimeoutError: 阶段执行超时
        """
        phase_def = get_phase_definition(phase)
        timeout = phase_def.timeout if phase_def else 30.0
        
        # 使用线程执行，支持超时
        result_container: list[Optional[PhaseResult]] = [None]
        exception_container: list[Optional[Exception]] = [None]
        
        def execute_in_thread():
            try:
                result_container[0] = registry.execute_phase(phase, context)
            except Exception as e:
                exception_container[0] = e
        
        thread = threading.Thread(target=execute_in_thread, daemon=True)
        thread.start()
        thread.join(timeout=timeout)
        
        if thread.is_alive():
            # 超时了
            error_msg = f"Phase {phase.value} execution timeout after {timeout} seconds"
            context.add_warning(error_msg)
            return PhaseResult(
                phase=phase,
                success=False,
                error=TimeoutError(error_msg)
            )
        
        # 检查是否有异常
        if exception_container[0]:
            raise exception_container[0]
        
        # 返回结果（已经确保不为None）
        if result_container[0] is None:
            raise RuntimeError(f"Phase {phase.value} returned None result")
        return result_container[0]
    
    def _check_dependencies(self, phase: InitializationPhase, 
                          context: InitializationContext) -> bool:
        """检查阶段依赖关系"""
        phase_def = get_phase_definition(phase)
        if not phase_def:
            return True
        
        for dependency in phase_def.dependencies:
            if not context.is_phase_completed(dependency):
                return False
        
        return True
    
    def _is_phase_optional(self, phase: InitializationPhase) -> bool:
        """检查阶段是否可选"""
        phase_def = get_phase_definition(phase)
        return phase_def.optional if phase_def else False
    
    def _fallback_initialization(self, settings=None, **kwargs):
        """降级初始化策略"""
        try:
            # 尝试创建基本的配置管理器
            from crawlo.settings.setting_manager import SettingManager
            
            if settings:
                return settings
            else:
                fallback_settings = SettingManager()
                if kwargs:
                    fallback_settings.update_attributes(kwargs)
                return fallback_settings
                
        except Exception:
            # 如果连降级都失败，返回None
            return None
    
    def reset(self):
        """重置初始化状态（主要用于测试）"""
        with self._init_lock:
            self._context = None
            self._is_ready = False