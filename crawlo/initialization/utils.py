#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
初始化工具模块 - 提供通用的初始化工具函数
"""

import time
from typing import Optional, Dict, Any
from .phases import PhaseResult, InitializationPhase


def create_initialization_result(
    phase: 'InitializationPhase',
    success: bool, 
    duration: float = 0.0,
    artifacts: Optional[Dict[str, Any]] = None, 
    error: Optional[Exception] = None
) -> PhaseResult:
    """
    创建标准化的初始化结果
    
    Args:
        phase: 初始化阶段
        success: 是否成功
        duration: 执行时长
        artifacts: 产生的工件数据
        error: 异常对象
        
    Returns:
        PhaseResult: 标准化的初始化结果
    """
    return PhaseResult(
        phase=phase,
        success=success,
        duration=duration,
        artifacts=artifacts or {},
        error=error
    )


class InitializationTimer:
    """初始化计时器"""
    
    def __init__(self):
        self.start_time = time.time()
    
    def get_duration(self) -> float:
        """获取经过的时间"""
        return time.time() - self.start_time