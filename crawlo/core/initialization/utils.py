#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
初始化工具函数
==============
- create_initialization_result: 创建标准化的初始化结果
- InitializationTimer: 初始化计时器
"""
import time as _time
from typing import Any, Dict, Optional

from crawlo.core.initialization.phases import InitializationPhase, PhaseResult


def create_initialization_result(
    phase: 'InitializationPhase',
    success: bool,
    duration: float = 0.0,
    artifacts: Optional[Dict[str, Any]] = None,
    error: Optional[Exception] = None
) -> PhaseResult:
    """创建标准化的初始化结果"""
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
        self.start_time = _time.time()

    def get_duration(self) -> float:
        return _time.time() - self.start_time


__all__ = ["create_initialization_result", "InitializationTimer"]
